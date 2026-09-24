# ADR-016 - Event Bus sincrono

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

A secao 39 do framework define 15 tipos de evento oficial (MarketDataReceived,
CandleClosed, SignalGenerated, OrderFilled, etc.). A secao 59 (Auditoria) e
a secao 60 (Decision Trace) preveem rastreamento ponta-a-ponta.

Antes deste milestone:
- Nao existia Event Bus
- Metricas eram incrementadas manualmente em `LiveTradingEngine`
- Nao havia publicacao/assinatura de eventos
- `AlertManager` (em telemetria) tinha um mini pub/sub, mas especifico
  para alertas e nao tipado por EventType

## Decisao

Criar um **Event Bus sincrono** minimalista, alinhado com a nomenclatura
oficial do framework.

### Arquitetura
src/events/
├── init.py exporta Event, EventType, EventBus, EventHandler
├── base.py EventType (enum, 15 tipos) + Event (dataclass)
└── bus.py EventBus (subscribe / subscribe_all / publish)

src/engine/live_engine.py
publica 3 eventos + SYSTEM_ERROR em excecao


### Design

**`EventType` (str, Enum):** 15 tipos conforme secao 39 do framework.

**`Event` (dataclass):**
- `event_type: EventType`
- `payload: Dict[str, Any]`
- `correlation_id: Optional[str]` (para rastreamento)
- `timestamp: datetime` (UTC, auto)
- `to_dict()` para serializacao

**`EventBus`:**
- `subscribe(event_type, handler)` — handler tipado
- `subscribe_all(handler)` — wildcard
- `unsubscribe(event_type, handler)` — remove handler
- `publish(event)` — chama handlers especificos + wildcard
- Historico opcional (`keep_history=True`, `max_history=1000`)
- `handlers_count()`, `get_history()`, `clear()`, `clear_history()`

### Caracteristicas

- **Sincrono**: `publish` executa handlers na mesma thread, na ordem de
  registro
- **Tolerante a falhas**: excecao em um handler e logada e engolida;
  os demais handlers executam
- **Nao thread-safe por design**: se concorrencia for necessaria no
  futuro, envolver com Lock
- **Retrocompativel em `LiveTradingEngine`**: `event_bus=None` (default)
  mantem comportamento anterior sem publicacao

### Integracao com `LiveTradingEngine`

`LiveTradingEngine.__init__` ganha `event_bus: Optional[EventBus] = None`.

Metodo privado `_publish(event_type, payload)`:
- Best-effort: se `event_bus` for `None`, no-op
- Se `publish` levantar, incrementa `event_publish_errors` mas nao
  derruba o pipeline

Eventos publicados (no fluxo novo e legado):

| Evento | Quando |
|---|---|
| `SIGNAL_GENERATED` | Apos `strategy.generate_signal` retornar sinal |
| `RISK_REJECTED` | Quando `risk_engine.generate_order` retorna `None`, ou `risk_manager.validate_signal` retorna `False` (legado) |
| `ORDER_FILLED` | Apos `execution_engine.execute_order` (ou `execute_signal` legado) |
| `SYSTEM_ERROR` | Em excecao de `generate_order` ou `execute_order` |

## Cobertura de testes

**`tests/test_events.py`** (15 testes):
- EventType tem os 15 membros esperados
- Event.to_dict serializa corretamente
- Publish chama handler especifico, nao chama outros
- Wildcard recebe todos os eventos
- Multiplos handlers chamados em ordem
- Excecao em handler nao quebra os demais
- `publish` rejeita nao-Event
- Historico: desabilitado por padrao, registrado quando ligado, capado
  em `max_history`, clear
- Unsubscribe / clear handlers
- handlers_count especifico e total

**`tests/test_live_engine.py`** (+5 testes):
- `SIGNAL_GENERATED` publicado
- `ORDER_FILLED` publicado
- `RISK_REJECTED` publicado
- Sem sinal = sem eventos
- `event_bus=None` nao quebra pipeline

Suite total: **218 passed** (eram 198; +20).

## Nao coberto (backlog)

- **Event Bus assincrono** (fila, worker thread)
- **Persistencia de eventos** (disco, DB)
- **Filtros por payload** (ex: so eventos de um symbol)
- **Integracao com `MetricsCollector`** como subscriber automatico
  (hoje metrics sao incrementadas manualmente — poderiam ser reativas)
- **Decision Trace completo** (secao 60): requer persistir todos os
  eventos com `correlation_id` ponta-a-ponta
- **`CANDLE_CLOSED`, `POSITION_OPENED/CLOSED`, `STOP_LOSS_TRIGGERED`**:
  eventos definidos no enum mas ainda nao publicados (falta fonte)
- **Rate limiting / backpressure**
- **Dead-letter queue** para handlers falhando

## Consequencias

- 15 tipos de evento formalizados ✅
- EventBus testado e desacoplado ✅
- `LiveTradingEngine` publica 3 eventos + erros ✅
- Compatibilidade total (`event_bus=None`) ✅
- Base para Decision Trace (secao 60) ✅
- 218 testes passando (eram 198; +20)
- +3 arquivos novos em `src/events/`

## Alternativas descartadas

- **Usar `AlertManager` como base do EventBus**: rejeitada porque
  `AlertManager` e especifico para alertas (com `AlertLevel`), nao para
  eventos genericos tipados.
- **Event Bus assincrono (queue + worker)**: rejeitada por introduzir
  complexidade de concorrencia desnecessaria. Sincrono atende 100% dos
  casos atuais.
- **Integrar EventBus diretamente como subscriber de MetricsCollector
  agora**: rejeitada por escopo. Metricas continuam manuais neste
  milestone; migrar para reativo fica para futuro.
- **Adicionar `Lock` para thread-safety**: rejeitada por escopo. Nao
  ha concorrencia no pipeline atual.

## Licao

Event bus nao e over-engineering se ha uso concreto: `Decision Trace`
(secao 60) e `Auditoria` (secao 59) sao requisitos explicitos do framework.
Um bus sincrono minimalista atende sem custo arquitetural.