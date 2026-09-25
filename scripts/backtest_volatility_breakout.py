"""
Backtest da VolatilityBreakoutStrategy com modelagem de custos + SL/TP.

Diferente do benchmark_volatility (que mede apenas edge preditivo),
este script mede PnL LIQUIDO considerando:
  - Spread por operacao (entrada + saida)
  - Comissao por contrato
  - SL/TP dinamicos via ATR (opcional)
  - Contratos fixos (1)
  - Multiplicador do WIN (1 ponto = R$ 0.20)

Interpretacao: se o PnL liquido for > 0 de forma consistente, o sinal
do ADR-023 e operavel. Se for <= 0, os custos absorvem o edge.

Uso:
    python scripts/backtest_volatility_breakout.py --from-mt5 --symbol WINV26
    python scripts/backtest_volatility_breakout.py  # sintetico
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


TIMEFRAME_MAP = {
    "M1":  "TIMEFRAME_M1",
    "M5":  "TIMEFRAME_M5",
    "M15": "TIMEFRAME_M15",
    "M30": "TIMEFRAME_M30",
    "H1":  "TIMEFRAME_H1",
}


from src.domain.models import Candle
from src.indicators.engine import IndicatorEngine
from src.strategies.volatility_breakout import VolatilityBreakoutStrategy


# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------

def candles_sinteticos(n: int = 5000) -> List[Candle]:
    """AR(1) + volatility clustering simulado (GARCH(1,1) simples)."""
    from datetime import timedelta
    np.random.seed(42)
    price = 130000.0
    prev_ret = 0.0
    vol = 0.0008
    base_ts = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    candles: List[Candle] = []
    for i in range(n):
        vol = 0.0000001 + 0.1 * (prev_ret ** 2) + 0.85 * vol
        ret = 0.3 * prev_ret + np.random.randn() * (vol ** 0.5)
        o = price
        c = price * (1 + ret)
        h = max(o, c) * (1 + abs(np.random.randn()) * 0.0002)
        l = min(o, c) * (1 - abs(np.random.randn()) * 0.0002)
        v = float(np.random.randint(500, 3000))
        candles.append(Candle(
            symbol="SYNTH",
            timestamp=base_ts + timedelta(minutes=5 * i),
            open=o, high=h, low=l, close=c, volume=v,
        ))
        price = c
        prev_ret = ret
    return candles


def candles_mt5(symbol: str, n: int, timeframe: str = "M5") -> List[Candle]:
    from datetime import datetime, timezone
    import MetaTrader5 as mt5

    tf_const = getattr(mt5, TIMEFRAME_MAP[timeframe])

    if not mt5.initialize():
        raise RuntimeError(f"mt5.initialize falhou: {mt5.last_error()}")
    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"Simbolo {symbol} nao encontrado")
        if not info.visible:
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Falha ao adicionar {symbol}")

        rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, n)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"Sem barras para {symbol} {timeframe}")

        return [
            Candle(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(int(r["time"]), tz=timezone.utc),
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
                volume=float(r["tick_volume"]),
            )
            for r in rates
        ]
    finally:
        mt5.shutdown()


# ---------------------------------------------------------------------------
# Backtest customizado
# ---------------------------------------------------------------------------

def run_backtest(
    candles: List[Candle],
    strategy: VolatilityBreakoutStrategy,
    initial_balance: float = 10000.0,
    contract_multiplier: float = 0.20,
    contracts: float = 1.0,
    spread_points: float = 5.0,
    commission_per_contract: float = 1.0,
    hold_max_candles: int = 10,
    use_sltp: bool = False,
    atr_mult_sl: float = 1.5,
    atr_mult_tp: float = 3.0,
    atr_key: str = "atr",
    max_trades: int = 50,
) -> Dict[str, Any]:
    """
    Loop de backtest direcional com SL/TP opcional.

    Regras:
      - 1 posicao por vez
      - Abre em BUY/SELL quando strategy sinaliza
      - Fecha em (ordem de verificacao):
          1. Stop loss atingido no candle
          2. Take profit atingido no candle
          3. Sinal oposto
          4. hold_max_candles atingido
      - SL/TP via ATR (se use_sltp=True): SL = atr_mult_sl * ATR;
        TP = atr_mult_tp * ATR
      - Custos: spread (entrada+saida) + comissao (entrada)
    """
    equity = initial_balance
    equity_curve = [equity]
    trades: List[Dict[str, Any]] = []
    position: Optional[Dict[str, Any]] = None

    indicator_engine = IndicatorEngine()

    for i in range(1, len(candles)):
        window = candles[: i + 1]
        last = candles[i]

        # Avalia sinal (com indicadores para obter ATR)
        try:
            indicators = indicator_engine.compute_all(window)
            sig = strategy.evaluate(window, indicator_results=indicators)
        except Exception:
            sig = None
            indicators = {}

        direction = str(getattr(sig.direction, "value", sig.direction)).upper() if sig else ""

        # Se temos posicao aberta, checa saidas (SL/TP primeiro)
        if position is not None:
            position["bars_held"] += 1
            should_close = False
            close_reason = None
            exit_price = None

            # 1. SL/TP (usando high/low do candle)
            if use_sltp and position.get("stop_loss") is not None:
                if position["side"] == "BUY":
                    if last.low <= position["stop_loss"]:
                        exit_price = position["stop_loss"] - spread_points
                        should_close = True
                        close_reason = "stop_loss"
                    elif last.high >= position["take_profit"]:
                        exit_price = position["take_profit"] - spread_points
                        should_close = True
                        close_reason = "take_profit"
                else:  # SELL
                    if last.high >= position["stop_loss"]:
                        exit_price = position["stop_loss"] + spread_points
                        should_close = True
                        close_reason = "stop_loss"
                    elif last.low <= position["take_profit"]:
                        exit_price = position["take_profit"] + spread_points
                        should_close = True
                        close_reason = "take_profit"

            # 2. Sinal oposto
            if not should_close:
                if "BUY" in direction and position["side"] == "SELL":
                    exit_price = last.close + spread_points
                    should_close = True
                    close_reason = "opposite_signal"
                elif "SELL" in direction and position["side"] == "BUY":
                    exit_price = last.close - spread_points
                    should_close = True
                    close_reason = "opposite_signal"

            # 3. Max hold
            if not should_close and position["bars_held"] >= hold_max_candles:
                if position["side"] == "BUY":
                    exit_price = last.close - spread_points
                else:
                    exit_price = last.close + spread_points
                should_close = True
                close_reason = "max_hold"

            if should_close:
                if position["side"] == "BUY":
                    pnl_points = exit_price - position["entry_price"]
                else:
                    pnl_points = position["entry_price"] - exit_price

                pnl_rs = pnl_points * contract_multiplier * contracts
                equity += pnl_rs

                trades.append({
                    "side": position["side"],
                    "entry_time": position["entry_time"].isoformat(),
                    "exit_time": last.timestamp.isoformat(),
                    "entry_price": round(position["entry_price"], 4),
                    "exit_price": round(exit_price, 4),
                    "pnl_rs": round(pnl_rs, 2),
                    "bars_held": position["bars_held"],
                    "reason": close_reason,
                })

                position = None

        # Se nao temos posicao, checa entrada
        if position is None and ("BUY" in direction or "SELL" in direction):
            atr_val = indicators.get(atr_key) if use_sltp else None

            if "BUY" in direction:
                entry_price = last.close + spread_points
                side = "BUY"
                sl = (entry_price - atr_mult_sl * atr_val) if (use_sltp and atr_val) else None
                tp = (entry_price + atr_mult_tp * atr_val) if (use_sltp and atr_val) else None
            else:
                entry_price = last.close - spread_points
                side = "SELL"
                sl = (entry_price + atr_mult_sl * atr_val) if (use_sltp and atr_val) else None
                tp = (entry_price - atr_mult_tp * atr_val) if (use_sltp and atr_val) else None

            equity -= commission_per_contract * contracts

            position = {
                "side": side,
                "entry_time": last.timestamp,
                "entry_price": entry_price,
                "bars_held": 0,
                "stop_loss": sl,
                "take_profit": tp,
            }

        equity_curve.append(equity)

    # Forca fechamento final
    if position is not None and candles:
        last = candles[-1]
        if position["side"] == "BUY":
            exit_price = last.close - spread_points
            pnl_points = exit_price - position["entry_price"]
        else:
            exit_price = last.close + spread_points
            pnl_points = position["entry_price"] - exit_price

        pnl_rs = pnl_points * contract_multiplier * contracts
        equity += pnl_rs

        trades.append({
            "side": position["side"],
            "entry_time": position["entry_time"].isoformat(),
            "exit_time": last.timestamp.isoformat(),
            "entry_price": round(position["entry_price"], 4),
            "exit_price": round(exit_price, 4),
            "pnl_rs": round(pnl_rs, 2),
            "bars_held": position["bars_held"],
            "reason": "end_of_data",
        })

    # Metricas
    total_trades = len(trades)
    wins = [t for t in trades if t["pnl_rs"] > 0]
    losses = [t for t in trades if t["pnl_rs"] < 0]
    gross_profit = sum(t["pnl_rs"] for t in wins)
    gross_loss = abs(sum(t["pnl_rs"] for t in losses))

    peak = initial_balance
    max_dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

    if len(equity_curve) > 2:
        rets = [
            (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
            for i in range(1, len(equity_curve))
            if equity_curve[i - 1] > 0
        ]
        if len(rets) > 1:
            mean_r = sum(rets) / len(rets)
            var = sum((r - mean_r) ** 2 for r in rets) / len(rets)
            std = var ** 0.5
            sharpe = (mean_r / std * (72576 ** 0.5)) if std > 0 else 0.0
        else:
            sharpe = 0.0
    else:
        sharpe = 0.0

    # Contagem por razao de saida
    exits_by_reason: Dict[str, int] = {}
    for t in trades:
        exits_by_reason[t["reason"]] = exits_by_reason.get(t["reason"], 0) + 1

    return {
        "initial_balance": initial_balance,
        "final_balance": round(equity, 2),
        "total_pnl_rs": round(equity - initial_balance, 2),
        "total_pnl_pct": round((equity - initial_balance) / initial_balance * 100, 2),
        "total_trades": total_trades,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / total_trades * 100, 2) if total_trades > 0 else 0.0,
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0.0,
        "max_drawdown_pct": round(max_dd * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "avg_trade_pnl": round(sum(t["pnl_rs"] for t in trades) / total_trades, 2) if total_trades > 0 else 0.0,
        "exits_by_reason": exits_by_reason,
        "costs_config": {
            "spread_points": spread_points,
            "commission_per_contract": commission_per_contract,
            "contract_multiplier": contract_multiplier,
            "contracts": contracts,
            "use_sltp": use_sltp,
            "atr_mult_sl": atr_mult_sl,
            "atr_mult_tp": atr_mult_tp,
        },
                "trades": trades[:max_trades] if max_trades > 0 else trades,
    }

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Backtest VB com custos + SL/TP")
    parser.add_argument("--from-mt5", action="store_true")
    parser.add_argument("--symbol", default="WINV26")
    parser.add_argument("--timeframe", choices=list(TIMEFRAME_MAP.keys()), default="M5")
    parser.add_argument("--n", type=int, default=20000)
    parser.add_argument("--initial-balance", type=float, default=10000.0)
    parser.add_argument("--spread-points", type=float, default=5.0)
    parser.add_argument("--commission", type=float, default=1.0)
    parser.add_argument("--multiplier", type=float, default=0.20)
    parser.add_argument("--hold-max", type=int, default=10)
    parser.add_argument("--lookback", type=int, default=20)
    parser.add_argument("--vol-threshold", type=float, default=1.3)
    parser.add_argument("--use-sltp", action="store_true",
                        help="Ativa SL/TP dinamico via ATR")
    parser.add_argument("--atr-sl", type=float, default=1.5, help="Multiplicador do ATR para SL")
    parser.add_argument("--atr-tp", type=float, default=3.0, help="Multiplicador do ATR para TP")
    parser.add_argument("--out-dir", default="models/benchmarks")
    args = parser.parse_args()

    if args.from_mt5:
        print(f"Buscando {args.n} candles de {args.symbol} ({args.timeframe})...")
        candles = candles_mt5(args.symbol, args.n, args.timeframe)
    else:
        print(f"Gerando {args.n} candles sinteticos (GARCH-like)...")
        candles = candles_sinteticos(args.n)

    print(f"Candles: {len(candles)}")

    strategy = VolatilityBreakoutStrategy(
        lookback=args.lookback,
        vol_threshold=args.vol_threshold,
    )

    print(f"\nEstrategia: {strategy.name} (lookback={args.lookback}, vol_threshold={args.vol_threshold})")
    print(f"Custos: spread={args.spread_points} pontos | comissao=R${args.commission}/contrato")
    print(f"SL/TP: {'ATIVO' if args.use_sltp else 'DESATIVADO'}", end="")
    if args.use_sltp:
        print(f" (SL={args.atr_sl}x ATR, TP={args.atr_tp}x ATR)")
    else:
        print()

    result = run_backtest(
        candles,
        strategy,
        initial_balance=args.initial_balance,
        contract_multiplier=args.multiplier,
        contracts=1.0,
        spread_points=args.spread_points,
        commission_per_contract=args.commission,
        hold_max_candles=args.hold_max,
        use_sltp=args.use_sltp,
        atr_mult_sl=args.atr_sl,
        atr_mult_tp=args.atr_tp,
    )

    print("\n" + "=" * 55)
    print("RESULTADO DO BACKTEST")
    print("=" * 55)
    print(f"Balance inicial:     R$ {result['initial_balance']:.2f}")
    print(f"Balance final:       R$ {result['final_balance']:.2f}")
    print(f"PnL liquido:         R$ {result['total_pnl_rs']:.2f} ({result['total_pnl_pct']:+.2f}%)")
    print(f"Total de trades:     {result['total_trades']}")
    print(f"Wins / Losses:       {result['wins']} / {result['losses']}")
    print(f"Win rate:            {result['win_rate']:.2f}%")
    print(f"Profit factor:       {result['profit_factor']:.2f}")
    print(f"Avg trade PnL:       R$ {result['avg_trade_pnl']:.2f}")
    print(f"Max drawdown:        {result['max_drawdown_pct']:.2f}%")
    print(f"Sharpe ratio:        {result['sharpe_ratio']:.2f}")
    print(f"Saidas por razao:    {result['exits_by_reason']}")
    print("=" * 55)

    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    suffix = "sltp" if args.use_sltp else "nosltp"
    out_path = os.path.join(args.out_dir, f"backtest_vb_{suffix}_{args.symbol}_{args.timeframe}_{ts}.json")
    result_full = {**result, "symbol": args.symbol, "timeframe": args.timeframe,
                   "source": "mt5" if args.from_mt5 else "synthetic",
                   "strategy": strategy.name, "n_candles": len(candles)}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result_full, f, indent=2, default=str)
    print(f"\nResultado salvo em: {out_path}")


if __name__ == "__main__":
    main()