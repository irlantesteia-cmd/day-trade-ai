from typing import Dict, Any, List
from src.domain.models import Position


class ReconciliationMismatch:
    def __init__(self, symbol: str, internal_qty: float, broker_qty: float, reason: str):
        self.symbol = symbol
        self.internal_qty = float(internal_qty)
        self.broker_qty = float(broker_qty)
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "internal_qty": self.internal_qty,
            "broker_qty": self.broker_qty,
            "reason": self.reason,
        }


class PositionReconciler:
    def __init__(self, portfolio: Any):
        self.portfolio = portfolio

    def reconcile(self, broker_positions: Dict[str, float]) -> List[ReconciliationMismatch]:
        mismatches: List[ReconciliationMismatch] = []
        internal_positions = getattr(self.portfolio, "positions", {})

        all_symbols = set(internal_positions.keys()).union(set(broker_positions.keys()))

        for symbol in set(all_symbols):
            internal_pos = internal_positions.get(symbol)
            internal_qty = getattr(internal_pos, "quantity", 0.0) if internal_pos else 0.0
            broker_qty = broker_positions.get(symbol, 0.0)

            if abs(internal_qty - broker_qty) > 1e-6:
                if symbol not in internal_positions or internal_qty == 0.0:
                    reason = "Ghost position on broker"
                elif symbol not in broker_positions or broker_qty == 0.0:
                    reason = "Position missing on broker"
                else:
                    reason = "Quantity mismatch"

                mismatches.append(
                    ReconciliationMismatch(
                        symbol=symbol,
                        internal_qty=internal_qty,
                        broker_qty=broker_qty,
                        reason=reason,
                    )
                )

        return mismatches