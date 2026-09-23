# Roadmap - Status Real

Documento vivo. Atualizar a cada milestone concluido.

Ultima atualizacao: pos-Milestone 1.

## Legenda

- `[OK]` Concluido
- `[~]` Parcial
- `[ ]` Nao iniciado

## Fases

| Fase | Descricao | Status |
|---|---|---|
| 0 | Discovery / Auditoria | [~] |
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
| 14 | Machine Learning | [~] |
| 15 | Portfolio | [OK] |
| 16 | API | [~] |
| 17 | Dashboard | [ ] |
| 18 | Production (Postgres, monitoramento) | [~] |
| 19 | Broker Integration (abstracao Broker) | [~] |
| 20 | Live Trading | [ ] |

## Progresso

- Concluidas: 12/21 fases (57%)
- Parciais: 6/21 fases (29%)
- Pendentes: 3/21 fases (14%)

## Problemas Conhecidos (Backlog Tecnico)

| # | Problema | Severidade | Fase alvo |
|---|---|---|---|
| P1 | `src/backtest/engine.py` nao tem `__main__` nem argparse | Baixa | Fase 9 |
| P2 | Config duplicado (`AppConfig` vs `Settings`) | Media | Ver ADR-002 |
| P3 | `MT5Adapter.execute_signal` nao envia stop_loss nem take_profit | Alta | Fase 11 |
| P4 | `src/ml/logistic_model.py` e stub morto (sempre retorna 0.5) | Baixa | Fase 14 |
| P5 | Sem abstracao `Broker` formal | Media | Fase 19 |
| P6 | Sem Event Bus | Media | Fase futura |
| P7 | Sem Model Registry | Media | Fase 14 |
| P8 | `src/pipeline.py` e `src/data/engine.py` com 0% de cobertura | Baixa | - |

## Proximos Milestones

### Milestone 2 - PHASE 14 (ML)

- `ModelRegistry` com metadados (model_id, version, dataset_version, metrics)
- Dataset versioning
- Re-treino com features de `src/features/`
- Walk-forward usando `src/validation/`
- Criterio de aceitacao: edge > 1.5 p.p. em OOS

### Milestone 3 - PHASE 15 (Portfolio, reconstrucao)

- Reconstruir `PortfolioOrchestrator` dentro do framework
- Usar ativos apenas com edge comprovado (Milestone 2)

### Milestone 4 - PHASE 19 (Broker Abstraction)

- Interface `Broker` formal
- `MT5Adapter` implementa `Broker`
- `PaperBroker` tambem implementa

### Milestone 5 - PHASE 16 (API HTTP)

- FastAPI com endpoints da secao 41 do framework

## Nao-Objetivos (por enquanto)

- LLM / GPT / linguagem natural
- Redis / Kafka / Celery
- Microservicos
- GPU / deep learning
- Live trading real
