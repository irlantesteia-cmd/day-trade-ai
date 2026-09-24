"""Testes do EventBus e Event."""
import pytest

from src.events import Event, EventBus, EventType


# ---------------------------------------------------------------------------
# Event / EventType
# ---------------------------------------------------------------------------

def test_event_type_has_expected_members():
    names = {e.name for e in EventType}
    expected = {
        "MARKET_DATA_RECEIVED", "CANDLE_CLOSED",
        "SIGNAL_GENERATED", "SIGNAL_REJECTED",
        "RISK_APPROVED", "RISK_REJECTED", "RISK_LIMIT_REACHED",
        "ORDER_CREATED", "ORDER_FILLED", "ORDER_REJECTED",
        "POSITION_OPENED", "POSITION_CLOSED",
        "STOP_LOSS_TRIGGERED", "TAKE_PROFIT_TRIGGERED",
        "SYSTEM_ERROR",
    }
    assert expected.issubset(names)


def test_event_to_dict():
    e = Event(event_type=EventType.SIGNAL_GENERATED, payload={"symbol": "WIN"})
    d = e.to_dict()
    assert d["event_type"] == "SignalGenerated"
    assert d["payload"] == {"symbol": "WIN"}
    assert d["correlation_id"] is None
    assert "timestamp" in d


# ---------------------------------------------------------------------------
# Subscricao e publicacao
# ---------------------------------------------------------------------------

def test_publish_calls_specific_handler():
    bus = EventBus()
    received = []
    bus.subscribe(EventType.SIGNAL_GENERATED, lambda e: received.append(e))

    bus.publish(Event(event_type=EventType.SIGNAL_GENERATED))
    assert len(received) == 1
    assert received[0].event_type == EventType.SIGNAL_GENERATED


def test_publish_does_not_call_other_handlers():
    bus = EventBus()
    received = []
    bus.subscribe(EventType.SIGNAL_GENERATED, lambda e: received.append("gen"))
    bus.subscribe(EventType.ORDER_FILLED, lambda e: received.append("fill"))

    bus.publish(Event(event_type=EventType.SIGNAL_GENERATED))
    assert received == ["gen"]


def test_wildcard_handler_receives_all():
    bus = EventBus()
    received = []
    bus.subscribe_all(lambda e: received.append(e.event_type.value))

    bus.publish(Event(event_type=EventType.SIGNAL_GENERATED))
    bus.publish(Event(event_type=EventType.ORDER_FILLED))

    assert received == ["SignalGenerated", "OrderFilled"]


def test_multiple_handlers_called_in_order():
    bus = EventBus()
    order = []
    bus.subscribe(EventType.SIGNAL_GENERATED, lambda e: order.append("a"))
    bus.subscribe(EventType.SIGNAL_GENERATED, lambda e: order.append("b"))
    bus.subscribe(EventType.SIGNAL_GENERATED, lambda e: order.append("c"))

    bus.publish(Event(event_type=EventType.SIGNAL_GENERATED))
    assert order == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# Tratamento de erros
# ---------------------------------------------------------------------------

def test_handler_exception_does_not_break_others():
    bus = EventBus()
    received = []

    def bad_handler(e):
        raise RuntimeError("boom")

    bus.subscribe(EventType.SIGNAL_GENERATED, bad_handler)
    bus.subscribe(EventType.SIGNAL_GENERATED, lambda e: received.append("ok"))

    # Nao deve levantar
    bus.publish(Event(event_type=EventType.SIGNAL_GENERATED))
    assert received == ["ok"]


def test_publish_rejects_non_event():
    bus = EventBus()
    with pytest.raises(TypeError):
        bus.publish({"not": "an event"})


# ---------------------------------------------------------------------------
# Historico
# ---------------------------------------------------------------------------

def test_history_disabled_by_default():
    bus = EventBus()
    bus.publish(Event(event_type=EventType.SIGNAL_GENERATED))
    assert bus.get_history() == []


def test_history_records_when_enabled():
    bus = EventBus(keep_history=True)
    bus.publish(Event(event_type=EventType.SIGNAL_GENERATED))
    bus.publish(Event(event_type=EventType.ORDER_FILLED))
    assert len(bus.get_history()) == 2


def test_history_capped_at_max():
    bus = EventBus(keep_history=True, max_history=3)
    for _ in range(5):
        bus.publish(Event(event_type=EventType.SIGNAL_GENERATED))
    assert len(bus.get_history()) == 3


def test_clear_history():
    bus = EventBus(keep_history=True)
    bus.publish(Event(event_type=EventType.SIGNAL_GENERATED))
    bus.clear_history()
    assert bus.get_history() == []


# ---------------------------------------------------------------------------
# Unsubscribe / clear
# ---------------------------------------------------------------------------

def test_unsubscribe_removes_handler():
    bus = EventBus()
    received = []

    def h(e):
        received.append(e)

    bus.subscribe(EventType.SIGNAL_GENERATED, h)
    bus.publish(Event(event_type=EventType.SIGNAL_GENERATED))
    assert len(received) == 1

    bus.unsubscribe(EventType.SIGNAL_GENERATED, h)
    bus.publish(Event(event_type=EventType.SIGNAL_GENERATED))
    assert len(received) == 1  # nao incrementou


def test_clear_removes_all_handlers():
    bus = EventBus()
    bus.subscribe(EventType.SIGNAL_GENERATED, lambda e: None)
    bus.subscribe_all(lambda e: None)
    assert bus.handlers_count() == 2

    bus.clear()
    assert bus.handlers_count() == 0


# ---------------------------------------------------------------------------
# Introspeccao
# ---------------------------------------------------------------------------

def test_handlers_count_specific_and_total():
    bus = EventBus()
    bus.subscribe(EventType.SIGNAL_GENERATED, lambda e: None)
    bus.subscribe(EventType.SIGNAL_GENERATED, lambda e: None)
    bus.subscribe(EventType.ORDER_FILLED, lambda e: None)
    bus.subscribe_all(lambda e: None)

    assert bus.handlers_count(EventType.SIGNAL_GENERATED) == 3  # 2 + wildcard
    assert bus.handlers_count(EventType.ORDER_FILLED) == 2      # 1 + wildcard
    assert bus.handlers_count() == 4                            # 3 + 1