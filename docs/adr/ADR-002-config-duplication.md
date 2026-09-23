# ADR-002 - Config consolidado (AppConfig sobre Settings)

- **Status**: Aceito (implementado em 2026-09-23)
- **Data original**: 2026-09-22
- **Data de resolucao**: 2026-09-23

## Contexto original

Existiam dois sistemas de configuracao coexistindo:

- `src/config/settings.py` - `AppConfig` (dataclass, 5 campos)
- `src/core/config.py` - `Settings` (pydantic-settings, 13 campos)

Divergencias:
- `AppConfig.max_daily_loss = 1000.0` vs `Settings.MAX_DAILY_LOSS = 500.0`
- Campos como `INITIAL_CAPITAL`, `RISK_PER_TRADE`, `MAX_DRAWDOWN`,
  `MAX_EXPOSURE`, `LIVE_TRADING_ENABLED`, `DATABASE_URL`, `MARKET_SYMBOL`,
  `TIMEFRAME` existiam em `Settings` mas nao em `AppConfig`
- `.env.example` refletia `Settings`
- Risco de bug silencioso: alterar `.env` podia nao ter efeito em `main.py`

## Decisao

Consolidar em `Settings` (pydantic-settings) como **fonte unica de verdade**,
mantendo `AppConfig` como **wrapper de compatibilidade**.

### Mudancas implementadas

**1. `src/core/config.py` (Settings)**
- `MAX_DAILY_LOSS` default alinhado para `500.0` (era 1000 em AppConfig,
  500 em Settings; adotado 500 por ser o valor em `.env.example` e por ser
  mais conservador - principio de preservacao de capital)
- Adicionado `BROKER_API_KEY: Optional[str] = None`
- Docstrings ASCII puro (sem mojibake)

**2. `src/config/settings.py` (AppConfig)**
- Deixou de ser `@dataclass`
- Virou wrapper sobre `Settings`
- Mantem API lowercase via properties + setters:
  - `environment` / `trading_mode` / `max_daily_loss` / `log_level` /
    `broker_api_key`
- `__init__` aceita `**kwargs` lowercase (compatibilidade com construtor
  estilo dataclass)
- `from_env()` delega para `Settings()` (le `.env` automaticamente)
- `__eq__` e `__repr__` implementados
- Expoe `settings` property para acesso a instancia subjacente

**3. `.env.example`**
- Adicionada linha comentada `# BROKER_API_KEY=sua_chave_aqui`

**4. `tests/test_config.py`**
- `test_default_config` ajustado para esperar `500.0` (valor canonico)
- Adicionados 3 testes: wrapper, equality, repr

## Compatibilidade

Todo o codigo existente continua funcionando sem alteracao:

- `src/main.py` usa `AppConfig.from_env()` -> OK
- `src/cli/runner.py` seta `.environment`, `.trading_mode`,
  `.max_daily_loss`, `.log_level` via setters -> OK
- `src/data/database.py` importa `settings` de `src.core.config` -> OK
- `tests/test_e2e_integration.py` usa `AppConfig(environment="test", ...)`
  via kwargs -> OK

## Consequencias

- Fonte unica de verdade: `Settings` (pydantic-settings) ✅
- `.env` passa a ter efeito em todo o sistema ✅
- Campos do `.env.example` todos lidos ✅
- Compatibilidade total com codigo legado via wrapper ✅
- 164 testes passando (eram 161; +3 de test_config) ✅

## Alternativas descartadas

- **Remover `AppConfig` completamente**: exigiria refatorar `src/main.py`,
  `src/cli/runner.py` e testes. Mais arriscado e fora do escopo minimo.
- **Manter 1000 como default**: rejeitado por conflitar com `.env.example`
  e com o principio de conservacao de capital.
- **Migrar `Settings` para ler de `AppConfig`**: invertido. Pydantic-settings
  e a tecnologia superior (validacao tipada, `.env` nativo, cache).

## Estado residual (backlog)

- A duplicacao de nomes `PortfolioManager` (`src/execution/portfolio.py` vs
  `src/portfolio/manager.py`) continua. Registrada em `docs/roadmap.md`.
- `AppConfig` continua existindo como wrapper. Migracao completa para
  `Settings` em codigo de producao e possivel, mas nao urgente.