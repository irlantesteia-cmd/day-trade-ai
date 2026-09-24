from datetime import datetime, timezone

import pytest

from src.engine.live_engine import LiveTradingEngine
from src.domain.models import Signal, Order
from src.domain.enums import SignalDirection, OrderStatus
from src.telemetry.collector import MetricsCollector


# ---------------------------------------------------------------------------
# Doubles (usados nos testes legado e novo)
# ---------------------------------------------------------------------------

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


class DummyRiskEngine:
    """Simula RiskEngine: gera Order com SL/TP e quantidade."""
    def __init__(self, produce_order: bool = True):
        self.produce_order = produce_order
        self.calls = []

    def generate_order(self, signal, current_price, account_balance):
        self.calls.append({
            "signal": signal,
            "current_price": current_price,
            "account_balance": account_balance,
        })
        if not self.produce_order:
            return None
        return Order(
            symbol=signal.symbol,
            direction=signal.direction,
            quantity=2.0,
            price=current_price,
            stop_loss=current_price - 5.0,
            take_profit=current_price + 10.0,
            status=OrderStatus.PENDING,
        )


class DummyExecutionEngineWithExecuteOrder:
    """Execution engine que expoe execute_order (novo contrato)."""
    def __init__(self):
        self.orders_received = []

    def execute_order(self, order, bar):
        self.orders_received.append(order)
        order.status = OrderStatus.FILLED
        return order


# ---------------------------------------------------------------------------
# Testes LEGADO (mantidos)
# ---------------------------------------------------------------------------

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

    bar = {"symbol": "WIN", "close": 100.0}
    assert engine.process_bar(bar) is None


# ---------------------------------------------------------------------------
# Testes NOVO fluxo (risk_engine presente)
# ---------------------------------------------------------------------------

def test_live_engine_risk_engine_generates_order_and_executes():
    strategy = DummyStrategy(should_signal=True)
    risk_engine = DummyRiskEngine(produce_order=True)
    execution = DummyExecutionEngineWithExecuteOrder()
    collector = MetricsCollector()

    engine = LiveTradingEngine(
        strategy=strategy,
        execution_engine=execution,
        risk_engine=risk_engine,
        metrics_collector=collector,
    )
    engine.start()

    bar = {"symbol": "WIN", "close": 100.0}
    order = engine.process_bar(bar)

    assert order is not None
    assert order.status == OrderStatus.FILLED
    assert order.quantity == 2.0
    assert order.stop_loss == 95.0
    assert order.take_profit == 110.0
    # Order que o execution engine recebeu deve ser a mesma
    assert len(execution.orders_received) == 1
    assert execution.orders_received[0] is order
    # Risk engine foi chamado 1 vez
    assert len(risk_engine.calls) == 1
    assert risk_engine.calls[0]["current_price"] == 100.0


def test_live_engine_risk_engine_rejects_returns_none():
    strategy = DummyStrategy(should_signal=True)
    risk_engine = DummyRiskEngine(produce_order=False)
    execution = DummyExecutionEngineWithExecuteOrder()
    collector = MetricsCollector()

    engine = LiveTradingEngine(
        strategy=strategy,
        execution_engine=execution,
        risk_engine=risk_engine,
        metrics_collector=collector,
    )
    engine.start()

    bar = {"symbol": "WIN", "close": 100.0}
    order = engine.process_bar(bar)

    assert order is None
    assert len(execution.orders_received) == 0
    assert collector.get_counter("signals_rejected_risk") == 1.0
    assert collector.get_counter("orders_executed") == 0.0


def test_live_engine_risk_engine_uses_balance_from_portfolio():
    """Se execution_engine.portfolio.equity existe, deve ir para generate_order."""
    strategy = DummyStrategy(should_signal=True)
    risk_engine = DummyRiskEngine(produce_order=True)
    execution = DummyExecutionEngineWithExecuteOrder()
    execution.portfolio = type("P", (), {"equity": 50000.0})()

    engine = LiveTradingEngine(
        strategy=strategy,
        execution_engine=execution,
        risk_engine=risk_engine,
    )
    engine.start()
    engine.process_bar({"symbol": "WIN", "close": 100.0})

    assert risk_engine.calls[0]["account_balance"] == 50000.0



# ---------------------------------------------------------------------------
# Testes de sincronizacao de estado (Milestone 11)
# ---------------------------------------------------------------------------

class SpyRiskManager:
    """RiskManager real (nao mock) que registra chamadas a update_state."""

    def __init__(self, max_open_positions: int = 3):
        self.calls = []
        self.daily_pnl_pct = 0.0
        self.open_positions_count = 0
        self.max_open_positions = max_open_positions

    def update_state(self, daily_pnl_pct: float, open_positions_count: int):
        self.calls.append({
            "daily_pnl_pct": daily_pnl_pct,
            "open_positions_count": open_positions_count,
        })
        self.daily_pnl_pct = daily_pnl_pct
        self.open_positions_count = open_positions_count

    def can_take_trade(self) -> bool:
        if self.open_positions_count >= self.max_open_positions:
            return False
        return True


class RiskEngineWithSpyManager:
    """RiskEngine fake que usa SpyRiskManager e respeita can_take_trade."""

    def __init__(self, spy_manager):
        self.manager = spy_manager

    def generate_order(self, signal, current_price, account_balance):
        if not self.manager.can_take_trade():
            return None
        return Order(
            symbol=signal.symbol,
            direction=signal.direction,
            quantity=1.0,
            price=current_price,
            status=OrderStatus.PENDING,
        )


def test_risk_manager_update_state_called_each_bar():
    """update_state deve ser chamado a cada barra processada."""
    spy = SpyRiskManager()
    risk_engine = RiskEngineWithSpyManager(spy)

    engine = LiveTradingEngine(
        strategy=DummyStrategy(should_signal=True),
        execution_engine=DummyExecutionEngineWithExecuteOrder(),
        risk_engine=risk_engine,
    )
    engine.start()

    engine.process_bar({"symbol": "WIN", "close": 100.0})
    engine.process_bar({"symbol": "WIN", "close": 101.0})

    assert len(spy.calls) == 2
    for call in spy.calls:
        assert call["daily_pnl_pct"] == 0.0  # limitacao documentada
        assert call["open_positions_count"] == 0  # portfolio vazio


def test_risk_manager_blocks_when_max_positions_reached():
    """Se portfolio tem N posicoes abertas >= max_open_positions, rejeita."""
    spy = SpyRiskManager(max_open_positions=2)
    risk_engine = RiskEngineWithSpyManager(spy)

    engine = LiveTradingEngine(
        strategy=DummyStrategy(should_signal=True),
        execution_engine=DummyExecutionEngineWithExecuteOrder(),
        risk_engine=risk_engine,
    )
    engine.start()

    # Simula 2 posicoes abertas no portfolio do execution engine
    engine.execution_engine.portfolio = type("P", (), {
        "positions": {"WIN": 1, "PETR4": 2},
        "equity": 10000.0,
    })()

    order = engine.process_bar({"symbol": "WIN", "close": 100.0})

    assert order is None
    assert len(spy.calls) == 1
    assert spy.calls[0]["open_positions_count"] == 2


def test_risk_manager_allows_when_below_max_positions():
    """Com N < max_open_positions, permite gerar Order."""
    spy = SpyRiskManager(max_open_positions=3)
    risk_engine = RiskEngineWithSpyManager(spy)

    engine = LiveTradingEngine(
        strategy=DummyStrategy(should_signal=True),
        execution_engine=DummyExecutionEngineWithExecuteOrder(),
        risk_engine=risk_engine,
    )
    engine.start()

    engine.execution_engine.portfolio = type("P", (), {
        "positions": {"WIN": 1},
        "equity": 10000.0,
    })()

    order = engine.process_bar({"symbol": "WIN", "close": 100.0})

    assert order is not None
    assert spy.calls[0]["open_positions_count"] == 1