"""
Walk-forward de RegimeFilteredMAStrategy (sem look-ahead).

Em cada janela, a estrategia computa o threshold de vol com dados
APENAS passados (rolling percentile). Diferente da analise
retrospectiva do M25, esta versao e o que rodaria em producao.

Uso:
    python scripts/walk_forward_regime_filtered.py --from-mt5 --symbol WINV26 --timeframe M5
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
from src.strategies.regime_filtered_ma import RegimeFilteredMAStrategy
from scripts.backtest_volatility_breakout import (
    candles_mt5,
    candles_sinteticos,
    run_backtest,
)


def split_windows(candles: List[Candle], n_windows: int) -> List[List[Candle]]:
    if n_windows < 2:
        raise ValueError("n_windows deve ser >= 2")
    total = len(candles)
    if total < n_windows * 200:
        raise ValueError(f"Serie muito curta ({total}) para {n_windows} janelas")
    size = total // n_windows
    out = []
    for i in range(n_windows):
        start = i * size
        end = start + size if i < n_windows - 1 else total
        out.append(candles[start:end])
    return out


def run_window(
    candles: List[Candle],
    strategy_factory,
    spread_points: float = 5.0,
    commission: float = 1.0,
    use_sltp: bool = True,
    atr_sl: float = 3.0,
    atr_tp: float = 6.0,
) -> Dict[str, Any]:
    strategy = strategy_factory()
    res = run_backtest(
        candles, strategy,
        initial_balance=10000.0,
        contract_multiplier=0.20,
        contracts=1.0,
        spread_points=spread_points,
        commission_per_contract=commission,
        hold_max_candles=10,
        use_sltp=use_sltp,
        atr_mult_sl=atr_sl,
        atr_mult_tp=atr_tp,
        max_trades=0,
    )
    return {
        "n_candles": len(candles),
        "n_trades": res["total_trades"],
        "pnl_pct": res["total_pnl_pct"],
        "pnl_rs": res["total_pnl_rs"],
        "win_rate": res["win_rate"],
        "pf": res["profit_factor"],
        "max_dd_pct": res["max_drawdown_pct"],
        "sharpe": res["sharpe_ratio"],
    }


def main():
    parser = argparse.ArgumentParser(description="WF: RegimeFilteredMAStrategy")
    parser.add_argument("--from-mt5", action="store_true")
    parser.add_argument("--symbol", default="WINV26")
    parser.add_argument("--timeframe", choices=list(TIMEFRAME_MAP.keys()), default="M5")
    parser.add_argument("--n", type=int, default=20000)
    parser.add_argument("--windows", type=int, default=5)
    parser.add_argument("--vol-window", type=int, default=20)
    parser.add_argument("--vol-lookback", type=int, default=500)
    parser.add_argument("--vol-percentile", type=float, default=66.0)
    parser.add_argument("--spread-points", type=float, default=5.0)
    parser.add_argument("--commission", type=float, default=1.0)
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
        return RegimeFilteredMAStrategy(
            vol_window=args.vol_window,
            vol_lookback=args.vol_lookback,
            vol_percentile=args.vol_percentile,
        )

    print(f"\nWalk-forward: {args.windows} janelas")
    print(f"Filtro: vol_window={args.vol_window}, lookback={args.vol_lookback}, p={args.vol_percentile}")
    print()

    windows = split_windows(candles, args.windows)

    print(f"{'Fold':>4} | {'Candles':>7} | {'Trades':>6} | {'PnL%':>8} | {'Win%':>6} | {'PF':>5} | {'DD%':>6} | {'Sharpe':>7}")
    print("-" * 70)

    results = []
    for i, w in enumerate(windows):
        r = run_window(
            w, factory,
            spread_points=args.spread_points,
            commission=args.commission,
        )
        results.append({"fold": i, **r})
        print(f"{i:>4} | {r['n_candles']:>7} | {r['n_trades']:>6} | {r['pnl_pct']:>+7.2f}% | {r['win_rate']:>5.1f}% | {r['pf']:>5.2f} | {r['max_dd_pct']:>5.1f}% | {r['sharpe']:>7.2f}")

    pnls = [r["pnl_pct"] for r in results]
    pos_folds = sum(1 for p in pnls if p > 0)
    mean_pnl = sum(pnls) / len(pnls)
    print("-" * 70)
    print(f"PnL medio: {mean_pnl:+.2f}% | Folds positivos: {pos_folds}/{len(results)}")
    print(f"PnL min/max: {min(pnls):+.2f}% / {max(pnls):+.2f}%")

    # Diagnostico
    if pos_folds >= 4 and mean_pnl > 2:
        print(f"\n>> FILTRO ROBUSTO: {pos_folds}/{len(results)} folds positivos, media {mean_pnl:+.2f}%")
    elif pos_folds >= 3:
        print(f"\n>> FILTRO MARGINAL: {pos_folds}/{len(results)} folds positivos")
    else:
        print(f"\n>> FILTRO NAO ROBUSTO: {pos_folds}/{len(results)} folds positivos")

    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = os.path.join(args.out_dir, f"wf_rfma_{args.symbol}_{args.timeframe}_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "n_candles": len(candles),
            "n_windows": args.windows,
            "vol_window": args.vol_window,
            "vol_lookback": args.vol_lookback,
            "vol_percentile": args.vol_percentile,
            "folds": results,
            "mean_pnl_pct": round(mean_pnl, 2),
            "positive_folds": pos_folds,
        }, f, indent=2, default=str)
    print(f"\nResultado salvo em: {out_path}")


if __name__ == "__main__":
    main()