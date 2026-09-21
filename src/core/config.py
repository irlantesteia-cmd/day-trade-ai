from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Day Trade AI Platform"
    APP_ENV: str = Field(default="development", description="Ambiente de execução")
    LOG_LEVEL: str = Field(default="INFO", description="Nível de log")

    DATABASE_URL: str = Field(
        default="sqlite:///./daytrade.db", description="URL do banco de dados"
    )

    MARKET_SYMBOL: str = Field(default="WIN", description="Símbolo padrão")
    TIMEFRAME: str = Field(default="1m", description="Timeframe padrão")

    INITIAL_CAPITAL: float = Field(default=10000.0, description="Capital inicial")
    RISK_PER_TRADE: float = Field(default=0.01, description="Risco por operação (1%)")
    MAX_DAILY_LOSS: float = Field(
        default=500.0, description="Perda máxima diária permitida"
    )
    MAX_DRAWDOWN: float = Field(
        default=0.10, description="Drawdown máximo permitido (10%)"
    )
    MAX_EXPOSURE: float = Field(
        default=1.0, description="Exposição máxima permitida"
    )

    TRADING_MODE: str = Field(default="paper", description="Modo de operação")
    LIVE_TRADING_ENABLED: bool = Field(
        default=False, description="Trava global de segurança para operação real"
    )


settings = Settings()