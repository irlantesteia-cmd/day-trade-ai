"""Testes do wrapper AppConfig sobre Settings (pydantic-settings)."""
import pytest

from src.config.settings import AppConfig
from src.core.config import Settings


def test_default_config():
    """AppConfig() le defaults de Settings (que le .env se existir)."""
    config = AppConfig()
    assert config.environment == "development"
    assert config.trading_mode == "paper"
    # Valor canonico: 500.0 (alinhado com .env.example)
    assert config.max_daily_loss == 500.0
    assert config.log_level == "INFO"
    assert config.broker_api_key is None


def test_config_from_env(monkeypatch):
    """Variaveis de ambiente tem precedencia sobre defaults."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("TRADING_MODE", "live")
    monkeypatch.setenv("MAX_DAILY_LOSS", "2500.0")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("BROKER_API_KEY", "key_prod_998877")

    # Settings() e re-instanciado dentro de from_env(), lendo env atualizado
    config = AppConfig.from_env()
    assert config.environment == "production"
    assert config.trading_mode == "live"
    assert config.max_daily_loss == 2500.0
    assert config.log_level == "DEBUG"
    assert config.broker_api_key == "key_prod_998877"


def test_appconfig_is_wrapper_of_settings():
    """AppConfig expoe a instancia Settings subjacente."""
    config = AppConfig()
    assert isinstance(config.settings, Settings)
    # Mudar via wrapper reflete no Settings subjacente
    config.max_daily_loss = 777.0
    assert config.settings.MAX_DAILY_LOSS == 777.0


def test_appconfig_equality():
    """Dois AppConfig com mesmos valores sao iguais."""
    c1 = AppConfig()
    c2 = AppConfig()
    assert c1 == c2

    c2.max_daily_loss = 999.0
    assert c1 != c2


def test_appconfig_repr():
    """__repr__ mostra os campos principais."""
    config = AppConfig()
    text = repr(config)
    assert "AppConfig" in text
    assert "environment" in text
    assert "trading_mode" in text