"""
Walk-forward do EnsembleStrategy (vote) vs VolatilityBreakout.

Compara os dois sob janelas independentes para ver qual é mais
robusto no tempo.

Uso:
    python scripts/walkforward_ensemble.py --from-mt5 --symbol WINV26 --timeframe M5
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


from src.domain.models import Candle
from src.strategies.ensemble_strategy import EnsembleStrategy
from src.strategies.volatility_breakout import VolatilityBreakoutStrategy
from scripts.backtest_volatility_breakout import (
    candles_mt5,
    candles_sinteticos,
    run_backtest,
)


def split_windows(candles: List[Candle], n_windows: int) -> List[List[Candle]]:
    total = len(candles)
    size = total // n_windows
    out = []
    for i in range(n_windows):
        start = i * size
        end = start + size if i < n_windows - 1 else total
        out.append(candles[start:end])
    return out


def run_one(candles, strategy, sl=3.0, tp=6.0):
    res = run_backtest(
        candles, strategy,
        initial_balance=10000.0,
        contract_multiplier=0.20,
        contracts=1.0,
        spread_points=5.0,
        commission_per_contract=1.0,
        hold_max_candles=10,
        use_sltp=True,
        atr_mult_sl=sl,
        atr_mult_tp=tp,
        max_trades=0,
    )
    return {
        "trades": res["total_trades"],
        "pnl_pct": res["total_pnl_pct"],
        "win_rate": res["win_rate"],
        "pf": res["profit_factor"],
        "dd_pct": res["max_drawdown_pct"],
        "sharpe": res["sharpe_ratio"],
    }


def main():
    parser = argparse.ArgumentParser(description="WF do ensemble vs VB")
    parser.add_argument("--from-mt5", action="store_true")
    parser.add_argument("--symbol", default="WINV26")
    parser.add_argument("--timeframe", choices=list(TIMEFRAME_MAP.keys()), default="M5")
    parser.add_argument("--n", type=int, default=20000)
    parser.add_argument("--windows", type=int, default=10)
    parser.add_argument("--out-dir", default="models/benchmarks")
    args = parser.parse_args()

    if args.from_mt5:
        print(f"Buscando {args.n} candles de {args.symbol} ({args.timeframe})...")
        candles = candles_mt5(args.symbol, args.n, args.timeframe)
    else:
        print(f"Gerando {args.n} candles sinteticos...")
        candles = candles_sinteticos(args.n)

    print(f"Candles: {len(candles)}")
    windows = split_windows(candles, args.windows)

    print(f"\n{'Fold':>4} | {'Ensemble PnL%':>14} | {'Ensemble Trades':>15} | {'VB PnL%':>10} | {'VB Trades':>10}")
    print("-" * 72)

    ens_results = []
    vb_results = []

    for i, w in enumerate(windows):
        ens = EnsembleStrategy(mode="vote", min_agreement=0.5)
        vb = VolatilityBreakoutStrategy(lookback=20, vol_threshold=1.5)

        r_ens = run_one(w, ens)
        r_vb = run_one(w, vb)

        ens_results.append(r_ens)
        vb_results.append(r_vb)

        print(
            f"{i:>4} | {r_ens['pnl_pct']:>+13.2f}% | {r_ens['trades']:>15} | "
            f"{r_vb['pnl_pct']:>+9.2f}% | {r_vb['trades']:>10}"
        )

    print("-" * 72)

    for label, res in [("Ensemble", ens_results), ("VB", vb_results)]:
        pnls = [r["pnl_pct"] for r in res]
        pos = sum(1 for p in pnls if p > 0)
        mean = sum(pnls) / len(pnls)
        # Excluindo outlier (maior pnl)
        if len(pnls) > 1:
            sorted_pnls = sorted(pnls)
            mean_sem_outlier = sum(sorted_pnls[:-1]) / (len(sorted_pnls) - 1)
        else:
            mean_sem_outlier = mean
        print(
            f"{label}: media={mean:+.2f}% | folds+={pos}/{len(pnls)} | "
            f"media sem outlier={mean_sem_outlier:+.2f}%"
        )

    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out = os.path.join(args.out_dir, f"wf_ensemble_{args.symbol}_{args.timeframe}_{ts}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "ensemble": ens_results,
            "volatility_breakout": vb_results,
        }, f, indent=2, default=str)
    print(f"\nSalvo em: {out}")


if __name__ == "__main__":
    main()