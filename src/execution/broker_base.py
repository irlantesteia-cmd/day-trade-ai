"""
Interface base para brokers.

Define o contrato minimo que qualquer broker (real ou simulado) deve
implementar para ser usado pelo pipeline de execucao.

Contrato unificado:
    execute_order(order: Order, current_price: float) -> Order

Nao define `is_connected` no contrato porque:
  - PaperBroker nao tem conceito de conexao
  - MT5Adapter ja expoe `is_connected` como atributo (nao metodo)
Adicionar isso ao ABC forcaria um dos dois a mudar de forma artificial.
"""
from abc import ABC, abstractmethod

from src.domain.models import Order


class Broker(ABC):
    """Interface abstrata para brokers de execucao."""

    @abstractmethod
    def execute_order(self, order: Order, current_price: float) -> Order:
        """
        Executa uma ordem.

        Deve retornar a MESMA `Order` com:
          - `status` atualizado (FILLED, REJECTED, etc.)
          - `price` efetivo (considerando slippage, se aplicavel)

        Regras:
          - Nao deve levantar excecao por rejeicao; retornar status=REJECTED
          - Deve ser idempotente em relacao a `order.order_id` (futuro)
        """
        raise NotImplementedError