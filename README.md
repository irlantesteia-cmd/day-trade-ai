# Day Trade AI Platform

Plataforma quantitativa modular para analise de mercado, backtesting,
paper trading e execucao assistida por Machine Learning.

**Status atual:** infraestrutura completa (FASES 1-19 do roadmap).
Edge direcional nao encontrado (ADR-020). Edge de volatilidade
parcialmente identificado no WIN (ADR-023). Live trading desabilitado
por design.

> Para o estado detalhado do projeto, ver [docs/STATUS.md](docs/STATUS.md).
> Para o historico de decisoes, ver [docs/adr/](docs/adr/).

---

## Principios

- **Separacao absoluta de responsabilidades** - dado, analise, estrategia,
  sinal, risco e execucao sao camadas independentes
- **Preservacao de capital antes de maximizacao de retorno**
- **Sem look-ahead bias** - validado por testes especificos
- **Sem overfitting** - walk-forward e out-of-sample como padrao
- **Sem martingale** - position sizing baseado em risco fixo por trade
- **Auditabilidade** - toda decisao gera evento rastreavel
- **Honestidade cientifica** - resultados negativos sao documentados
  em ADRs (ver ADR-020, ADR-022, ADR-023)

---

## O que a plataforma faz hoje

- **Coleta** barras de multiplos ativos via MetaTrader 5
- **Valida** qualidade de dados (duplicatas, gaps, timestamps)
- **Persiste** em SQLite (dev) ou PostgreSQL (prod) com Alembic
- **Processa** series temporais (resampling, rolling windows)
- **Calcula** indicadores tecnicos (SMA, EMA, RSI, MACD, ATR, BB, OBV)
- **Extrai** features (price action, tecnicas, temporais, volatilidade)
- **Executa** estrategias classicas (MA, RSI) e modelos ML
- **Valida** com walk-forward, out-of-sample, Monte Carlo
- **Gerencia risco** (SL/TP via ATR, position sizing, kill switch)
- **Executa** ordens em paper broker ou MT5 demo
- **Publica** eventos via EventBus
- **Expõe** API HTTP + dashboard
- **Roda 24/7** via daemon resiliente

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

Detalhes em [docs/architecture.md](docs/architecture.md).

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

# 5. (Opcional) API HTTP + dashboard
pip install -e ".[api]"

# 6. (Opcional) PostgreSQL + migrations
pip install -e ".[postgres]"

# 7. (Opcional) Ferramentas de desenvolvimento
pip install -e ".[dev]"

Configuracao
Copy-Item .env.example .env
Variaveis principais em .env.example. Nunca faca commit do .env.

Uso
Testes
pytest tests/ -v

Paper Trading (simulado, sem MT5)
python -m src.cli --mode paper --symbol WINV26
Paper Trading via MT5 Demo
Requer terminal MetaTrader 5 aberto e logado.
python -m src.cli --mode paper_mt5 --symbol WINV26 --log-level INFO
Daemon 24/7
powershell
python -m src.daemon --symbol WINV26 --mode paper_mt5 --poll 5.0
API HTTP + Dashboard
powershell
pip install -e ".[api]"
uvicorn src.api.http:app --reload
# Abrir http://127.0.0.1:8000/
Docker Compose (app + Postgres)
powershell
docker compose up -d
Benchmark de estrategias
powershell
python scripts/benchmark_strategies.py --from-mt5 --symbol WINV26 --timeframe M5
Benchmark de volatilidade
powershell
python scripts/benchmark_volatility.py --from-mt5 --symbol WINV26 --timeframe M5
Treino de modelo ML
powershell
python scripts/train_model_v3.py --from-mt5 --symbol WINV26 --timeframe M5 --feature-set technical
Estrutura de Pastas
text
src/
  adapters/         Adaptadores de broker (MT5)
  agents/           Auditoria e retreino automatico
  analytics/        Relatorios e exportacao
  api/              API HTTP (FastAPI) + dashboard estatico
  backtest/         Motor de backtest e metricas
  cli/              Interface de linha de comando
  config/           AppConfig (wrapper sobre Settings)
  core/             Settings (pydantic) - canonico
  daemon/           Operacao 24/7 (StateStore, Scheduler, Runner)
  data/             Providers, quality, persistencia
  deploy/           Orquestracao de deploy
  domain/           Entidades (Candle, Signal, Order, Position)
  engine/           Live engine, kill switch, MT5 bridge
  events/           EventBus + EventType (15 tipos)
  execution/        Paper broker, broker_base, executor
  features/         Feature engineering (price_action, technical,
                    temporal, volatility, sets)
  indicators/       SMA, EMA, RSI, MACD, ATR, BB, OBV
  models/           LogisticRegression, DatasetBuilder, ModelRegistry
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
  STATUS.md
  adr/  (24 ADRs)

scripts/
  benchmark_strategies.py
  benchmark_volatility.py
  train_model_v3.py
  train_model.py  (legado)

migrations/         Alembic
models/
  registry/         Modelos versionados
  benchmarks/       Resultados de benchmarks
Testes
280 testes (unit + integracao + e2e) + 4 auto-skip (Postgres).

powershell
pytest tests/ -v
Achados cientificos
Os ADRs documentam descobertas honestas:

ADR-020: Nenhuma estrategia direcional testada tem edge (MA, RSI,
ML logistico; ~20 combinacoes ativo x timeframe x horizonte).

ADR-022: Previsao de volatilidade nao generaliza para todos os ativos.

ADR-023: Sinal de volatilidade e real para o WIN, especifico de
horizonte curto (H=3..5). Edge modesto (+3 a +6 p.p.).

Documentacao
Arquitetura

Desenvolvimento

Roadmap

API

STATUS

ADRs

Contribuicao
git status antes de alterar

pytest tests/ -v deve passar 100%

Commits atomicos com mensagens descritivas

Nunca quebrar testes em main

Toda decisao arquitetural gera um ADR

Licenca
Projeto privado. Todos os direitos reservados.