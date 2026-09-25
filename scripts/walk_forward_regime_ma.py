"""
Walk-forward de MA Crossover com filtro de regime de volatilidade.

Testa a hipotese do M25: MA tem edge em regimes de alta volatilidade
e perde em regimes de baixa. Filtro de vol pode extrair valor.

Estrutura:
  - Divide candles em N janelas consecutivas
  - Em cada janela:
      a) Computa realized_vol_20 em todos os candles
      b) Calcula tercis (low/mid/high)
      c) Roda MA em cada bucket separadamente
      d) Compara: MA sem filtro vs MA so em "high vol"
  - Reporta PnL por fold

Uso:
    python scripts/walk_forward_regime_ma.py --from-mt5 --symbol WINV26 --timeframe M5
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
from src.features.volatility import RealizedVolatilityExtractor
from src.strategies.moving_average import MovingAverageCrossoverStrategy
from scripts.backtest_volatility_breakout import (
    candles_mt5,
    candles_sinteticos,
    run_backtest,
)


def compute_vol_series(
    candles: List[Candle],
    period: int = 20,
) -> List[Optional[float]]:
    extractor = RealizedVolatilityExtractor(period=period)
    vols: List[Optional[float]] = []
    for i in range(len(candles)):
        if i < period:
            vols.append(None)
            continue
        window = candles[: i + 1]
        out = extractor.extract(window, None)
        vols.append(out.get(f"realized_vol_{period}"))
    return vols


def enrich_trades_with_vol(trades, candles, vols):
    ts_to_vol = {c.timestamp.isoformat(): v for c, v in zip(candles, vols)}
    for t in trades:
        t["vol_at_entry"] = ts_to_vol.get(t.get("entry_time"))
    return trades


def split_by_tercis(trades):
    valid = [t for t in trades if t.get("vol_at_entry") is not None]
    if len(valid) < 15:
        return {"low": [], "mid": [], "high": []}
    vols = np.array([t["vol_at_entry"] for t in valid], dtype=float)
    p33 = float(np.percentile(vols, 33.333))
    p66 = float(np.percentile(vols, 66.667))
    out = {"low": [], "mid": [], "high": []}
    for t in valid:
        v = t["vol_at_entry"]
        if v <= p33:
            out["low"].append(t)
        elif v <= p66:
            out["mid"].append(t)
        else:
            out["high"].append(t)
    return out


def metrics(trades, initial_balance=10000.0):
    if not trades:
        return {"n_trades": 0, "pnl_rs": 0.0, "pnl_pct": 0.0, "win_rate": 0.0, "pf": 0.0}
    pnls = [t["pnl_rs"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gp = sum(wins) if wins else 0.0
    gl = abs(sum(losses)) if losses else 0.0
    return {
        "n_trades": len(trades),
        "pnl_rs": round(sum(pnls), 2),
        "pnl_pct": round(sum(pnls) / initial_balance * 100, 2),
        "win_rate": round(len(wins) / len(trades) * 100, 2),
        "pf": round(gp / gl, 2) if gl > 0 else 0.0,
    }


def run_window(
    candles: List[Candle],
    vol_window: int = 20,
    spread_points: float = 5.0,
    commission: float = 1.0,
    use_sltp: bool = True,
    atr_sl: float = 3.0,
    atr_tp: float = 6.0,
) -> Dict[str, Any]:
    """Roda MA em uma janela e retorna metricas por bucket."""
    strategy = MovingAverageCrossoverStrategy()
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

    if not res["trades"]:
        return {
            "n_candles": len(candles),
            "total": metrics([]),
            "low": metrics([]),
            "mid": metrics([]),
            "high": metrics([]),
            "high_filtered_pnl_pct": 0.0,
        }

    vols = compute_vol_series(candles, period=vol_window)
    trades = enrich_trades_with_vol(res["trades"], candles, vols)
    buckets = split_by_tercis(trades)

    return {
        "n_candles": len(candles),
        "total": metrics(trades),
        "low": metrics(buckets["low"]),
        "mid": metrics(buckets["mid"]),
        "high": metrics(buckets["high"]),
        "high_filtered_pnl_pct": metrics(buckets["high"])["pnl_pct"],
    }


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


def main():
    parser = argparse.ArgumentParser(description="WF: MA + filtro de regime")
    parser.add_argument("--from-mt5", action="store_true")
    parser.add_argument("--symbol", default="WINV26")
    parser.add_argument("--timeframe", choices=list(TIMEFRAME_MAP.keys()), default="M5")
    parser.add_argument("--n", type=int, default=20000)
    parser.add_argument("--windows", type=int, default=5)
    parser.add_argument("--vol-window", type=int, default=20)
    parser.add_argument("--spread-points", type=float, default=5.0)
    parser.add_argument("--commission", type=float, default=1.0)
    parser.add_argument("--use-sltp", action="store_true", default=True)
    parser.add_argument("--out-dir", default="models/benchmarks")
    args = parser.parse_args()

    if args.from_mt5:
        print(f"Buscando {args.n} candles de {args.symbol} ({args.timeframe})...")
        candles = candles_mt5(args.symbol, args.n, args.timeframe)
    else:
        print(f"Gerando {args.n} candles sinteticos...")
        candles = candles_sinteticos(args.n)

    print(f"Candles: {len(candles)}")
    print(f"\nWalk-forward: {args.windows} janelas | filtro: realized_vol_{args.vol_window}")

    windows = split_windows(candles, args.windows)

    print(f"\n{'Fold':>4} | {'Total PnL%':>10} | {'Total PF':>8} | {'Low PnL%':>9} | {'Mid PnL%':>9} | {'High PnL%':>9} | {'High PF':>7}")
    print("-" * 80)

    results = []
    for i, w in enumerate(windows):
        res = run_window(
            w, vol_window=args.vol_window,
            spread_points=args.spread_points,
            commission=args.commission,
        )
        results.append({"fold": i, **res})
        print(
            f"{i:>4} | {res['total']['pnl_pct']:>+9.2f}% | {res['total']['pf']:>8.2f} | "
            f"{res['low']['pnl_pct']:>+8.2f}% | {res['mid']['pnl_pct']:>+8.2f}% | "
            f"{res['high']['pnl_pct']:>+8.2f}% | {res['high']['pf']:>7.2f}"
        )

    print("-" * 80)

    # Agregados
    totals = [r["total"]["pnl_pct"] for r in results]
    lows = [r["low"]["pnl_pct"] for r in results]
    mids = [r["mid"]["pnl_pct"] for r in results]
    highs = [r["high"]["pnl_pct"] for r in results]

    print(f"\nPnL medio por bucket:")
    print(f"  total (sem filtro):  {sum(totals)/len(totals):+.2f}% | folds+: {sum(1 for x in totals if x>0)}/{len(totals)}")
    print(f"  low vol:             {sum(lows)/len(lows):+.2f}% | folds+: {sum(1 for x in lows if x>0)}/{len(lows)}")
    print(f"  mid vol:             {sum(mids)/len(mids):+.2f}% | folds+: {sum(1 for x in mids if x>0)}/{len(mids)}")
    print(f"  high vol (filtro):   {sum(highs)/len(highs):+.2f}% | folds+: {sum(1 for x in highs if x>0)}/{len(highs)}")

    # Diagnostico
    print(f"\nDiagnostico:")
    if sum(1 for x in highs if x > 0) >= 4 and sum(highs)/len(highs) > 3:
        print(f"  >> Filtro 'high vol' e ROBUSTO: {sum(1 for x in highs if x>0)}/{len(highs)} folds positivos, media {sum(highs)/len(highs):+.2f}%")
    elif sum(1 for x in highs if x > 0) >= 3:
        print(f"  >> Filtro 'high vol' e marginal: {sum(1 for x in highs if x>0)}/{len(highs)} folds positivos")
    else:
        print(f"  >> Filtro nao e robusto: {sum(1 for x in highs if x>0)}/{len(highs)} folds positivos")

    # Salvar
    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = os.path.join(
        args.out_dir,
        f"wf_regime_ma_{args.symbol}_{args.timeframe}_{ts}.json",
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "n_candles": len(candles),
            "n_windows": args.windows,
            "vol_window": args.vol_window,
            "folds": results,
            "summary": {
                "total_mean_pnl_pct": round(sum(totals)/len(totals), 2),
                "low_mean_pnl_pct": round(sum(lows)/len(lows), 2),
                "mid_mean_pnl_pct": round(sum(mids)/len(mids), 2),
                "high_mean_pnl_pct": round(sum(highs)/len(highs), 2),
                "high_positive_folds": sum(1 for x in highs if x > 0),
                "total_positive_folds": sum(1 for x in totals if x > 0),
            },
        }, f, indent=2, default=str)
    print(f"\nResultado salvo em: {out_path}")


if __name__ == "__main__":
    main()