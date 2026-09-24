"""
MT5ExecutionEngine - ponte entre o pipeline de execucao e o MetaTrader 5.

Suporta dois modos de chamada:
  - execute_signal(signal, bar): legado, adapter calcula SL/TP e quantidade
  - execute_order(order, bar): novo, recebe Order ja pronta (com SL/TP
    e quantidade calculadas pelo RiskEngine)
"""
import logging
from typing import Dict, Any, Optional

from src.adapters.mt5_adapter import MT5Adapter
from src.domain.models import Order, Signal

logger = logging.getLogger(__name__)


class MT5ExecutionEngine:
    """Motor de execucao que faz a ponte entre o pipeline e o MT5."""

    def __init__(self, adapter: Optional[MT5Adapter] = None):
        self.adapter = adapter or MT5Adapter()
        if not self.adapter.is_connected:
            self.adapter.initialize()

    def execute_signal(self, signal: Signal, bar: Dict[str, Any]) -> Order:
        """
        Legado: recebe Signal e delega ao adapter (que calcula SL/TP
        e quantidade internamente).
        """
        return self.adapter.execute_signal(signal, bar)

    def execute_order(self, order: Order, bar: Dict[str, Any]) -> Order:
        """
        Novo: recebe Order ja pronta (SL/TP + quantidade definidos pelo
        RiskEngine) e delega ao adapter.execute_order.

        Extrai o preco atual de bar["close"] para passar ao adapter.
        """
        current_price = float(bar.get("close", 0.0))
        return self.adapter.execute_order(order, current_price)