"""
ExecutionEngine - motor de execucao de ordens via broker.

Consolida o que antes era duplicado entre engine.py e executor.py.
Mantem salvaguardas defensivas (cash, balance, positions) herdadas
do antigo executor.py.

Usa AccountState (nao PortfolioManager) para o estado financeiro da conta.
"""
from typing import Optional

from src.execution.broker import PaperBroker
from src.execution.portfolio import AccountState
from src.domain.models import Order


class ExecutionEngine:
    def __init__(
        self,
        initial_balance: float = 10000.0,
        broker=None,
        portfolio=None,
    ):
        self.portfolio = (
            portfolio
            if portfolio is not None
            else AccountState(initial_balance=initial_balance)
        )

        # Salvaguardas defensivas: garantir atributos minimos esperados
        if not hasattr(self.portfolio, "cash") and hasattr(self.portfolio, "balance"):
            self.portfolio.cash = self.portfolio.balance
        if not hasattr(self.portfolio, "positions"):
            self.portfolio.positions = {}

        if broker is not None:
            self.broker = broker
        else:
            self.broker = PaperBroker(initial_balance=initial_balance)

        # Sincroniza portfolio do broker com o do engine
        self.broker.portfolio = self.portfolio

    def process_order(self, order: Order, current_price: float) -> Order:
        return self.broker.execute_order(order, current_price)