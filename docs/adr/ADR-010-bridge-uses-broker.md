# ADR-010 - MT5ExecutionEngine adota interface Broker

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

A FASE 19 (Broker Abstraction) foi parcialmente endereçada em milestones
anteriores:

- M3.B (ADR-005): criou a interface `Broker` (ABC) em
  `src/execution/broker_base.py` e adicionou `execute_order` em
  `MT5Adapter` e `PaperBroker`.
- M3.A (ADR-004): SL/TP enviados ao MT5.

Porem o `MT5ExecutionEngine` (`src/engine/mt5_bridge.py`) continuava
acoplado a `MT5Adapter` via parametro `adapter=`. Nao aceitava qualquer
implementacao da interface `Broker`. Isso impedia:

- Testar o bridge com um broker mockado (sem MT5 instalado)
- Trocar MT5Adapter por PaperBroker ou outro broker futuramente
- Reuso do bridge em backtests

## Decisao

Refatorar `MT5ExecutionEngine` para aceitar um `Broker` formal,
preservando compatibilidade com o parametro `adapter=`.

### Mudancas

**`src/engine/mt5_bridge.py`**

`__init__` agora:
1. Aceita `broker=` (novo) OU `adapter=` (retrocompat)
2. Prioridade: `broker` > `adapter` > `MT5Adapter()` (default)
3. Mantem `self.adapter` como alias de `self.broker` (compatibilidade
   estrutural para codigo legado que le `engine.adapter`)
4. Auto-inicializa se broker tiver `is_connected=False` e metodo
   `initialize()`

`execute_signal(signal, bar)`:
- Verifica se `broker` tem `execute_signal`
- Se nao tiver, levanta `AttributeError` com mensagem clara
  (indica o tipo do broker e sugere `execute_order`)

`execute_order(order, bar)`:
- Extrai `bar["close"]` (fallback 0.0)
- Delega para `broker.execute_order(order, current_price)`

**`tests/test_mt5_bridge.py`**
- Teste legado mantido (1)
- 7 testes novos cobrindo:
  - `broker=` kwarg funciona
  - `adapter=` kwarg continua funcionando (retrocompat)
  - sem kwargs, cria MT5Adapter
  - `execute_order` delega corretamente (extrai preco do bar)
  - `bar` sem `close` cai para 0.0
  - `execute_signal` levanta AttributeError se broker nao suporta
  - `MT5Adapter` suporta ambas interfaces

## Compatibilidade

Todo o codigo existente continua funcionando sem alteracao:

- `src/main.py` instancia `MT5ExecutionEngine(adapter=mt5_adapter)` -> OK
- `tests/test_mt5_bridge.py::test_mt5_execution_engine_execute` -> OK
- `LiveTradingEngine._process_with_risk_engine` chama
  `execution_engine.execute_order(order, bar)` -> OK
- `LiveTradingEngine._process_legacy` chama
  `execution_engine.execute_signal(signal, bar)` -> OK

## Consequencias

- MT5ExecutionEngine agora aceita qualquer implementacao da interface
  `Broker` ✅
- Testavel com broker mockado (sem MT5) ✅
- Retrocompativel com `adapter=` ✅
- `self.adapter` mantido como alias (nao quebra codigo legado) ✅
- 184 testes passando (eram 177; +7)
- FASE 19 (Broker Abstraction) agora substancialmente completa

## Nao coberto (backlog da FASE 19)

- `PaperBroker` continua sem teste integrado ao `MT5ExecutionEngine`
  (so `PaperBroker` unitario em `test_execution.py`). Adicionar em
  milestone futuro.
- `MT5Adapter.execute_signal` continua sendo a unica interface que
  calcula SL/TP internamente. Codigo novo deve preferir `execute_order`
  (que recebe Order pronta via RiskEngine, per ADR-008).
- Alias `engine.adapter` deve ser removido apos confirmar que nenhum
  consumidor externo o usa.

## Alternativas descartadas

- **Remover `adapter=`**: rejeitada por quebrar `src/main.py` e
  `test_mt5_bridge.py`. Retrocompatibilidade e preferivel.
- **Nao manter alias `self.adapter`**: rejeitada por quebrar
  consumidores que leem `engine.adapter` (mesmo que hoje sejam poucos).
- **Forcar `broker=` como unico parametro**: rejeitada porque o nome
  `adapter` ja esta estabelecido no codebase.

## Estado residual (backlog)

Atualizar `docs/roadmap.md`:
- PHASE 19 (Broker Abstraction): ⚠️ -> ✅ (substancialmente completa)
- Item: adicionar teste integrado PaperBroker + MT5ExecutionEngine
- Item: remover alias `engine.adapter` em milestone futuro