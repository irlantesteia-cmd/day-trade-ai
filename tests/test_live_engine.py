from datetime import datetime, timezone
import pytest
from src.engine.live_engine import LiveTradingEngine
from src.domain.models import Signal, Order
from src.domain.enums import SignalDirection, OrderStatus
from src.telemetry.collector import MetricsCollector


class DummyStrategy:
    def __init__(self, should_signal: bool = True):
        self.should_signal = should_signal

    def generate_signal(self, bar):
        if not self.should_signal:
            return None
        return Signal(
            symbol=bar.get("symbol", "WIN"),
            direction=SignalDirection.BUY,
            confidence=0.85,
            metadata={"price": bar.get("close", 100.0)},
        )


class DummyRiskManager:
    def __init__(self, approve: bool = True):
        self.approve = approve

    def validate_signal(self, signal):
        return self.approve


class DummyExecutionEngine:
    def execute_signal(self, signal, bar):
        return Order(
            symbol=signal.symbol,
            direction=signal.direction,
            quantity=1.0,
            price=bar.get("close", 100.0),
            status=OrderStatus.FILLED,
        )


def test_live_engine_flow_approved():
    strategy = DummyStrategy(should_signal=True)
    risk = DummyRiskManager(approve=True)
    execution = DummyExecutionEngine()
    collector = MetricsCollector()

    engine = LiveTradingEngine(
        strategy=strategy,
        risk_manager=risk,
        execution_engine=execution,
        metrics_collector=collector,
    )
    engine.start()

    bar = {"symbol": "WIN", "close": 100.0, "timestamp": datetime.now(timezone.utc)}
    order = engine.process_bar(bar)

    assert order is not None
    assert order.status == OrderStatus.FILLED
    assert collector.get_counter("bars_processed") == 1.0
    assert collector.get_counter("signals_generated") == 1.0
    assert collector.get_counter("orders_executed") == 1.0


def test_live_engine_flow_risk_rejected():
    strategy = DummyStrategy(should_signal=True)
    risk = DummyRiskManager(approve=False)
    execution = DummyExecutionEngine()
    collector = MetricsCollector()

    engine = LiveTradingEngine(
        strategy=strategy,
        risk_manager=risk,
        execution_engine=execution,
        metrics_collector=collector,
    )
    engine.start()

    bar = {"symbol": "WIN", "close": 100.0, "timestamp": datetime.now(timezone.utc)}
    order = engine.process_bar(bar)

    assert order is None
    assert collector.get_counter("signals_rejected_risk") == 1.0
    assert collector.get_counter("orders_executed") == 0.0


def test_live_engine_stopped():
    strategy = DummyStrategy(should_signal=True)
    risk = DummyRiskManager(approve=True)
    execution = DummyExecutionEngine()

    engine = LiveTradingEngine(strategy=strategy, risk_manager=risk, execution_engine=execution)
    # Não chama engine.start()

    bar = {"symbol": "WIN", "close": 100.0}
    assert engine.process_bar(bar) is None