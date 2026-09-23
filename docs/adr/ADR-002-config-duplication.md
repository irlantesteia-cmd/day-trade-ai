# ADR-002 - Config duplicado (AppConfig vs Settings)

- **Status**: Proposto (nao corrigido)
- **Data**: 2026-09-22

## Contexto

Existem **dois** sistemas de configuracao coexistentes:

### `src/config/settings.py` - `AppConfig` (dataclass)

```python
@dataclass
class AppConfig:
    environment: str = "development"
    trading_mode: str = "paper"
    max_daily_loss: float = 1000.0
    log_level: str = "INFO"
    broker_api_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AppConfig": ...

    Usado por: src/main.py::build_system()

src/core/config.py - Settings (pydantic)
python
class Settings(BaseSettings):
    APP_NAME: str = "Day Trade AI Platform"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "sqlite:///./daytrade.db"
    MARKET_SYMBOL: str = "WIN"
    TIMEFRAME: str = "1m"
    INITIAL_CAPITAL: float = 10000.0
    RISK_PER_TRADE: float = 0.01
    MAX_DAILY_LOSS: float = 500.0
    MAX_DRAWDOWN: float = 0.10
    MAX_EXPOSURE: float = 1.0
    TRADING_MODE: str = "paper"
    LIVE_TRADING_ENABLED: bool = False

settings = Settings()
Usado por: tests/test_foundation.py (validacao)

Problema
Divergencia de defaults: AppConfig.max_daily_loss = 1000.0 vs
Settings.MAX_DAILY_LOSS = 500.0. Qual e o correto?

Campos ausentes em AppConfig: INITIAL_CAPITAL, RISK_PER_TRADE,
MAX_DRAWDOWN, MAX_EXPOSURE, LIVE_TRADING_ENABLED, DATABASE_URL,
MARKET_SYMBOL, TIMEFRAME - todos existem no .env.example mas sao
ignorados pelo codigo principal

.env.example reflete Settings, nao AppConfig - inconsistencia

Risco de bug silencioso: alterar .env pode nao ter efeito nenhum se o
codigo le do outro sistema

Decisao proposta (a implementar em milestone futuro)
Consolidar em Settings (pydantic):

Remover AppConfig de src/config/settings.py

src/main.py passa a usar from src.core.config import settings

Validar na inicializacao que todas as variaveis do .env.example sao lidas

Atualizar testes

Manter src/core/config.py como unico ponto de verdade

Consequencias
Nao corrigir agora - requer milestone dedicado (regressao em testes)

Registrar como gap arquitetural em docs/architecture.md

Deve ser resolvido antes de adicionar config de ML (features, modelos,
thresholds via env)

Alternativas descartadas
Manter os dois: mantem ambiguidade, aumenta risco operacional

Migrar para AppConfig (dataclass): perde validacao tipada do pydantic