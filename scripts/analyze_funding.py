"""
Analise de funding rates em perpetous Binance.

Uso:
    python scripts/analyze_funding.py
    python scripts/analyze_funding.py --symbols BTCUSDT ETHUSDT SOLUSDT
    python scripts/analyze_funding.py --lookback-days 30
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.adapters.binance_futures_adapter import BinanceFuturesAdapter


DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "PEPEUSDT",
    "BNBUSDT", "LTCUSDT", "TRXUSDT", "MATICUSDT", "ATOMUSDT",
]


def main():
    parser = argparse.ArgumentParser(description="Analise de funding em perps Binance")
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    parser.add_argument("--lookback-days", type=int, default=30)
    parser.add_argument("--out-dir", default="models/benchmarks")
    args = parser.parse_args()

    print(f"Lookback: {args.lookback_days} dias | {len(args.symbols)} simbolos")
    print()

    header = (
        f"{'Symbol':<14} | {'N obs':>6} | {'Mean (8h)':>10} | {'Anualiz.':>10} | "
        f"{'% pos':>6} | {'Hint':<16}"
    )
    print(header)
    print("-" * len(header))

    results: List[Dict[str, Any]] = []

    with BinanceFuturesAdapter() as fa:
        for sym in args.symbols:
            try:
                stats = fa.funding_stats(sym, lookback_days=args.lookback_days)
                if stats.get("n_obs", 0) == 0:
                    print(f"{sym:<14} | sem dados")
                    continue
                results.append(stats)
                print(
                    f"{sym:<14} | {stats['n_obs']:>6} | "
                    f"{stats['mean_rate']*100:>9.5f}% | "
                    f"{stats['annualized_mean_pct']:>9.2f}% | "
                    f"{stats['pct_positive']*100:>5.1f}% | "
                    f"{stats['strategy_hint']:<16}"
                )
            except Exception as exc:
                print(f"{sym:<14} | erro: {exc}")

    print()

    # Ordena por anualizado descendente
    results.sort(key=lambda r: r["annualized_mean_pct"], reverse=True)

    print("Top 5 maiores funding (cash-and-carry candidates):")
    for r in results[:5]:
        print(
            f"  {r['symbol']:<14} anualizado={r['annualized_mean_pct']:+.2f}% "
            f"(% pos={r['pct_positive']*100:.0f}%)"
        )

    print()
    print("Bottom 5 (reverse funding candidates):")
    for r in results[-5:]:
        print(
            f"  {r['symbol']:<14} anualizado={r['annualized_mean_pct']:+.2f}% "
            f"(% pos={r['pct_positive']*100:.0f}%)"
        )

    # Salvar
    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = os.path.join(args.out_dir, f"funding_analysis_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "lookback_days": args.lookback_days,
            "n_symbols": len(args.symbols),
            "results": results,
        }, f, indent=2, default=str)
    print(f"\nResultado salvo em: {out_path}")


if __name__ == "__main__":
    main()