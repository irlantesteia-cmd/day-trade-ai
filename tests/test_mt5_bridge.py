"""Testes do MT5ExecutionEngine - agora compativel com a interface Broker."""
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.mt5_adapter import MT5Adapter
from src.domain.enums import OrderStatus
from src.domain.models import Order, Signal, SignalDirection
from src.engine.mt5_bridge import MT5ExecutionEngine
from src.execution.broker_base import Broker


# ---------------------------------------------------------------------------
# Teste legado (mantido)
# ---------------------------------------------------------------------------

def test_mt5_execution_engine_execute():
    engine = MT5Adapter()
    engine.initialize()

    signal = Signal(
        symbol="WIN$",
        direction=SignalDirection.BUY,
        confidence=0.8,
        metadata={},
    )
    bar = {"symbol": "WIN$", "close": 100.0}

    mock_result = MagicMock()
    mock_result.retcode = 10009
    mock_result.price = 100.0

    with patch("MetaTrader5.order_send", return_value=mock_result):
        order = engine.execute_signal(signal, bar)
        assert order.symbol == "WIN$"
        assert order.status == OrderStatus.FILLED


# ---------------------------------------------------------------------------
# Testes do contrato Broker no MT5ExecutionEngine
# ---------------------------------------------------------------------------

class FakeBroker(Broker):
    """Broker minimo que implementa o contrato formal."""

    def __init__(self):
        self.orders = []

    def execute_order(self, order: Order, current_price: float) -> Order:
        self.orders.append({"order": order, "price": current_price})
        order.price = current_price
        order.status = OrderStatus.FILLED
        return order


def test_engine_accepts_broker_kwarg():
    """MT5ExecutionEngine(broker=...) com qualquer Broker."""
    fake = FakeBroker()
    engine = MT5ExecutionEngine(broker=fake)
    assert engine.broker is fake
    assert engine.adapter is fake


def test_engine_accepts_adapter_kwarg_retrocompat():
    """MT5ExecutionEngine(adapter=...) continua funcionando."""
    adapter = MT5Adapter()
    adapter.is_connected = True  # evita initialize real
    engine = MT5ExecutionEngine(adapter=adapter)
    assert engine.broker is adapter
    assert engine.adapter is adapter


def test_engine_creates_mt5_adapter_by_default():
    """Sem argumentos, instancia MT5Adapter."""
    engine = MT5ExecutionEngine()
    assert isinstance(engine.broker, MT5Adapter)
    assert isinstance(engine.adapter, MT5Adapter)


def test_execute_order_delegates_to_broker():
    """execute_order extrai preco do bar e chama broker.execute_order."""
    fake = FakeBroker()
    engine = MT5ExecutionEngine(broker=fake)

    order = Order(
        symbol="WIN$",
        direction=SignalDirection.BUY,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0,
    )
    bar = {"symbol": "WIN$", "close": 100.0}

    result = engine.execute_order(order, bar)

    assert result is order
    assert result.status == OrderStatus.FILLED
    assert result.price == 100.0
    assert len(fake.orders) == 1
    assert fake.orders[0]["price"] == 100.0


def test_execute_order_with_missing_close_falls_back_to_zero():
    """Sem bar['close'], usa 0.0 sem crashar."""
    fake = FakeBroker()
    engine = MT5ExecutionEngine(broker=fake)

    order = Order(symbol="WIN$", direction=SignalDirection.BUY, quantity=1.0)
    engine.execute_order(order, {"symbol": "WIN$"})

    assert fake.orders[0]["price"] == 0.0


def test_execute_signal_raises_when_broker_unsupported():
    """Broker sem execute_signal levanta AttributeError claro."""
    fake = FakeBroker()
    engine = MT5ExecutionEngine(broker=fake)

    signal = Signal(
        symbol="WIN$",
        direction=SignalDirection.BUY,
        confidence=0.8,
        metadata={},
    )
    with pytest.raises(AttributeError) as exc_info:
        engine.execute_signal(signal, {"symbol": "WIN$", "close": 100.0})
    assert "nao suporta execute_signal" in str(exc_info.value)
    assert "FakeBroker" in str(exc_info.value)


def test_mt5_adapter_supports_both_interfaces():
    """MT5Adapter implementa execute_signal E execute_order."""
    adapter = MT5Adapter()
    adapter.is_connected = True
    engine = MT5ExecutionEngine(adapter=adapter)

    # execute_signal existe
    assert hasattr(engine, "execute_signal")
    # execute_order existe
    assert hasattr(engine, "execute_order")
    # broker suporta ambos
    assert hasattr(engine.broker, "execute_signal")
    assert hasattr(engine.broker, "execute_order")