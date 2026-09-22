import pytest
from src.adapters.mt5_adapter import MT5Adapter
from src.domain.enums import OrderStatus, SignalDirection
from src.domain.models import Signal


def test_mt5_adapter_initialization_and_shutdown():
    adapter = MT5Adapter()
    assert adapter.is_connected is False

    success = adapter.initialize()
    assert success is True
    assert adapter.is_connected is True

    adapter.shutdown()
    assert adapter.is_connected is False


def test_mt5_adapter_account_info_fallback():
    adapter = MT5Adapter()
    adapter.initialize()

    info = adapter.get_account_info()
    assert "balance" in info
    assert info["balance"] > 0
    assert "equity" in info


def test_mt5_adapter_fetch_latest_bar():
    adapter = MT5Adapter()
    adapter.initialize()

    bar = adapter.fetch_latest_bar("WIN$")
    assert bar["symbol"] == "WIN$"
    assert "close" in bar
    assert bar["close"] > 0.0


def test_mt5_adapter_execute_signal():
    adapter = MT5Adapter()
    adapter.initialize()

    signal = Signal(
        symbol="WIN$",
        direction=SignalDirection.BUY,
        confidence=0.9,
        metadata={"price": 100.0},
    )
    bar = {"symbol": "WIN$", "close": 105.0}

    order = adapter.execute_signal(signal, bar)
    assert order.symbol == "WIN$"
    assert order.direction == SignalDirection.BUY
    assert order.status == OrderStatus.FILLED