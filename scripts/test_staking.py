"""Teste rapido do BinanceStakingAdapter."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.adapters.binance_staking_adapter import BinanceStakingAdapter


def main():
    with BinanceStakingAdapter() as sa:
        print("Assets suportados:", sa.list_supported_assets())
        print()
        for asset in ["ETH", "SOL", "BNB", "USDT", "USDC"]:
            info = sa.get_staking_info(asset)
            apy = info.get("apy_pct")
            kind = info.get("type")
            print(f"{asset:6s}: APY {apy:>5}% ({kind})")


if __name__ == "__main__":
    main()