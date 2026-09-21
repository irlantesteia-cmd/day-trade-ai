from typing import Dict, Any


class PortfolioManager:
    def __init__(self, initial_balance: float = 10000.0):
        self.cash: float = initial_balance
        self.balance: float = initial_balance
        self.positions: Dict[str, Any] = {}

    @property
    def equity(self) -> float:
        unrealized = 0.0
        for p in self.positions.values():
            val = getattr(p, "unrealized_pnl", None)
            if val is None:
                val = getattr(p, "pnl", 0.0)
            unrealized += float(val or 0.0)
        return self.cash + unrealized

    def add_position(self, position):
        symbol = getattr(position, "symbol", None)
        if symbol:
            self.positions[symbol] = position

    def remove_position(self, symbol: str):
        if symbol in self.positions:
            del self.positions[symbol]

    def deposit(self, amount: float):
        self.cash += amount
        self.balance = self.cash

    def withdraw(self, amount: float):
        self.cash -= amount
        self.balance = self.cash

    def update_positions_pnl(self, current_prices: Dict[str, float]):
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                price = current_prices[symbol]
                if hasattr(position, "current_price"):
                    position.current_price = price
                
                side_val = getattr(position, "side", None)
                is_long = True
                if side_val is not None:
                    val = getattr(side_val, "value", str(side_val))
                    is_long = str(val).upper() in ["LONG", "BUY"]
                    
                entry = getattr(position, "entry_price", price)
                qty = getattr(position, "quantity", 0.0)
                pnl = (price - entry) * qty if is_long else (entry - price) * qty
                if hasattr(position, "unrealized_pnl"):
                    position.unrealized_pnl = pnl
                if hasattr(position, "pnl"):
                    position.pnl = pnl