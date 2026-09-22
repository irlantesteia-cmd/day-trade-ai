import pytest
from src.telemetry.alerts import AlertManager, AlertLevel


def test_alert_manager_trigger_and_handler():
    manager = AlertManager()
    received_alerts = []

    def custom_handler(alert):
        received_alerts.append(alert)

    manager.register_handler(custom_handler)

    alert = manager.trigger_alert(
        level=AlertLevel.WARNING,
        message="High memory usage",
        details={"usage_pct": 85.0},
    )

    assert len(received_alerts) == 1
    assert received_alerts[0].message == "High memory usage"
    assert received_alerts[0].level == AlertLevel.WARNING
    assert len(manager.get_history()) == 1


def test_alert_manager_evaluate_health():
    manager = AlertManager()

    unhealthy_data = {
        "status": "UNHEALTHY",
        "reasons": ["Heartbeat stale (35.0s > 30.0s)"],
    }

    triggered = manager.evaluate_health(unhealthy_data)
    assert len(triggered) == 1
    assert triggered[0].level == AlertLevel.CRITICAL
    assert "Heartbeat stale" in triggered[0].message


def test_alert_manager_clear_history():
    manager = AlertManager()
    manager.trigger_alert(AlertLevel.INFO, "System started")
    assert len(manager.get_history()) == 1

    manager.clear_history()
    assert len(manager.get_history()) == 0