# ADR-024 - Fechamento da sessao de desenvolvimento

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

Esta sessao de desenvolvimento cobriu um ciclo extenso de melhorias
na plataforma, partindo de um estado pos-v1.0.0 (commit `9d9ac28`) e
terminando com infraestrutura completa e achados cientificos
documentados.

O objetivo do projeto era construir uma "empresa de investimento
quantitativa 24/7 multi-ativo com auto-aperfeicoamento". Essa visao
orientou as decisoes, mas a evidencia empirica exigiu honestidade
sobre o que e alcancavel.

## Trabalho realizado

### FASE 1 - Correcao de regressoes e limpeza (M3.A)
- Reverter regressoes introduzidas por commits anteriores
- Corrigir SL/TP ausente em `MT5Adapter.execute_signal`
- Config consolidada (`AppConfig` virou wrapper sobre `Settings`)

### FASE 2 - Cleanup arquitetural (M4)
- Deletar `src/pipeline.py` (codigo morto)
- Unificar `engine.py` / `executor.py` (evitar duplicacao)
- Renomear `PortfolioManager` para `AccountState` (evitar conflito)
- Integrar `RiskEngine` ao pipeline de execucao

### FASE 3 - API e broker (M5, M6)
- API HTTP com FastAPI (6 endpoints + dashboard)
- Interface `Broker` formal
- `MT5ExecutionEngine` adaptado para aceitar `Broker`

### FASE 4 - Persistencia (M7)
- PostgreSQL + Alembic
- Migration inicial para tabela `candles`
- Testes estruturais + auto-skip sem Postgres

### FASE 5 - Machine Learning (M8, M9, M10)
- Features tecnicas (`technical_v1`)
- Diagnostico do ciclo senoidal no gerador sintetico
- Correcao do gerador (AR(1) puro)
- Experimento multi-timeframe (M1/M5/M15)

### FASE 6 - RiskManager (M11)
- Wiring parcial: sincronizar `open_positions_count`
- `max_open_positions` agora ativo em producao

### FASE 7 - Event Bus (M12)
- `EventBus` sincrono com 15 tipos
- Publicacao automatica em `LiveTradingEngine`

### FASE 8 - Dashboard (M13)
- HTML estatico servido em `/`
- Auto-refresh + botoes de controle

### FASE 9 - Deploy (M14)
- Container Postgres + testes de integracao

### FASE 10 - Benchmarks honestos (M15, M16)
- Benchmark de estrategias nao-ML (MA, RSI)
- Benchmark multi-ativo (5 ativos)
- **ADR-020**: nenhuma estrategia direcional tem edge

### FASE 11 - Daemon 24/7 (M17)
- `StateStore`, `Scheduler`, `DaemonRunner`
- Persistencia de estado, backoff exponencial, graceful shutdown

### FASE 12 - Volatilidade (M18, M19)
- Features de volatilidade
- Benchmark nao-direcional
- **ADR-022**: 1/4 ativos confirma
- **ADR-023**: sinal real para WIN, horizonte curto

### FASE 13 - Consolidacao (M20)
- README atualizado
- Roadmap atualizado
- STATUS.md (single-page)
- ADR-024 (este)

## Numeros da sessao

| Metrica | Antes | Depois |
|---|---|---|
| Testes | 132 | **280** (+4 skip) |
| ADRs | 3 | **24** |
| Commits | - | **20+** |
| Fases do roadmap | 12/21 | **19/21** |
| Modelos versionados | 0 | **5** |

## Licoes aprendidas

### 1. Rigor cientifico prevalece sobre entusiasmo
O resultado positivo do ADR-023 (+5.73 p.p. no WIN M5 H=3) so foi
aceito apos 3 confirmacoes (vencimento, horizonte curto, coerencia
entre folds). Nao tratamos como "descoberta" ate generalizar.

### 2. Resultados negativos sao valiosos
ADR-020 evita que alguem repita as mesmas ~20 combinacoes. Melhor
documentar o que **nao** funciona do que fingir progresso.

### 3. Dados multi-ativo sao defesa contra overfitting
O WINV26 M5 sozinho parecia uma descoberta. Ao generalizar para
outros ativos, o sinal evaporou em 3/4 dos casos.

### 4. Infraestrutura nao substitui edge
A plataforma esta completa tecnicamente, mas sem edge robusto nao
tem produto. A visao "empresa de investimento" so se materializa
quando houver sinal exploravel.

### 5. Complexidade se paga apenas quando resolve problema real
Daemon 24/7 foi sincrono (~300 linhas). Nao usamos asyncio, threads,
Redis, Kafka. Resolveu o problema com o minimo.

## Estado final do projeto

### Infraestrutura
- **Completa** em todas as fases 1-19
- Todos os testes passando
- CI configurado
- Docker + Postgres + Alembic prontos

### Cientifico
- Edge direcional: **nao encontrado** (ADR-020)
- Edge de volatilidade: **parcialmente identificado** (ADR-023)
- Achados documentados em 24 ADRs

### Operacional
- Daemon 24/7 funcional
- Paper trading via MT5 demo
- Dashboard HTTP
- Live trading desabilitado por design

## Proximos caminhos

Ver `docs/STATUS.md` secao 7. Ordem recomendada:

1. **A** - Estrategia de breakout baseada em ADR-023 (valida edge liquido)
2. **C** - DailyPnLTracker (fecha gap de risco)
3. **D** - CI com Postgres real
4. **E** - Autenticacao na API
5. **B** - GARCH/HAR-RV dedicado (se A confirmar)

## Nao coberto

- Live trading real (bloqueado por ausencia de edge robusto)
- Modelos de deep learning
- Microestrutura / order flow
- Pairs trading / market making

## Consequencias

- Projeto em estado consistente e documentado ✅
- 280 testes passando, 4 skipped ✅
- 24 ADRs cobrindo decisoes arquiteturais e achados cientificos ✅
- Documentacao para onboarding (`README.md`, `docs/STATUS.md`) ✅
- Base solida para continuacao ✅

## Licao final

Um projeto quantitativo serio nao e medido por "lucro" ou "edge
encontrado". E medido por **rigor metodologico**:
- Testes automatizados
- Walk-forward out-of-sample
- Multi-ativo como defesa contra overfitting
- Documentacao honesta de resultados (positivos E negativos)
- Infraestrutura reproduzivel

Nesta metrica, o projeto esta em excelente estado.

Referencias cruzadas: todos os ADRs (000-023).