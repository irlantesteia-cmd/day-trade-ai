from dataclasses import dataclass
from typing import Dict, List
from .manager import AssetAllocation


@dataclass
class RebalanceOrder:
    symbol: str
    action: str  # "BUY" ou "SELL"
    quantity: float
    current_weight: float
    target_weight: float


class PortfolioRebalancer:
    def __init__(self, tolerance_threshold: float = 0.05):
        if not 0.0 <= tolerance_threshold < 1.0:
            raise ValueError("tolerance_threshold must be between 0.0 and 1.0")
        self.tolerance_threshold = tolerance_threshold

    def calculate_rebalance(
        self,
        current_positions: Dict[str, float],
        current_prices: Dict[str, float],
        target_allocations: Dict[str, AssetAllocation],
        total_equity: float,
    ) -> List[RebalanceOrder]:
        if total_equity <= 0:
            raise ValueError("total_equity must be positive")
        if not current_prices:
            raise ValueError("current_prices dictionary cannot be empty")

        orders: List[RebalanceOrder] = []

        # Todos os símbolos únicos presentes tanto nas posições quanto na alocação alvo
        all_symbols = set(current_positions.keys()) | set(target_allocations.keys())

        for sym in sorted(all_symbols):
            if sym not in current_prices or current_prices[sym] <= 0:
                raise ValueError(f"Valid price required for symbol: {sym}")

            price = current_prices[sym]
            curr_qty = current_positions.get(sym, 0.0)
            curr_val = curr_qty * price
            curr_weight = curr_val / total_equity

            target_alloc = target_allocations.get(sym)
            target_weight = target_alloc.weight if target_alloc else 0.0
            target_val = total_equity * target_weight

            weight_drift = abs(curr_weight - target_weight)

            if weight_drift >= self.tolerance_threshold:
                val_delta = target_val - curr_val
                qty_delta = val_delta / price

                action = "BUY" if qty_delta > 0 else "SELL"
                orders.append(
                    RebalanceOrder(
                        symbol=sym,
                        action=action,
                        quantity=abs(qty_delta),
                        current_weight=curr_weight,
                        target_weight=target_weight,
                    )
                )

        return orders