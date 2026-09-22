import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AppConfig:
    environment: str = "development"
    trading_mode: str = "paper"
    max_daily_loss: float = 1000.0
    log_level: str = "INFO"
    broker_api_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            environment=os.getenv("APP_ENV", "development"),
            trading_mode=os.getenv("TRADING_MODE", "paper"),
            max_daily_loss=float(os.getenv("MAX_DAILY_LOSS", "1000.0")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            broker_api_key=os.getenv("BROKER_API_KEY", None),
        )