# ADR-021 - Daemon 24/7

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

A plataforma tinha um loop interativo (`src/cli/runner.py`) adequado
para uso manual, mas inadequado para operacao continua:

- Sem reconnect automatico de MT5
- Sem persistencia de estado entre reinicios
- Sem tarefas periodicas (health, snapshot)
- Sem graceful shutdown programatico
- Sem politica de backoff

A FASE 20 (Live) permanece bloqueada pela ausencia de edge, mas a
infraestrutura de operacao 24/7 e util independentemente disso
(paper trading continuo, validacao operacional).

## Decisao

Implementar daemon sincrono com 3 componentes:

### 1. `src/daemon/state.py` - `StateStore`

Persistencia key-value em SQLite (stdlib, sem nova dependencia):

- `set(key, dict)` / `get(key)` / `delete(key)` / `list_keys()`
- `updated_at(key)` para diagnostico
- Helpers de alto nivel:
  - `save_kill_switch(status, reason)` / `load_kill_switch()`
  - `save_heartbeat(source)` / `load_heartbeat()`
  - `save_daemon_config(config)` / `load_daemon_config()`

Escolhas:
- Sem SQLAlchemy (evita acoplamento com `Base.metadata` do projeto)
- Commit imediato (durabilidade > performance)
- JSON no campo `value` (schema flexivel)
- `check_same_thread=False` (permite uso futuro com threads sem mudar)

### 2. `src/daemon/scheduler.py` - `Scheduler`

Agendador sincrono baseado em `time.monotonic()`:

- `every(interval_sec, name, func)` registra/substitui tarefa
- `tick(now=None)` executa apenas tarefas vencidas
- Erros em uma tarefa nao interrompem as demais
- Contadores: `run_count`, `error_count`, `last_error`, `last_run`

Escolhas:
- Sem asyncio, sem threads (comportamento previsivel)
- `time.monotonic()` em vez de `datetime` (resistente a mudancas de relogio)
- Testavel: aceita `now` como parametro

### 3. `src/daemon/runner.py` - `DaemonRunner`

Loop principal:

- Chama `tick_fn()` repetidamente
- Em excecao: chama `reconnect_fn()` com backoff exponencial
  (1s, 2s, 4s, 8s, ..., cap em `max_reconnect_backoff_sec`)
- Reset do backoff em sucesso do tick
- Graceful shutdown via SIGINT/SIGTERM (`request_shutdown()`)
- Instala handlers de sinal (silencioso se nao estiver na main thread)
- Integracao opcional com `Scheduler` e `StateStore`
- Injetavel (`sleep_fn`, `max_iterations`) para testes deterministicos

### 4. `src/daemon/__main__.py` - Entry point
python -m src.daemon --symbol WINV26 --mode paper_mt5 --poll 5.0

Liga tudo:
- `build_system(use_mt5=True)` para o pipeline
- `MT5Adapter` como fonte de barras
- `tick_fn` busca barra nova (pula se timestamp igual)
- `reconnect_fn` reinicia MT5Adapter
- `Scheduler` com heartbeat/snapshot automaticos
- Shutdown gracioso: para engine, fecha store

## Uso

```powershell
# Paper trading via MT5 demo, loop resiliente
python -m src.daemon --symbol WINV26 --mode paper_mt5 --poll 5.0

# Teste rapido (3 iteracoes)
python -m src.daemon --symbol WINV26 --mode paper_mt5 --max-iterations 3

Cobertura de testes
tests/test_daemon_state.py (13 testes): CRUD, persistencia,
helpers, serializacao, validacoes

tests/test_daemon_scheduler.py (16 testes): registro, tick, due,
multi-tarefa, erros, remove, reset

tests/test_daemon_runner.py (17 testes): validacao, loop, shutdown,
reconnect, backoff, scheduler, state store

Suite total: 280 passed, 4 skipped (eram 234; +46).

Nao coberto (backlog)
Healthcheck HTTP no daemon: o daemon roda offline. Se a API
quiser saber o status, precisa ler o StateStore ou o daemon expor
um endpoint local.

Restart automatico no container: docker-compose tem
restart: unless-stopped, mas o daemon nao tem healthcheck proprio
que o Docker possa monitorar.

Metricas persistentes ao longo do dia: daemon_stats e cumulativo
entre reinicios. Se quiser reset diario, precisa de logica adicional.

Estrategias conectadas: o daemon usa build_system() que hoje
carrega DummyStrategy ou FeatureMLStrategy. Sem edge (ADR-020),
a operacao continua paper.

Alerta em trip do KillSwitch: o estado e persistido, mas nenhum
alerta externo (webhook) e disparado. AlertManager existe, mas
nao esta ligado no daemon.

Sinais de sistema (SIGINT/SIGTERM) em Windows: testado com
max_iterations, nao com Ctrl+C real em ambiente Windows. Testar em
producao antes de confiar.

Consequencias
Daemon pronto para operacao continua ✅

Persistencia de estado entre reinicios ✅

Reconnect resiliente com backoff ✅

Shutdown gracioso ✅

46 testes novos cobrindo state/scheduler/runner ✅

Docker Compose ja tem restart: unless-stopped para uso ✅

280 passed, 4 skipped (eram 234; +46)

+4 arquivos em src/daemon/

Alternativas descartadas
APScheduler: rejeitada por adicionar dependencia pesada para
um caso simples (tick() + tasks periodicas). Scheduler proprio e
~100 linhas testaveis.

AsyncIO: rejeitada por introduzir complexidade desnecessaria.
Todo o pipeline atual e sincrono; migrar para async seria um projeto
por si so.

Redis para estado: rejeitada por ser overkill. SQLite atende
operacao single-node.

Watchdog externo (systemd/Docker healthcheck): complementa o
daemon, mas nao substitui a resiliencia interna (reconnect, backoff).
Fica para milestone futuro.

Threads para tarefas periodicas: rejeitada por introduzir race
conditions. O tick do scheduler no mesmo loop e mais simples de
raciocinar.

Licao
"Operacao 24/7" nao requer threads, asyncio, nem frameworks pesados.
Um loop sincrono com backoff, scheduler trivial e persistencia minima
resolve 90% do problema. Complexidade adicional so quando houver
evidencia de necessidade.

Referencias cruzadas: ADR-009 (API), ADR-016 (EventBus), ADR-020
(achado sem edge).