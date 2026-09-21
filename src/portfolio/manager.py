from dataclasses import dataclass
from typing import Dict, List


@dataclass
class AssetAllocation:
    symbol: str
    weight: float
    target_capital: float


class PortfolioManager:
    def __init__(self, total_capital: float, max_asset_weight: float = 1.0):
        if total_capital <= 0:
            raise ValueError("total_capital must be positive")
        if not 0.0 < max_asset_weight <= 1.0:
            raise ValueError("max_asset_weight must be between 0.0 and 1.0")
        self.total_capital = total_capital
        self.max_asset_weight = max_asset_weight

    def allocate_equal_weight(self, symbols: List[str]) -> Dict[str, AssetAllocation]:
        if not symbols:
            raise ValueError("Symbols list cannot be empty")

        unique_symbols = list(dict.fromkeys(symbols))
        raw_weight = 1.0 / len(unique_symbols)
        weight = min(raw_weight, self.max_asset_weight)

        allocations = {}
        for sym in unique_symbols:
            cap = self.total_capital * weight
            allocations[sym] = AssetAllocation(symbol=sym, weight=weight, target_capital=cap)
        return allocations

    def allocate_custom_weights(self, weights: Dict[str, float]) -> Dict[str, AssetAllocation]:
        if not weights:
            raise ValueError("Weights dictionary cannot be empty")

        total_w = sum(weights.values())
        if total_w <= 0:
            raise ValueError("Sum of weights must be greater than zero")

        allocations = {}
        for sym, w in weights.items():
            if w < 0:
                raise ValueError(f"Weight for {sym} cannot be negative")
            norm_weight = w / total_w
            capped_weight = min(norm_weight, self.max_asset_weight)
            cap = self.total_capital * capped_weight
            allocations[sym] = AssetAllocation(symbol=sym, weight=capped_weight, target_capital=cap)
        return allocations