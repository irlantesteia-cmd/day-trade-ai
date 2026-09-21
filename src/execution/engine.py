from typing import Optional, Dict, Any
from src.execution.broker import PaperBroker
from src.execution.portfolio import PortfolioManager
from src.domain.models import Order
from src.domain.enums import PositionSide, OrderDirection


class ExecutionEngine:
    def __init__(self, initial_balance: float = 10000.0, portfolio=None, broker=None):
        self.portfolio = portfolio if portfolio is not None else PortfolioManager(initial_balance=initial_balance)
        self.broker = broker if broker is not None else PaperBroker(initial_balance=initial_balance, portfolio=self.portfolio)
        self.broker.portfolio = self.portfolio

    def process_order(self, order: Order, current_price: float) -> Order:
        return self.broker.execute_order(order, current_price)