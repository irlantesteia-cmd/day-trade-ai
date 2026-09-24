"""
Walk-forward da VolatilityBreakoutStrategy.

Diferente de walk-forward de ML (que treina em janela e testa em outra),
esta estrategia e baseada em regra (sem treino). Portanto walk-forward
aqui significa: rodar o backtest em multiplas janelas CONSECUTIVAS
independentes e verificar se o PnL e consistente ou concentrado.

Se PnL e concentrado em 1-2 folds: o resultado da janela completa e
enganoso (talvez um regime especifico).

Se PnL e distribuido entre folds: a estrategia e robusta ao tempo.

Uso:
    python scripts/walk_forward_vb.py --from-mt5 --symbol WINV26 --timeframe M5
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

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
from src.strategies.volatility_breakout import VolatilityBreakoutStrategy
from scripts.backtest_volatility_breakout import (
    candles_mt5,
    candles_sinteticos,
    run_backtest,
)


def split_windows(candles: List[Candle], n_windows: int) -> List[List[Candle]]:
    """Divide a serie em N janelas consecutivas de tamanho similar."""
    if n_windows < 2:
        raise ValueError("n_windows deve ser >= 2")
    total = len(candles)
    if total < n_windows * 100:
        raise ValueError(f"Serie muito curta ({total}) para {n_windows} janelas")

    size = total // n_windows
    windows = []
    for i in range(n_windows):
        start = i * size
        end = start + size if i < n_windows - 1 else total
        windows.append(candles[start:end])
    return windows


def run_walk_forward(
    candles: List[Candle],
    strategy_factory,
    n_windows: int = 5,
    initial_balance: float = 10000.0,
    spread_points: float = 5.0,
    commission: float = 1.0,
    multiplier: float = 0.20,
    hold_max: int = 10,
    use_sltp: bool = True,
    atr_sl: float = 3.0,
    atr_tp: float = 6.0,
) -> List[Dict[str, Any]]:
    windows = split_windows(candles, n_windows)
    results = []

    for i, w in enumerate(windows):
        # Cada janela roda com capital inicial proprio
        strat = strategy_factory()
        res = run_backtest(
            w, strat,
            initial_balance=initial_balance,
            contract_multiplier=multiplier,
            contracts=1.0,
            spread_points=spread_points,
            commission_per_contract=commission,
            hold_max_candles=hold_max,
            use_sltp=use_sltp,
            atr_mult_sl=atr_sl,
            atr_mult_tp=atr_tp,
        )
        results.append({
            "fold": i,
            "n_candles": len(w),
            "start": w[0].timestamp.isoformat(),
            "end": w[-1].timestamp.isoformat(),
            "pnl_pct": res["total_pnl_pct"],
            "trades": res["total_trades"],
            "win_rate": res["win_rate"],
            "profit_factor": res["profit_factor"],
            "max_dd_pct": res["max_drawdown_pct"],
            "sharpe": res["sharpe_ratio"],
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="Walk-forward VolatilityBreakout")
    parser.add_argument("--from-mt5", action="store_true")
    parser.add_argument("--symbol", default="WINV26")
    parser.add_argument("--timeframe", choices=list(TIMEFRAME_MAP.keys()), default="M5")
    parser.add_argument("--n", type=int, default=20000)
    parser.add_argument("--windows", type=int, default=5)
    parser.add_argument("--vol-threshold", type=float, default=1.5)
    parser.add_argument("--lookback", type=int, default=20)
    parser.add_argument("--spread-points", type=float, default=5.0)
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

    def factory():
        return VolatilityBreakoutStrategy(
            lookback=args.lookback,
            vol_threshold=args.vol_threshold,
        )

    print(f"\nWalk-forward: {args.windows} janelas consecutivas")
    print(f"Config: lookback={args.lookback}, vol_threshold={args.vol_threshold}")
    print(f"SL/TP: {args.atr_sl}x / {args.atr_tp}x ATR | Spread: {args.spread_points} pts")
    print()

    results = run_walk_forward(
        candles, factory,
        n_windows=args.windows,
        spread_points=args.spread_points,
        atr_sl=args.atr_sl,
        atr_tp=args.atr_tp,
    )

    # Tabela
    print(f"{'Fold':>4} | {'Candles':>7} | {'PnL%':>8} | {'Trades':>6} | {'Win%':>6} | {'PF':>5} | {'DD%':>6} | {'Sharpe':>7}")
    print("-" * 78)
    for r in results:
        print(f"{r['fold']:>4} | {r['n_candles']:>7} | {r['pnl_pct']:>+7.2f}% | {r['trades']:>6} | {r['win_rate']:>5.1f}% | {r['profit_factor']:>5.2f} | {r['max_dd_pct']:>5.1f}% | {r['sharpe']:>7.2f}")

    pnls = [r["pnl_pct"] for r in results]
    pos_folds = sum(1 for p in pnls if p > 0)
    mean_pnl = sum(pnls) / len(pnls)
    print("-" * 78)
    print(f"PnL medio: {mean_pnl:+.2f}% | Folds positivos: {pos_folds}/{len(results)}")
    print(f"PnL min/max: {min(pnls):+.2f}% / {max(pnls):+.2f}%")

    # Salvar
    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = os.path.join(args.out_dir, f"walkforward_vb_{args.symbol}_{args.timeframe}_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "source": "mt5" if args.from_mt5 else "synthetic",
            "n_candles": len(candles),
            "n_windows": args.windows,
            "vol_threshold": args.vol_threshold,
            "lookback": args.lookback,
            "atr_sl": args.atr_sl,
            "atr_tp": args.atr_tp,
            "spread_points": args.spread_points,
            "folds": results,
            "mean_pnl_pct": round(mean_pnl, 2),
            "positive_folds": pos_folds,
            "total_folds": len(results),
        }, f, indent=2, default=str)
    print(f"\nResultado salvo em: {out_path}")


if __name__ == "__main__":
    main()