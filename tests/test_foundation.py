import json
from src.core.config import Settings
from src.utils.health import HealthChecker, SystemState
from src.utils.logger import StructuredLogger


def test_settings_initialization():
    settings = Settings()
    assert settings.APP_NAME == "Day Trade AI Platform"
    assert settings.LIVE_TRADING_ENABLED is False
    assert settings.TRADING_MODE == "paper"


def test_health_checker_states():
    checker = HealthChecker()
    assert checker.state == SystemState.STARTING
    assert checker.get_status()["healthy"] is False

    checker.set_state(SystemState.READY)
    assert checker.state == SystemState.READY
    assert checker.get_status()["healthy"] is True


def test_structured_logger_json_format():
    logger = StructuredLogger(level="INFO")
    payload_str = logger._format_event(
        level="INFO",
        event_type="SYS_INIT",
        component="TEST",
        message="System initialized",
    )
    payload = json.loads(payload_str)
    assert payload["event_type"] == "SYS_INIT"
    assert payload["component"] == "TEST"
    assert payload["level"] == "INFO"