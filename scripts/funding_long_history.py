"""
Analise de funding em janela longa (365 dias).

Para os top candidatos do analyze_funding.py, verifica:
  - Consistencia em 30/90/180/365 dias
  - Drawdown de funding (pior janela)
  - % positivos por janela

Uso:
    python scripts/funding_long_history.py
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
    "MATICUSDT", "DOGEUSDT", "LTCUSDT", "BTCUSDT", "LINKUSDT",
    "TRXUSDT",
]


def main():
    parser = argparse.ArgumentParser(description="Funding em janelas longas")
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    parser.add_argument("--windows", nargs="+", type=int, default=[30, 90, 180, 365])
    parser.add_argument("--out-dir", default="models/benchmarks")
    args = parser.parse_args()

    print(f"Windows: {args.windows} dias | {len(args.symbols)} simbolos")
    print()

    header = f"{'Symbol':<12} | " + " | ".join(f"{w:>3}d anual%".rjust(11) for w in args.windows)
    print(header)
    print("-" * len(header))

    all_results: Dict[str, Dict[str, Any]] = {}

    with BinanceFuturesAdapter() as fa:
        for sym in args.symbols:
            row = f"{sym:<12} |"
            sym_results: Dict[str, Any] = {}
            for days in args.windows:
                try:
                    stats = fa.funding_stats(sym, lookback_days=days)
                    if stats.get("n_obs", 0) == 0:
                        row += f" {'sem dados':>11} |"
                        continue
                    anu = stats["annualized_mean_pct"]
                    row += f" {anu:>+10.2f}% |"
                    sym_results[f"{days}d"] = stats
                except Exception as exc:
                    row += f" {'erro':>11} |"
                    sym_results[f"{days}d"] = {"error": str(exc)}
            print(row)
            all_results[sym] = sym_results

    print()

    # Detalhe do BTC (o mais confiavel)
    print("Detalhe BTCUSDT por janela:")
    if "BTCUSDT" in all_results:
        for window_key, stats in all_results["BTCUSDT"].items():
            if "error" in stats:
                print(f"  {window_key}: erro")
                continue
            print(
                f"  {window_key}: n={stats['n_obs']:>4} | "
                f"mean={stats['mean_rate']*100:+.5f}% | "
                f"anual={stats['annualized_mean_pct']:+.2f}% | "
                f"%pos={stats['pct_positive']*100:.1f}% | "
                f"p05={stats['p05']*100:+.5f}%"
            )

    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = os.path.join(args.out_dir, f"funding_long_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nResultado salvo em: {out_path}")


if __name__ == "__main__":
    main()