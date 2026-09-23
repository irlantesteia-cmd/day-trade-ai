# Day Trade AI Platform

Plataforma quantitativa modular para analise de mercado, backtesting,
paper trading e execucao assistida por Machine Learning.

**Status atual:** FASES 1-13 do roadmap concluidas. FASE 14 (ML) em andamento.
Live trading desabilitado por padrao.

---

## Principios

- **Separacao absoluta de responsabilidades** - dado, analise, estrategia, sinal,
  risco e execucao sao camadas independentes
- **Preservacao de capital antes de maximizacao de retorno**
- **Sem look-ahead bias** - validado por testes especificos
- **Sem overfitting** - walk-forward e out-of-sample como padrao
- **Sem martingale** - position sizing baseado em risco fixo por trade
- **Auditabilidade** - toda decisao gera evento rastreavel

---

## Arquitetura (visao de alto nivel)

Data -> Quality -> Store -> TimeSeries -> Indicators/Features
|
Strategy / AI
|
Signal
|
Risk Engine
|
Execution / Broker
|
Paper Broker | MT5 Broker

text

Detalhes em [docs/architecture.md](docs/architecture.md).

---

## Requisitos

- Python 3.10+
- Windows (para integracao MT5) ou Linux/macOS (modo paper)
- Git

---

## Instalacao

```powershell
# 1. Clonar
git clone https://github.com/irlantesteia-cmd/day-trade-ai.git
cd day-trade-ai

# 2. Ambiente virtual
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Dependencias core
pip install -e .

# 4. (Opcional) Suporte MetaTrader 5 - apenas Windows
pip install -e ".[mt5]"

# 5. (Opcional) Ferramentas de desenvolvimento
pip install -e ".[dev]"
Configuracao
Copie .env.example para .env e ajuste:

powershell
Copy-Item .env.example .env
Variaveis principais:

Variavel	Default	Descricao
APP_ENV	development	Ambiente de execucao
LOG_LEVEL	INFO	Nivel de log
DATABASE_URL	sqlite:///./daytrade.db	Banco (SQLite dev, Postgres prod)
MARKET_SYMBOL	WIN	Simbolo padrao
TIMEFRAME	1m	Timeframe padrao
INITIAL_CAPITAL	10000.0	Capital inicial
RISK_PER_TRADE	0.01	Risco por operacao (1%)
MAX_DAILY_LOSS	500.0	Perda diaria maxima
MAX_DRAWDOWN	0.10	Drawdown maximo
MAX_EXPOSURE	1.0	Exposicao maxima
TRADING_MODE	paper	paper / paper_mt5 / live
LIVE_TRADING_ENABLED	false	Trava global de seguranca
Nunca faca commit do arquivo .env.

Uso
Testes
powershell
pytest tests/ -v
Paper Trading (simulado, sem MT5)
powershell
python -m src.cli --mode paper --symbol WIN$
Paper Trading via MT5 Demo
Requer terminal MetaTrader 5 aberto e logado em conta demo.

powershell
python -m src.cli --mode paper_mt5 --symbol "WIN$" --log-level INFO
Estrutura de Pastas
text
src/
  adapters/         Adaptadores de broker (MT5)
  agents/           Auditoria e retreino automatico
  analytics/        Relatorios e exportacao
  api/              Gateway e webhook (classes Python)
  backtest/         Motor de backtest e metricas
  cli/              Interface de linha de comando
  config/           AppConfig (dataclass)
  core/             Settings (pydantic) - canonico
  data/             Providers, quality, persistencia
  deploy/           Orquestracao de deploy
  domain/           Entidades (Candle, Signal, Order, Position)
  engine/           Live engine, kill switch, MT5 bridge
  execution/        Paper broker, executor
  features/         Feature engineering
  indicators/       SMA, EMA, RSI, MACD, ATR, BB, OBV
  ml/               Modelos ML
  models/           Base + Logistic Regression + Dataset
  portfolio/        Manager, rebalancer, correlacao
  risk/             Risk engine, position sizing, SL/TP
  strategies/       Base, engine, registry, MA, RSI, ML
  telemetry/        Metricas, health, alerts
  timeseries/       Resampling, rolling windows
  utils/            Logger, health utils
  validation/       OOS, walk-forward, stress, sensitivity

docs/
  architecture.md
  development.md
  roadmap.md
  api.md
  adr/
    ADR-000-bootstrap.md
    ADR-001-stack.md
    ADR-002-config-duplication.md

tests/                132 testes (unit + integracao + e2e)
Documentacao
Arquitetura

Desenvolvimento

Roadmap

API

ADRs

Contribuicao
git status antes de alterar

pytest tests/ -v deve passar 100%

Commits atomicos com mensagens descritivas

Nunca quebrar testes em main

Licenca
Projeto privado. Todos os direitos reservados.

text

---

**Depois de salvar, rode apenas este comando e cole o output:**

```powershell
Get-Item README.md | Select-Object Name, Length
Get-Content README.md -TotalCount 5
Esperado:

Length > 4000

As 5 primeiras linhas legíveis (sem mojibake tipo anГѓВЎlise)

Se Length < 2000, o arquivo foi truncado de novo — me avisa.

This response is AI-generated, for reference only.


Detalhes em [docs/architecture.md](docs/architecture.md).

---

## Requisitos

- Python 3.10+
- Windows (para integracao MT5) ou Linux/macOS (modo paper)
- Git

---

## Instalacao

```powershell
# 1. Clonar
git clone https://github.com/irlantesteia-cmd/day-trade-ai.git
cd day-trade-ai

# 2. Ambiente virtual
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Dependencias core
pip install -e .

# 4. (Opcional) Suporte MetaTrader 5 - apenas Windows
pip install -e ".[mt5]"

# 5. (Opcional) Ferramentas de desenvolvimento
pip install -e ".[dev]"

Configuracao
Copie .env.example para .env e ajuste:

powershell
Copy-Item .env.example .env
Variaveis principais:

Variavel	Default	Descricao
APP_ENV	development	Ambiente de execucao
LOG_LEVEL	INFO	Nivel de log
DATABASE_URL	sqlite:///./daytrade.db	Banco (SQLite dev, Postgres prod)
MARKET_SYMBOL	WIN	Simbolo padrao
TIMEFRAME	1m	Timeframe padrao
INITIAL_CAPITAL	10000.0	Capital inicial
RISK_PER_TRADE	0.01	Risco por operacao (1%)
MAX_DAILY_LOSS	500.0	Perda diaria maxima
MAX_DRAWDOWN	0.10	Drawdown maximo
MAX_EXPOSURE	1.0	Exposicao maxima
TRADING_MODE	paper	paper / paper_mt5 / live
LIVE_TRADING_ENABLED	false	Trava global de seguranca
Nunca faca commit do arquivo .env.

Uso
Testes
powershell
pytest tests/ -v
Paper Trading (simulado, sem MT5)
powershell
python -m src.cli --mode paper --symbol WIN$
Paper Trading via MT5 Demo
Requer terminal MetaTrader 5 aberto e logado em conta demo.

powershell
python -m src.cli --mode paper_mt5 --symbol "WIN$" --log-level INFO
Estrutura de Pastas
text
src/
  adapters/         Adaptadores de broker (MT5)
  agents/           Auditoria e retreino automatico
  analytics/        Relatorios e exportacao
  api/              Gateway e webhook (classes Python)
  backtest/         Motor de backtest e metricas
  cli/              Interface de linha de comando
  config/           AppConfig (dataclass)
  core/             Settings (pydantic) - canonico
  data/             Providers, quality, persistencia
  deploy/           Orquestracao de deploy
  domain/           Entidades (Candle, Signal, Order, Position)
  engine/           Live engine, kill switch, MT5 bridge
  execution/        Paper broker, executor
  features/         Feature engineering
  indicators/       SMA, EMA, RSI, MACD, ATR, BB, OBV
  ml/               Modelos ML
  models/           Base + Logistic Regression + Dataset
  portfolio/        Manager, rebalancer, correlacao
  risk/             Risk engine, position sizing, SL/TP
  strategies/       Base, engine, registry, MA, RSI, ML
  telemetry/        Metricas, health, alerts
  timeseries/       Resampling, rolling windows
  utils/            Logger, health utils
  validation/       OOS, walk-forward, stress, sensitivity

docs/
  architecture.md
  development.md
  roadmap.md
  api.md
  adr/
    ADR-000-bootstrap.md
    ADR-001-stack.md
    ADR-002-config-duplication.md

tests/                132 testes (unit + integracao + e2e)
Documentacao
Arquitetura

Desenvolvimento

Roadmap

API

ADRs

Contribuicao
git status antes de alterar

pytest tests/ -v deve passar 100%

Commits atomicos com mensagens descritivas

Nunca quebrar testes em main

Licenca
Projeto privado. Todos os direitos reservados.

text

---

**Depois de salvar, rode apenas este comando e cole o output:**

```powershell
Get-Item README.md | Select-Object Name, Length
Get-Content README.md -TotalCount 5