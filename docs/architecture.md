# Arquitetura

## Visão Geral

A plataforma segue um fluxo **unidirecional em camadas**, onde cada camada
depende apenas da camada imediatamente inferior. Nenhuma camada superior pode
ser ignorada.

┌────────────────────────────────────────────────────────────────┐
│ DATA SOURCES (MT5, Mock Provider, CSV futuro) │
└────────────────────────┬───────────────────────────────────────┘
↓
┌────────────────────────────────────────────────────────────────┐
│ DATA INGESTION (src/data/providers/) │
└────────────────────────┬───────────────────────────────────────┘
↓
┌────────────────────────────────────────────────────────────────┐
│ DATA QUALITY (src/data/quality.py) │
│ → VALID | WARNING | INVALID | STALE │
└────────────────────────┬───────────────────────────────────────┘
↓
┌────────────────────────────────────────────────────────────────┐
│ DATA STORE (src/data/repository.py, database.py) │
└────────────────────────┬───────────────────────────────────────┘
↓
┌────────────────────────────────────────────────────────────────┐
│ TIME SERIES (src/timeseries/) │
│ → resample, rolling windows, alignment │
└────────────────────────┬───────────────────────────────────────┘
↓
┌──────────┴──────────┐
↓ ↓
┌─────────────────┐ ┌─────────────────┐
│ INDICATORS │ │ FEATURES │
│ src/indicators/ │ │ src/features/ │
└────────┬────────┘ └────────┬────────┘
└──────────┬──────────┘
↓
┌───────────────────────────────────────┐
│ STRATEGY / ML │
│ src/strategies/, src/models/ │
└───────────────────┬───────────────────┘
↓
┌───────────────────────────────────────┐
│ SIGNAL (src/domain/models.py::Signal) │
└───────────────────┬───────────────────┘
↓
┌───────────────────────────────────────┐
│ RISK (src/risk/) │
│ → validate_signal, position_sizing │
└───────────────────┬───────────────────┘
↓
┌───────────────────────────────────────┐
│ EXECUTION (src/execution/, src/engine/mt5_bridge) │
└───────────────────┬───────────────────┘
↓
┌────────────────┴────────────────┐
↓ ↓
PaperBroker MT5ExecutionEngine


## Regras de Dependência

| Camada | Pode importar de | NÃO pode importar de |
|---|---|---|
| `domain/` | stdlib | todo o resto |
| `data/` | domain, stdlib | estratégias, engine, execution |
| `indicators/`, `features/` | domain, stdlib | estratégias, engine |
| `strategies/` | domain, features, indicators | engine, execution, adapters |
| `risk/` | domain | execution, adapters |
| `engine/` | domain, strategies, risk, execution | — |
| `adapters/` | domain, stdlib | strategies, risk |
| `cli/` | tudo (é entrypoint) | — |

## Módulos

### `domain/`
Entidades puras: `Candle`, `Signal`, `Order`, `Position`. Sem dependências externas.

### `data/`
- `interfaces.py` — contratos `MarketDataProvider`
- `providers/` — implementações (Mock, MT5 futuro)
- `quality.py` — validação (duplicatas, gaps, timestamps)
- `repository.py` — persistência (SQLite/SQLAlchemy)

### `timeseries/`
- `resample.py` — agregação M1 → M5/M15/M30/H1
- `window.py` — rolling windows com garantia anti-look-ahead

### `indicators/`
- `trend.py` — SMA, EMA, VWAP, ADX
- `momentum.py` — RSI, MACD, Stochastic
- `volatility.py` — ATR, Bollinger Bands
- `volume.py` — OBV, Volume MA, Relative Volume
- `registry.py` + `engine.py` — execução declarativa

### `features/`
- `price_action.py` — body, wicks, range
- `technical.py` — usa indicadores
- `temporal.py` — hora do dia, dia da semana
- `pipeline.py` — orquestra extratores

### `strategies/`
- `base.py` — contrato `Strategy.generate_signal(bar) -> Signal | None`
- `registry.py` — registro de estratégias
- `moving_average.py`, `rsi_mean_reversion.py`, `ml_strategy.py`

### `risk/`
- `engine.py` — `validate_signal()`
- `manager.py` — limites e circuit breakers
- `calculators.py` — position sizing, SL/TP dinâmico

### `engine/`
- `live_engine.py` — orquestra signal → risk → execution
- `kill_switch.py` — circuit breaker global
- `mt5_bridge.py` — adapter do MT5 para o contrato de execution

### `execution/`
- `broker.py` — PaperBroker com slippage e fees
- `executor.py`, `engine.py`, `portfolio.py`

### `cli/`
- `runner.py` — entrypoint `python -m src.cli`
- `formatter.py` — status de saúde

## Gaps Arquiteturais Conhecidos

Registrados como ADRs, não corrigidos ainda:

1. **Config duplicado** — `src/config/settings.py` (dataclass) vs
   `src/core/config.py` (pydantic). Ver `ADR-002-config-duplication.md`.
2. **Sem abstração `Broker`** — `MT5ExecutionEngine` acopla direto no `MT5Adapter`.
3. **Sem Event Bus** — o fluxo é síncrono. Eventos previstos na seção 39 do
   framework ainda não implementados.
4. **Sem Model Registry** — o `.pkl` é carregado por caminho de arquivo.