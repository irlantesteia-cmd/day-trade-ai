"""
Analise de estrategia por regime de volatilidade.

Hipotese: o edge de uma estrategia pode ser mascarado pela agregacao
de regimes opostos. Se MA Crossover (edge -6.21 em WINV26 M5) tem
edge POSITIVO em algum regime especifico (low/mid/high vol), o filtro
por regime extrai valor.

Metodo:
  1. Carrega candles MT5 (ou sintetico)
  2. Calcula realized_vol_20 em cada candle
  3. Roda backtest da estrategia (qualquer, via --strategy)
  4. Para cada trade, faz lookup do vol na entrada
  5. Bucketiza em tercis (low/mid/high vol)
  6. Reporta PnL, win rate, PF por bucket

Uso:
    python scripts/regime_split_analysis.py --from-mt5 --symbol WINV26 --strategy ma
    python scripts/regime_split_analysis.py --from-mt5 --symbol WINV26 --strategy rsi
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

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
from src.features.volatility import RealizedVolatilityExtractor
from src.strategies.moving_average import MovingAverageCrossoverStrategy
from src.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from src.strategies.volatility_breakout import VolatilityBreakoutStrategy
from src.indicators.engine import IndicatorEngine
from scripts.backtest_volatility_breakout import (
    candles_mt5,
    candles_sinteticos,
    run_backtest,
)


def build_strategy(name: str) -> Any:
    """Factory de estrategias."""
    name = name.lower()
    if name == "ma":
        return MovingAverageCrossoverStrategy()
    if name == "rsi":
        return RSIMeanReversionStrategy(rsi_key="rsi")
    if name == "vb":
        return VolatilityBreakoutStrategy(lookback=20, vol_threshold=1.5)
    raise ValueError(f"Estrategia desconhecida: {name}. Use: ma, rsi, vb")


def compute_vol_series(
    candles: List[Candle],
    period: int = 20,
) -> List[Optional[float]]:
    """
    Computa realized volatility rolling de N barras para cada candle.
    Retorna lista do mesmo tamanho; primeiros `period` sao None.
    """
    extractor = RealizedVolatilityExtractor(period=period)
    vols: List[Optional[float]] = []
    for i in range(len(candles)):
        if i < period:
            vols.append(None)
            continue
        window = candles[: i + 1]
        out = extractor.extract(window, None)
        v = out.get(f"realized_vol_{period}")
        vols.append(v)
    return vols


def enrich_trades_with_vol(
    trades: List[Dict[str, Any]],
    candles: List[Candle],
    vols: List[Optional[float]],
) -> List[Dict[str, Any]]:
    """
    Para cada trade, adiciona vol no momento da entrada.

    Faz lookup por timestamp (entry_time).
    """
    ts_to_vol: Dict[str, Optional[float]] = {}
    for c, v in zip(candles, vols):
        ts_to_vol[c.timestamp.isoformat()] = v

    for t in trades:
        entry_ts = t.get("entry_time")
        t["vol_at_entry"] = ts_to_vol.get(entry_ts)
    return trades


def split_by_tercis(
    trades: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Divide os trades em 3 buckets por vol_at_entry:
      low:  vol <= 33.3 percentil
      mid:  33.3 < vol <= 66.6 percentil
      high: > 66.6 percentil

    Retorna dict {low, mid, high: [trades]}.
    """
    valid = [t for t in trades if t.get("vol_at_entry") is not None]
    if len(valid) < 15:
        return {"low": [], "mid": [], "high": []}

    vols = np.array([t["vol_at_entry"] for t in valid], dtype=float)
    p33 = float(np.percentile(vols, 33.333))
    p66 = float(np.percentile(vols, 66.667))

    buckets: Dict[str, List[Dict[str, Any]]] = {"low": [], "mid": [], "high": []}
    for t in valid:
        v = t["vol_at_entry"]
        if v <= p33:
            buckets["low"].append(t)
        elif v <= p66:
            buckets["mid"].append(t)
        else:
            buckets["high"].append(t)
    return buckets


def metrics_for_trades(
    trades: List[Dict[str, Any]],
    initial_balance: float = 10000.0,
    contract_multiplier: float = 0.20,
    spread_points: float = 5.0,
    commission: float = 1.0,
) -> Dict[str, Any]:
    """Calcula metricas para um subset de trades (com custos ja embutidos)."""
    if not trades:
        return {
            "n_trades": 0,
            "pnl_rs": 0.0,
            "pnl_pct": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "avg_pnl": 0.0,
        }

    pnls = [t["pnl_rs"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0

    total_pnl = sum(pnls)
    total_commission = len(trades) * commission  # ja esta embutido, mas redundante

    return {
        "n_trades": len(trades),
        "pnl_rs": round(total_pnl, 2),
        "pnl_pct": round(total_pnl / initial_balance * 100, 2),
        "win_rate": round(len(wins) / len(trades) * 100, 2),
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0.0,
        "avg_pnl": round(total_pnl / len(trades), 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
    }


def main():
    parser = argparse.ArgumentParser(description="Analise de estrategia por regime de vol")
    parser.add_argument("--from-mt5", action="store_true")
    parser.add_argument("--symbol", default="WINV26")
    parser.add_argument("--timeframe", choices=list(TIMEFRAME_MAP.keys()), default="M5")
    parser.add_argument("--n", type=int, default=20000)
    parser.add_argument("--strategy", choices=["ma", "rsi", "vb"], default="ma")
    parser.add_argument("--vol-window", type=int, default=20)
    parser.add_argument("--spread-points", type=float, default=5.0)
    parser.add_argument("--commission", type=float, default=1.0)
    parser.add_argument("--hold-max", type=int, default=10)
    parser.add_argument("--use-sltp", action="store_true")
    parser.add_argument("--atr-sl", type=float, default=3.0)
    parser.add_argument("--atr-tp", type=float, default=6.0)
    parser.add_argument("--out-dir", default="models/benchmarks")
    args = parser.parse_args()

    # 1. Dados
    if args.from_mt5:
        print(f"Buscando {args.n} candles de {args.symbol} ({args.timeframe})...")
        candles = candles_mt5(args.symbol, args.n, args.timeframe)
    else:
        print(f"Gerando {args.n} candles sinteticos...")
        candles = candles_sinteticos(args.n)

    print(f"Candles: {len(candles)}")

    # 2. Estrategia
    strategy = build_strategy(args.strategy)
    print(f"Estrategia: {strategy.name}")

    # 3. Backtest
    print(f"\nRodando backtest (custos: {args.spread_points}pts + R${args.commission}/contrato)...")
    result = run_backtest(
        candles,
        strategy,
        initial_balance=10000.0,
        contract_multiplier=0.20,
        contracts=1.0,
        spread_points=args.spread_points,
        commission_per_contract=args.commission,
        hold_max_candles=args.hold_max,
        use_sltp=args.use_sltp,
        atr_mult_sl=args.atr_sl,
        atr_mult_tp=args.atr_tp,
        max_trades=0,  # retorna todos os trades (nao trunca em 50)
    )

    trades = result["trades"]
    print(f"Total de trades: {result['total_trades']} | PnL: {result['total_pnl_pct']:+.2f}%")
    print(f"Win rate: {result['win_rate']:.2f}% | PF: {result['profit_factor']:.2f}")

    if not trades:
        raise SystemExit("Sem trades para analisar por regime.")

    # 4. Vol series
    print(f"\nCalculando realized_vol_{args.vol_window} em cada candle...")
    vols = compute_vol_series(candles, period=args.vol_window)
    n_valid = sum(1 for v in vols if v is not None)
    print(f"Vol valida em {n_valid}/{len(candles)} candles")

    # 5. Enriquecer trades
    trades = enrich_trades_with_vol(trades, candles, vols)
    n_with_vol = sum(1 for t in trades if t.get("vol_at_entry") is not None)
    print(f"Trades com vol: {n_with_vol}/{len(trades)}")

    # 6. Split por tercil
    print(f"\nSplit por tercil de volatilidade...")
    buckets = split_by_tercis(trades)
    for name, ts in buckets.items():
        print(f"  {name}: {len(ts)} trades")

    # 7. Metricas por bucket
    print("\n" + "=" * 78)
    print(f"{'Bucket':<10} | {'Trades':>7} | {'PnL R$':>10} | {'PnL %':>8} | {'Win%':>6} | {'PF':>5} | {'Avg R$':>8}")
    print("-" * 78)

    all_metrics: Dict[str, Any] = {}
    for name in ["low", "mid", "high"]:
        m = metrics_for_trades(
            buckets[name],
            initial_balance=10000.0,
            spread_points=args.spread_points,
            commission=args.commission,
        )
        all_metrics[name] = m
        print(f"{name:<10} | {m['n_trades']:>7} | {m['pnl_rs']:>+9.2f} | {m['pnl_pct']:>+7.2f}% | {m['win_rate']:>5.1f}% | {m['profit_factor']:>5.2f} | {m['avg_pnl']:>+7.2f}")

    # Referencia: total
    print("-" * 78)
    m_total = metrics_for_trades(
        trades, initial_balance=10000.0,
    )
    print(f"{'TOTAL':<10} | {m_total['n_trades']:>7} | {m_total['pnl_rs']:>+9.2f} | {m_total['pnl_pct']:>+7.2f}% | {m_total['win_rate']:>5.1f}% | {m_total['profit_factor']:>5.2f} | {m_total['avg_pnl']:>+7.2f}")
    print("=" * 78)

    # 8. Diagnostico rapido
    print("\nDiagnostico:")
    best_bucket = max(all_metrics.items(), key=lambda kv: kv[1]["pnl_rs"])
    worst_bucket = min(all_metrics.items(), key=lambda kv: kv[1]["pnl_rs"])
    print(f"  Melhor bucket: {best_bucket[0]} (PnL R$ {best_bucket[1]['pnl_rs']:+.2f})")
    print(f"  Pior bucket:   {worst_bucket[0]} (PnL R$ {worst_bucket[1]['pnl_rs']:+.2f})")

    if best_bucket[1]["pnl_rs"] > 0 and best_bucket[1]["profit_factor"] > 1.2:
        print(f"  >> Bucket '{best_bucket[0]}' tem edge positivo. Filtrar por regime pode ajudar.")
    else:
        print(f"  >> Nenhum bucket tem edge consistente. Regime nao ajuda.")

    # 9. Salvar
    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = os.path.join(
        args.out_dir,
        f"regime_split_{args.strategy}_{args.symbol}_{args.timeframe}_{ts}.json",
    )
    output = {
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "strategy": args.strategy,
        "strategy_name": strategy.name,
        "source": "mt5" if args.from_mt5 else "synthetic",
        "n_candles": len(candles),
        "vol_window": args.vol_window,
        "spread_points": args.spread_points,
        "commission": args.commission,
        "use_sltp": args.use_sltp,
        "overall": m_total,
        "buckets": all_metrics,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nResultado salvo em: {out_path}")


if __name__ == "__main__":
    main()