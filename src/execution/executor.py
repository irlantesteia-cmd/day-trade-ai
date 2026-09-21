from typing import Optional
from src.domain.models import Order
from src.execution.broker import PaperBroker
from src.execution.portfolio import PortfolioManager


class ExecutionEngine:
    def __init__(self, initial_balance: float = 10000.0):
        self.portfolio = PortfolioManager(initial_balance=initial_balance)
        self.broker = PaperBroker(self.portfolio)

    def process_order(self, order: Optional[Order], current_price: float) -> Optional[Order]:
        if not order:
            return None

        return self.broker.execute_order(order, current_price)