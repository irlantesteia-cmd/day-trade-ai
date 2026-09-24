"""
MT5ExecutionEngine - ponte entre o pipeline de execucao e o broker.

Recebe um Broker (qualquer implementacao do contrato formal definido em
src/execution/broker_base.py). Por padrao, instancia MT5Adapter.

Suporta dois modos de chamada:
  - execute_signal(signal, bar): legado, requer broker com execute_signal
    (tipicamente MT5Adapter)
  - execute_order(order, bar): novo, requer broker com execute_order
    (contrato Broker)

Compatibilidade:
  - MT5ExecutionEngine(adapter=mt5)      -> retrocompativel (adapter = broker)
  - MT5ExecutionEngine(broker=mt5)       -> novo
  - MT5ExecutionEngine(broker=paper)     -> novo (testes)
  - MT5ExecutionEngine()                 -> cria MT5Adapter()
"""
import logging
from typing import Dict, Any, Optional

from src.adapters.mt5_adapter import MT5Adapter
from src.domain.models import Order, Signal

logger = logging.getLogger(__name__)


class MT5ExecutionEngine:
    """
    Motor de execucao que delega ordens para um Broker.

    Aceita qualquer implementacao do contrato Broker. Se nenhum for
    passado, instancia MT5Adapter como padrao.
    """

    def __init__(
        self,
        broker=None,
        adapter: Optional[MT5Adapter] = None,
    ):
        # Prioridade: broker explicito > adapter (retrocompat) > MT5Adapter()
        if broker is not None:
            self.broker = broker
        elif adapter is not None:
            self.broker = adapter
        else:
            self.broker = MT5Adapter()

        # Mantem alias `adapter` para consumidores legado que leem
        # `engine.adapter` (compatibilidade estrutural).
        self.adapter = self.broker

        # Inicializa se for um adapter MT5 e ainda nao estiver conectado
        if hasattr(self.broker, "is_connected") and not self.broker.is_connected:
            if hasattr(self.broker, "initialize"):
                self.broker.initialize()

    def execute_signal(self, signal: Signal, bar: Dict[str, Any]) -> Order:
        """
        Legado: requer broker com metodo execute_signal (ex: MT5Adapter).
        """
        if not hasattr(self.broker, "execute_signal"):
            raise AttributeError(
                f"Broker {type(self.broker).__name__} nao suporta execute_signal. "
                f"Use execute_order para o contrato Broker formal."
            )
        return self.broker.execute_signal(signal, bar)

    def execute_order(self, order: Order, bar: Dict[str, Any]) -> Order:
        """
        Contrato Broker formal: extrai o preco de bar["close"] e delega.
        """
        current_price = float(bar.get("close", 0.0))
        return self.broker.execute_order(order, current_price)