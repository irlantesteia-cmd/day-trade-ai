import pytest
from src.config.settings import AppConfig
from src.domain.enums import OrderStatus
from src.engine.kill_switch import CircuitBreakerStatus
from src.main import build_system, run_app


def test_e2e_system_initialization():
    config = AppConfig(environment="test", max_daily_loss=500.0)
    system = build_system(config)

    assert system["config"].max_daily_loss == 500.0
    assert system["kill_switch"].max_daily_loss == 500.0


def test_e2e_trading_loop_and_kill_switch():
    config = AppConfig(max_daily_loss=300.0)
    system, order = run_app(config)

    # 1. Valida processamento e execução da ordem
    assert order is not None
    assert order.status == OrderStatus.FILLED
    assert system["metrics"].get_counter("orders_executed") == 1.0

    # 2. Testa o disparo do KillSwitch por limite de perda diária
    ks = system["kill_switch"]
    tripped = ks.check_daily_pnl(-400.0)

    assert tripped is True
    assert ks.status == CircuitBreakerStatus.TRIPPED
    assert system["engine"].is_running is False

    # 3. Garante que com a engine parada, novas barras não geram ordens
    new_order = system["engine"].process_bar({"symbol": "WIN", "close": 110.0})
    assert new_order is None