"""Teste rapido do DefiLendingAdapter."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.adapters.defi_lending_adapter import DefiLendingAdapter


def main():
    with DefiLendingAdapter() as la:
        print("Protocolos:", la.list_protocols())
        print("Assets:", la.list_assets())
        print()
        print("Todos os yields:")
        for r in la.all_rates():
            print(
                f"  {r['protocol']:14s} {r['asset']:6s}: "
                f"{r['supply_apy_pct']:>5}% supply  |  "
                f"{r['borrow_apy_pct']:>5}% borrow  |  "
                f"util {r['utilization_pct']:>5}%"
            )
        print()
        print("Melhor rate para USDC:")
        best = la.best_rate("USDC")
        print(f"  {best['protocol']} -> {best['supply_apy_pct']}%")


if __name__ == "__main__":
    main()