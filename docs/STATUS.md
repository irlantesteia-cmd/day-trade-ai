# Status do Projeto

Single-page com o estado consolidado da plataforma. Atualizado em
2026-09-24 (pos-Milestone 20).

Para detalhes arquiteturais, ver `docs/architecture.md`.
Para historico de decisoes, ver `docs/adr/`.
Para roadmap de fases, ver `docs/roadmap.md`.

---

## 1. O que a plataforma faz

Infraestrutura quantitativa completa:

| Componente | Status | Notas |
|---|---|---|
| Coleta MT5 | OK | Via `src/adapters/mt5_adapter.py` |
| Data quality | OK | Validacao em `src/data/quality.py` |
| Persistencia | OK | SQLite (dev) + PostgreSQL (prod) via SQLAlchemy |
| Migrations | OK | Alembic configurado |
| Time series | OK | Resampling, rolling windows |
| Indicators | OK | SMA, EMA, RSI, MACD, ATR, BB, OBV |
| Features | OK | Price action, technical, temporal, volatility |
| Strategies | OK | MA Crossover, RSI Reversion, ML |
| Walk-forward | OK | `src/validation/splitter.py` |
| ML pipeline | OK | Dataset, treino, registry versionado |
| Risk | OK | SL/TP, position sizing, kill switch, max positions |
| Execution | OK | PaperBroker + MT5Adapter (contrato Broker) |
| Events | OK | EventBus com 15 tipos |
| API HTTP | OK | FastAPI, 6 endpoints + dashboard |
| Dashboard | OK | HTML estatico em `/` |
| Daemon 24/7 | OK | StateStore + Scheduler + Runner resiliente |
| Docker | OK | docker-compose com app + postgres |
| CI | OK | GitHub Actions (pytest) |

---

## 2. Estado dos testes
280 passed, 4 skipped

- 4 skips: testes de integracao Postgres (auto-skip sem Postgres)

Cobertura: unit + integracao + e2e.

---

## 3. Achados cientificos

Os experimentos foram rigorosos (walk-forward, multi-ativo, multi-timeframe).

### 3.1 Sem edge direcional (ADR-020)

Testadas ~20 combinacoes:

| Familia | Ativos | TFs | Resultado |
|---|---|---|---|
| ML logistico (8 features) | WINV26 | M1/M5/M15 | 3x negativo |
| MA Crossover | WINV26, WDOX26, PETR4, VALE3, ITUB4 | M5 | 5x negativo |
| MA Crossover | PETR4 | M15/M30 | 2x negativo |
| RSI Reversion | WINV26, WDOX26, PETR4, VALE3, ITUB4 | M5 | 5x negativo |
| RSI Reversion | PETR4 | M15/M30 | 2x negativo |

**Conclusao:** prever direcao com indicadores tecnicos puros nao
funciona nos ativos testados. Consistente com eficiencia de mercado
fraca.

### 3.2 Volatilidade: sinal especifico do WIN (ADR-022, ADR-023)

Target binario: "vai ter movimento grande no proximo H candles?"

| Teste | Edge medio | Folds + | Conclusao |
|---|---|---|---|
| WINV26 M5 H=5 | +4.87 p.p. | 56/79 (71%) | positivo |
| WINZ26 M5 H=5 | +3.31 p.p. | 22/39 (56%) | positivo |
| WINV26 M5 H=3 | **+5.73 p.p.** | **61/79 (77%)** | positivo |
| WINV26 M5 H=10 | +0.85 p.p. | 40/79 (51%) | neutro |
| PETR4 M5 H=5 | -1.91 p.p. | 66/194 (34%) | negativo |
| WDOX26 M5 H=5 | +0.94 p.p. | 10/17 (59%) | neutro |

**Conclusao:** sinal de volatilidade e real **para o WIN**,
especifico de horizonte curto (H=3..5). Edge modesto (+3 a +6 p.p.).

### 3.3 Por que nao operar ainda

1. Edge modesto (+3-5 p.p.) pode ser absorvido por spread + corretagem
2. Sem estrategia de execucao implementada (breakout, straddle)
3. Sem teste com bid/ask real (spread nao modelado)
4. Sem teste em regimes historicos diferentes (2023, 2024)

---

## 4. Arquitetura de alto nivel
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

**Separacao de camadas:** cada camada tem responsabilidade unica e
depende apenas da camada imediatamente inferior. Nenhuma camada pode
ser ignorada.

**Eventos:** EventBus publica 15 tipos de evento (SIGNAL_GENERATED,
RISK_REJECTED, ORDER_FILLED, etc.) permitindo rastreabilidade.

**Persistencia:** SQLite (dev), PostgreSQL (prod via Docker).

---

## 5. Como rodar

### Testes

```powershell
pytest tests/ -v
Paper trading
powershell
python -m src.cli --mode paper_mt5 --symbol WINV26
Daemon 24/7
powershell
python -m src.daemon --symbol WINV26 --mode paper_mt5 --poll 5.0
API + dashboard
powershell
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
6. Limitacoes conhecidas
Limitacao	Impacto	Ver
Sem edge direcional	Nao operar direcao	ADR-020
Edge vol modesto	Pode nao cobrir custos	ADR-023
Sem autenticacao na API	Nao expor publicamente	ADR-009
DailyPnLTracker ausente	Drawdown diario nao enforcado	ADR-015
Sem CI com Postgres real	Testes Postgres nao rodam em CI	ADR-018
Docker nao instalado local	Testes Postgres skipam	-
7. Proximos caminhos (ordenados por viabilidade)
A. Estrategia de breakout baseada em ADR-023
Usar o sinal de volatilidade (WIN M5 H=3..5) para disparar ordens.
Modelar spread/commission para validar edge liquido.

B. GARCH / HAR-RV dedicado
Implementar modelo de volatilidade especializado. Comparar com
logistico + features simples.

C. DailyPnLTracker
Rastrear PnL diario + conectar ao RiskManager. Fecha P13.

D. CI com Postgres real
Adicionar services.postgres no GitHub Actions.

E. Autenticacao na API
API key ou OAuth. Requerido antes de exposicao publica.

8. Nao-objetivos
LLM / GPT / linguagem natural

Redis / Kafka / Celery

Microservicos

GPU / deep learning

Live trading real sem edge comprovado

9. Licoes aprendidas
Dados multi-ativo sao defesa contra falso positivo. WINV26 M5
sozinho parecia descoberta; multi-ativo mostrou variacao.

Documentar negativos e tao importante quanto positivos. ADR-020
evita que alguem repita as mesmas ~20 combinacoes.

Nao insistir com "fishing". Ajustar hiperparametros ate dar
positivo e overfitting. Melhor aceitar o achado e pivotar.

Infraestrutura 24/7 nao requer complexidade. Um loop sincrono
com backoff, scheduler trivial e persistencia minima resolve.

10. Referencias
README

Architecture

Development

Roadmap

API

ADRs