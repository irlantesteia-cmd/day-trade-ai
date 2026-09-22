import logging
from typing import Dict, Any, Optional
from src.adapters.mt5_adapter import MT5Adapter
from src.domain.models import Order, Signal

logger = logging.getLogger(__name__)


class MT5ExecutionEngine:
    """
    Motor de execucao que faz a ponte entre o gerador de sinais da LiveEngine
    e a corretora via MetaTrader 5.
    """

    def __init__(self, adapter: Optional[MT5Adapter] = None):
        self.adapter = adapter or MT5Adapter()
        if not self.adapter.is_connected:
            self.adapter.initialize()

    def execute_signal(self, signal: Signal, bar: Dict[str, Any]) -> Order:
        """Envia o sinal para ser executado no MT5."""
        return self.adapter.execute_signal(signal, bar)