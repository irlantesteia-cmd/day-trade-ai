"""
Relatorio consolidado de yields estruturalmente disponiveis.

Uso:
    python scripts/yield_report.py
"""
import sys
import os
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.yields.yield_aggregator import YieldAggregator, RISK_FREE


def main():
    with YieldAggregator() as agg:
        # Tabela completa
        comp = agg.compare_to_risk_free()

        print(f"{'Asset':<10} | {'Category':<8} | {'Source':<28} | {'APY':>6} | {'RF':>5} | {'Spread':>7} | {'Beats?':>6}")
        print("-" * 92)
        for c in comp:
            beats = "SIM" if c["beats_risk_free"] else "NAO"
            print(
                f"{c['asset']:<10} | {c['category']:<8} | {c['source']:<28} | "
                f"{c['apy_pct']:>5.2f}% | {c['risk_free_pct']:>4.1f}% | "
                f"{c['spread_pct']:>+6.2f}% | {beats:>6}"
            )

        print()
        print("Risk-free de referencia:")
        for k, v in RISK_FREE.items():
            print(f"  {v['name']:<24} {v['apy_pct']:>5.2f}% ({v['currency']})")

        print()
        s = agg.summary()
        print(f"Total de oportunidades: {s['n_opportunities']}")
        print(f"Que batem risk-free:    {s['n_beats_risk_free']}")

        # Salvar
        os.makedirs("models/benchmarks", exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        out = f"models/benchmarks/yield_report_{ts}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, default=str)
        print(f"\nRelatorio salvo em: {out}")


if __name__ == "__main__":
    main()