import pytest
from src.main import build_system, run_app
from src.domain.enums import OrderStatus


def test_build_system():
    system = build_system()
    assert "engine" in system
    assert "metrics" in system
    assert "health" in system
    assert "alerts" in system
    assert "kill_switch" in system


def test_run_app():
    system, order = run_app()
    assert order is not None
    assert order.status == OrderStatus.FILLED
    assert system["metrics"].get_counter("bars_processed") == 1.0
    assert system["metrics"].get_counter("orders_executed") == 1.0