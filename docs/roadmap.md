# Roadmap - Status Real

Documento vivo. Atualizar a cada milestone concluido.

Ultima atualizacao: pos-Milestone 20 (2026-09-24).

## Legenda

- `[OK]` Concluido
- `[~]` Parcial
- `[ ]` Nao iniciado

## Fases

| Fase | Descricao | Status |
|---|---|---|
| 0 | Discovery / Auditoria | [OK] |
| 1 | Foundation (config, logging, health, git, pytest, README, estrutura) | [OK] |
| 2 | Domain (Market, Symbol, Candle, Signal, Order, Position) | [OK] |
| 3 | Data Engine (providers, quality, persistence) | [OK] |
| 4 | Time Series (resampling, windows, alignment) | [OK] |
| 5 | Indicators | [OK] |
| 6 | Features | [OK] |
| 7 | Strategies | [OK] |
| 8 | Signal Engine | [~] |
| 9 | Backtesting | [OK] |
| 10 | Performance (metrics, equity, drawdown) | [OK] |
| 11 | Risk | [OK] |
| 12 | Paper Trading | [OK] |
| 13 | Robustness (OOS, Walk-Forward, Monte Carlo, Sensitivity) | [OK] |
| 14 | Machine Learning | [~] infra completa, sem edge direcional |
| 15 | Portfolio | [OK] |
| 16 | API | [OK] HTTP + dashboard |
| 17 | Dashboard | [OK] HTML estatico |
| 18 | Production (Postgres, monitoramento) | [OK] Docker + Alembic |
| 19 | Broker Integration (abstracao Broker) | [OK] |
| 20 | Live Trading | [ ] bloqueada (sem edge comprovado) |

## Progresso

- Concluidas: 19/21 fases (90%)
- Parciais: 1/21 fases (5%) - FASE 8
- Bloqueadas: 1/21 fases (5%) - FASE 20

## Problemas Conhecidos (Backlog Tecnico)

| # | Problema | Severidade | Fase alvo |
|---|---|---|---|
| P1 | `src/backtest/engine.py` nao tem `__main__` nem argparse | Baixa | Fase 9 |
| P4 | `src/ml/logistic_model.py` e stub usado por AutoRetrainer | Media | Fase 14 |
| P8 | `train_model.py` (v2) ainda contem ciclo senoidal (script legado) | Baixa | - |
| P9 | `models/logistic_v1.pkl` ainda referenciado por `_load_strategy()` | Media | Fase 14 |
| P10 | Alias `PortfolioManager = AccountState` deprecado | Baixa | - |
| P11 | Nome `portfolio` no `ExecutionEngine.__init__` (historico) | Baixa | - |
| P12 | API HTTP sem autenticacao | Alta (se exposta) | Fase 16 |
| P13 | DailyPnLTracker nao implementado (ADR-015) | Media | Fase 11 |
| P14 | Sem CI com Postgres real | Baixa | Fase 18 |
| P15 | Docker nao instalado no ambiente dev local | Baixa | - |

## Achados Cientificos

Ver `docs/STATUS.md` para detalhes. Resumo:

- **ADR-020**: nenhuma estrategia direcional testada tem edge
  (~20 combinacoes: ML logistico, MA Crossover, RSI Reversion; 5 ativos;
  4 timeframes; 2 horizontes). Consistente com eficiencia de mercado.
- **ADR-022**: previsao de volatilidade nao generaliza uniformemente.
- **ADR-023**: sinal de volatilidade real **para o WIN**, especifico de
  horizonte curto (H=3..5). Edge modesto (+3 a +6 p.p.).

## Proximos Milestones Possiveis

### Milestone A - GARCH / HAR-RV dedicado
- Implementar modelo de volatilidade dedicado (biblioteca `arch`)
- Testar em WIN M5 H=3..5
- Comparar com logistico + features simples
- **Risco**: complexidade alta, ganho incerto

### Milestone B - Estrategia de breakout baseada em volatilidade
- Usar o sinal do ADR-023 para disparar ordens (nao so previsao)
- Modelar spread/commission no backtest
- **Risco**: edge modesto pode ser absorvido por custos

### Milestone C - DailyPnLTracker + KillSwitch unificado
- Implementar rastreamento de PnL diario
- Conectar ao RiskManager (fecha P13)
- **Risco**: baixo, valor medio

### Milestone D - CI com Postgres real
- Adicionar `services.postgres` no GitHub Actions
- Rodar testes de integracao em CI
- **Risco**: baixo, valor baixo

### Milestone E - Autenticacao na API
- API key ou OAuth
- Requer antes de exposicao publica
- **Risco**: baixo, valor alto se for expor

## Nao-Objetivos (mantidos)

- LLM / GPT / linguagem natural
- Redis / Kafka / Celery
- Microservicos
- GPU / deep learning
- Live trading real sem edge comprovado