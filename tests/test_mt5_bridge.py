import pytest
from src.adapters.mt5_adapter import MT5Adapter
from src.domain.enums import OrderStatus, SignalDirection
from src.domain.models import Signal
from src.engine.mt5_bridge import MT5ExecutionEngine
from src.main import build_system


def test_mt5_execution_engine_initialization():
    adapter = MT5Adapter()
    engine = MT5ExecutionEngine(adapter=adapter)

    assert engine.adapter.is_connected is True


def test_mt5_execution_engine_execute():
    engine = MT5ExecutionEngine()
    signal = Signal(
        symbol="WIN$",
        direction=SignalDirection.BUY,
        confidence=0.8,
        metadata={},
    )
    bar = {"symbol": "WIN$", "close": 100.0}

    order = engine.execute_signal(signal, bar)
    assert order.symbol == "WIN$"
    assert order.status == OrderStatus.FILLED


def test_build_system_with_mt5_enabled():
    system = build_system(use_mt5=True)
    assert isinstance(system["engine"].execution_engine, MT5ExecutionEngine)