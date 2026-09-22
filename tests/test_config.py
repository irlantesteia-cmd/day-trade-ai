import pytest
from src.config.settings import AppConfig


def test_default_config():
    config = AppConfig()
    assert config.environment == "development"
    assert config.trading_mode == "paper"
    assert config.max_daily_loss == 1000.0
    assert config.log_level == "INFO"
    assert config.broker_api_key is None


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("TRADING_MODE", "live")
    monkeypatch.setenv("MAX_DAILY_LOSS", "2500.0")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("BROKER_API_KEY", "key_prod_998877")

    config = AppConfig.from_env()
    assert config.environment == "production"
    assert config.trading_mode == "live"
    assert config.max_daily_loss == 2500.0
    assert config.log_level == "DEBUG"
    assert config.broker_api_key == "key_prod_998877"