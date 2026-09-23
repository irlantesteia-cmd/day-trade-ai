"""
AppConfig - wrapper de compatibilidade sobre src.core.config.Settings.

Mantem a API lowercase usada por codigo legado (environment, trading_mode,
max_daily_loss, log_level, broker_api_key) enquanto delega toda a leitura
de configuracao para Settings (pydantic-settings), que e a fonte unica
de verdade.

Suporta dois estilos de construcao:
    AppConfig(environment="test", max_daily_loss=500.0)  # kwargs (legado)
    AppConfig.from_env()                                  # le .env
    AppConfig()                                           # defaults
"""
from typing import Any, Optional

from src.core.config import Settings


# Mapeamento campo lowercase -> atributo uppercase em Settings
_FIELD_MAP = {
    "environment": "APP_ENV",
    "trading_mode": "TRADING_MODE",
    "max_daily_loss": "MAX_DAILY_LOSS",
    "log_level": "LOG_LEVEL",
    "broker_api_key": "BROKER_API_KEY",
}


class AppConfig:
    """
    Wrapper sobre Settings com API lowercase para compatibilidade.

    Campos expostos:
        environment     -> Settings.APP_ENV
        trading_mode    -> Settings.TRADING_MODE
        max_daily_loss  -> Settings.MAX_DAILY_LOSS
        log_level       -> Settings.LOG_LEVEL
        broker_api_key  -> Settings.BROKER_API_KEY
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        **kwargs: Any,
    ) -> None:
        self._settings = settings or Settings()

        # Aplica kwargs lowercase (compatibilidade com dataclass legada)
        for key, value in kwargs.items():
            if key not in _FIELD_MAP:
                raise TypeError(
                    f"AppConfig.__init__() got an unexpected keyword argument '{key}'"
                )
            setattr(self._settings, _FIELD_MAP[key], value)

    # ------------------------------------------------------------------
    # Propriedades lowercase
    # ------------------------------------------------------------------

    @property
    def environment(self) -> str:
        return self._settings.APP_ENV

    @environment.setter
    def environment(self, value: str) -> None:
        self._settings.APP_ENV = value

    @property
    def trading_mode(self) -> str:
        return self._settings.TRADING_MODE

    @trading_mode.setter
    def trading_mode(self, value: str) -> None:
        self._settings.TRADING_MODE = value

    @property
    def max_daily_loss(self) -> float:
        return self._settings.MAX_DAILY_LOSS

    @max_daily_loss.setter
    def max_daily_loss(self, value: float) -> None:
        self._settings.MAX_DAILY_LOSS = value

    @property
    def log_level(self) -> str:
        return self._settings.LOG_LEVEL

    @log_level.setter
    def log_level(self, value: str) -> None:
        self._settings.LOG_LEVEL = value

    @property
    def broker_api_key(self) -> Optional[str]:
        return self._settings.BROKER_API_KEY

    @broker_api_key.setter
    def broker_api_key(self, value: Optional[str]) -> None:
        self._settings.BROKER_API_KEY = value

    # ------------------------------------------------------------------
    # Acesso direto a Settings subjacente
    # ------------------------------------------------------------------

    @property
    def settings(self) -> Settings:
        """Retorna a instancia Settings subjacente."""
        return self._settings

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Constroi AppConfig lendo de variaveis de ambiente e .env."""
        return cls(settings=Settings())

    # ------------------------------------------------------------------
    # Representacao
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"AppConfig(environment={self.environment!r}, "
            f"trading_mode={self.trading_mode!r}, "
            f"max_daily_loss={self.max_daily_loss!r}, "
            f"log_level={self.log_level!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AppConfig):
            return NotImplemented
        return (
            self.environment == other.environment
            and self.trading_mode == other.trading_mode
            and self.max_daily_loss == other.max_daily_loss
            and self.log_level == other.log_level
            and self.broker_api_key == other.broker_api_key
        )