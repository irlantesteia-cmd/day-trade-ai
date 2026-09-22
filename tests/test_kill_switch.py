import pytest
from src.engine.kill_switch import KillSwitch, CircuitBreakerStatus
from src.telemetry.alerts import Alert, AlertLevel


class DummyEngine:
    def __init__(self):
        self.is_running = True

    def stop(self):
        self.is_running = False


def test_kill_switch_manual_trip():
    engine = DummyEngine()
    ks = KillSwitch(engine)
    assert ks.status == CircuitBreakerStatus.ARMED

    ks.trip("Manual emergency shutdown")
    assert ks.status == CircuitBreakerStatus.TRIPPED
    assert engine.is_running is False
    assert ks.trip_reason == "Manual emergency shutdown"


def test_kill_switch_critical_alert():
    engine = DummyEngine()
    ks = KillSwitch(engine)
    alert = Alert(level=AlertLevel.CRITICAL, message="System Unhealthy: Heartbeat stale")

    ks.handle_alert(alert)
    assert ks.status == CircuitBreakerStatus.TRIPPED
    assert engine.is_running is False
    assert "Heartbeat stale" in ks.trip_reason


def test_kill_switch_daily_pnl_exceeded():
    engine = DummyEngine()
    ks = KillSwitch(engine, max_daily_loss=500.0)

    tripped = ks.check_daily_pnl(-600.0)
    assert tripped is True
    assert ks.status == CircuitBreakerStatus.TRIPPED
    assert engine.is_running is False

    ks.reset()
    assert ks.status == CircuitBreakerStatus.ARMED
    assert ks.trip_reason is None