"""
Testes de conformidade da interface Broker.

Verifica que PaperBroker e MT5Adapter implementam o contrato minimo
definido em src/execution/broker_base.py, e que ambos aceitam a
assinatura execute_order(order, current_price) -> Order.
"""
from unittest.mock import MagicMock, patch

import pytest

from src.domain.enums import OrderStatus
from src.domain.models import Order, SignalDirection
from src.execution.broker import PaperBroker
from src.execution.broker_base import Broker


# ---------------------------------------------------------------------------
# ABC nao pode ser instanciado diretamente
# ---------------------------------------------------------------------------

def test_broker_abc_cannot_be_instantiated():
    with pytest.raises(TypeError):
        Broker()


# ---------------------------------------------------------------------------
# PaperBroker conforme
# ---------------------------------------------------------------------------

def test_paper_broker_is_subclass_of_broker():
    assert issubclass(PaperBroker, Broker)


def test_paper_broker_implements_execute_order():
    broker = PaperBroker(initial_balance=10000.0)
    order = Order(
        symbol="WIN",
        direction=SignalDirection.BUY,
        quantity=1.0,
    )
    result = broker.execute_order(order, current_price=100.0)
    assert result is order
    assert result.status == OrderStatus.FILLED


# ---------------------------------------------------------------------------
# MT5Adapter conforme (contrato estrutural, nao herda de Broker)
# ---------------------------------------------------------------------------

def test_mt5_adapter_has_execute_order_method():
    from src.adapters.mt5_adapter import MT5Adapter

    assert hasattr(MT5Adapter, "execute_order")
    assert callable(getattr(MT5Adapter, "execute_order"))


def test_mt5_adapter_execute_order_signature_matches_paper_broker():
    """Ambos aceitam (order, current_price) -> Order."""
    import inspect

    from src.adapters.mt5_adapter import MT5Adapter

    sig_paper = inspect.signature(PaperBroker.execute_order)
    sig_mt5 = inspect.signature(MT5Adapter.execute_order)

    # Parametros devem ser os mesmos nomes: self, order, current_price
    assert list(sig_paper.parameters.keys()) == ["self", "order", "current_price"]
    assert list(sig_mt5.parameters.keys()) == ["self", "order", "current_price"]


def test_mt5_adapter_execute_order_returns_order():
    from src.adapters.mt5_adapter import MT5Adapter

    adapter = MT5Adapter()
    adapter.initialize()

    order = Order(
        symbol="WIN$",
        direction=SignalDirection.BUY,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0,
    )

    mock_result = MagicMock()
    mock_result.retcode = 10009
    mock_result.price = 100.0

    with patch("MetaTrader5.order_send", return_value=mock_result):
        result = adapter.execute_order(order, current_price=100.0)

    assert isinstance(result, Order)
    assert result is order
    assert result.status == OrderStatus.FILLED
    assert result.stop_loss == 95.0
    assert result.take_profit == 110.0


def test_mt5_adapter_execute_order_computes_sltp_when_missing():
    """Se order chega sem SL/TP, adapter calcula via SLTPCalculator."""
    from src.adapters.mt5_adapter import MT5Adapter

    adapter = MT5Adapter()
    adapter.initialize()

    order = Order(
        symbol="WIN$",
        direction=SignalDirection.BUY,
        quantity=1.0,
        # sem stop_loss nem take_profit
    )

    mock_result = MagicMock()
    mock_result.retcode = 10009
    mock_result.price = 100.0

    with patch("MetaTrader5.order_send", return_value=mock_result):
        result = adapter.execute_order(order, current_price=100.0)

    assert result.stop_loss is not None
    assert result.take_profit is not None
    assert result.stop_loss < 100.0  # BUY: SL abaixo
    assert result.take_profit > 100.0  # BUY: TP acima


def test_mt5_adapter_execute_order_rejected_when_disconnected():
    from src.adapters.mt5_adapter import MT5Adapter

    adapter = MT5Adapter()
    adapter.is_connected = False

    order = Order(
        symbol="WIN$",
        direction=SignalDirection.BUY,
        quantity=1.0,
    )
    result = adapter.execute_order(order, current_price=100.0)
    assert result.status == OrderStatus.REJECTED