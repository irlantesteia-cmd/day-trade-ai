from typing import Dict, List
from src.domain.enums import OrderSide, PositionSide
from src.domain.models import Order, Position


class PortfolioManager:
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.cash = initial_balance
        self.positions: Dict[str, Position] = {}
        self.order_history: List[Order] = []

    @property
    def equity(self) -> float:
        unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        return self.cash + unrealized

    @property
    def total_pnl_pct(self) -> float:
        if self.initial_balance == 0:
            return 0.0
        return ((self.equity - self.initial_balance) / self.initial_balance) * 100.0

    def update_positions_pnl(self, current_prices: Dict[str, float]):
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                price = current_prices[symbol]
                position.current_price = price
                if position.side == PositionSide.LONG:
                    position.unrealized_pnl = (price - position.entry_price) * position.quantity
                elif position.side == PositionSide.SHORT:
                    position.unrealized_pnl = (position.entry_price - price) * position.quantity