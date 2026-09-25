"""
Backtest do EnsembleStrategy vs estrategias individuais.

Compara:
  - EnsembleStrategy (mode vote) com 4 estrategias
  - MA Crossover isolado
  - RSI Reversion isolado
  - VolatilityBreakout isolado

Todos com o mesmo motor de backtest (custo + SL/TP) em WINV26 M5.

Uso:
    python scripts/backtest_ensemble.py --from-mt5 --symbol WINV26 --timeframe M5
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


TIMEFRAME_MAP = {
    "M1":  "TIMEFRAME_M1",
    "M5":  "TIMEFRAME_M5",
    "M15": "TIMEFRAME_M15",
    "M30": "TIMEFRAME_M30",
    "H1":  "TIMEFRAME_H1",
}


from src.strategies.ensemble_strategy import EnsembleStrategy
from src.strategies.moving_average import MovingAverageCrossoverStrategy
from src.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from src.strategies.volatility_breakout import VolatilityBreakoutStrategy
from scripts.backtest_volatility_breakout import (
    candles_mt5,
    candles_sinteticos,
    run_backtest,
)


def build_strategies() -> Dict[str, Any]:
    return {
        "ENSEMBLE_VOTE": EnsembleStrategy(mode="vote", min_agreement=0.5),
        "ENSEMBLE_UNANIMOUS": EnsembleStrategy(mode="unanimous"),
        "MA_CROSSOVER": MovingAverageCrossoverStrategy(),
        "RSI_REVERSION": RSIMeanReversionStrategy(rsi_key="rsi"),
        "VOLATILITY_BREAKOUT": VolatilityBreakoutStrategy(lookback=20, vol_threshold=1.5),
    }


def main():
    parser = argparse.ArgumentParser(description="Backtest ensemble vs individuais")
    parser.add_argument("--from-mt5", action="store_true")
    parser.add_argument("--symbol", default="WINV26")
    parser.add_argument("--timeframe", choices=list(TIMEFRAME_MAP.keys()), default="M5")
    parser.add_argument("--n", type=int, default=20000)
    parser.add_argument("--spread-points", type=float, default=5.0)
    parser.add_argument("--commission", type=float, default=1.0)
    parser.add_argument("--multiplier", type=float, default=0.20)
    parser.add_argument("--use-sltp", action="store_true", default=True)
    parser.add_argument("--atr-sl", type=float, default=3.0)
    parser.add_argument("--atr-tp", type=float, default=6.0)
    parser.add_argument("--out-dir", default="models/benchmarks")
    args = parser.parse_args()

    if args.from_mt5:
        print(f"Buscando {args.n} candles de {args.symbol} ({args.timeframe})...")
        candles = candles_mt5(args.symbol, args.n, args.timeframe)
    else:
        print(f"Gerando {args.n} candles sinteticos...")
        candles = candles_sinteticos(args.n)

    print(f"Candles: {len(candles)}")

    strategies = build_strategies()

    print(f"\nBacktest | custos: {args.spread_points}pts + R${args.commission}/contrato")
    print(f"SL/TP: {args.atr_sl}x / {args.atr_tp}x ATR")
    print()

    header = (
        f"{'Estrategia':<22} | {'Trades':>7} | {'PnL%':>8} | {'Win%':>6} | "
        f"{'PF':>5} | {'DD%':>6} | {'Sharpe':>7}"
    )
    print(header)
    print("-" * len(header))

    results: Dict[str, Any] = {}

    for name, strategy in strategies.items():
        res = run_backtest(
            candles, strategy,
            initial_balance=10000.0,
            contract_multiplier=args.multiplier,
            contracts=1.0,
            spread_points=args.spread_points,
            commission_per_contract=args.commission,
            hold_max_candles=10,
            use_sltp=args.use_sltp,
            atr_mult_sl=args.atr_sl,
            atr_mult_tp=args.atr_tp,
            max_trades=0,
        )
        results[name] = {
            "total_trades": res["total_trades"],
            "pnl_pct": res["total_pnl_pct"],
            "win_rate": res["win_rate"],
            "pf": res["profit_factor"],
            "dd_pct": res["max_drawdown_pct"],
            "sharpe": res["sharpe_ratio"],
            "exits_by_reason": res.get("exits_by_reason", {}),
        }
        print(
            f"{name:<22} | {res['total_trades']:>7} | "
            f"{res['total_pnl_pct']:>+7.2f}% | {res['win_rate']:>5.1f}% | "
            f"{res['profit_factor']:>5.2f} | {res['max_drawdown_pct']:>5.1f}% | "
            f"{res['sharpe_ratio']:>7.2f}"
        )

    print()

    # Ranking
    ranking = sorted(
        results.items(),
        key=lambda kv: kv[1]["pnl_pct"],
        reverse=True,
    )
    print("Ranking por PnL:")
    for i, (name, r) in enumerate(ranking, 1):
        marker = " <<<" if i == 1 else ""
        print(f"  {i}. {name:<22} {r['pnl_pct']:+.2f}% (DD {r['dd_pct']:.1f}%){marker}")

    # Salvar
    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = os.path.join(args.out_dir, f"backtest_ensemble_{args.symbol}_{args.timeframe}_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "source": "mt5" if args.from_mt5 else "synthetic",
            "n_candles": len(candles),
            "spread_points": args.spread_points,
            "commission": args.commission,
            "atr_sl": args.atr_sl,
            "atr_tp": args.atr_tp,
            "results": results,
        }, f, indent=2, default=str)
    print(f"\nResultado salvo em: {out_path}")


if __name__ == "__main__":
    main()