# ADR-008 - Integracao do RiskEngine ao pipeline de execucao

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

O backlog registrava P3.c: `RiskEngine.generate_order()` existia mas nao
era chamado em nenhum ponto do pipeline de producao. O fluxo real era:
strategy.generate_signal(bar) -> Signal
|
v
execution_engine.execute_signal(signal, bar) (sem RiskEngine)
|
v
MT5Adapter.execute_signal (calcula SL/TP e quantidade internamente)
|
v
Order


Alem disso, `build_system` passava `risk_manager=None` para o
`LiveTradingEngine`. Resultado: nenhuma validacao booleana nem calculo
de position sizing acontecia em producao. O `RiskEngine` (com
`SLTPCalculator` + `PositionSizer`) ficava apenas no backtest e nos
testes.

A secao 33 do framework define o fluxo correto:
Signal -> Risk Check -> OrderIntent -> ExecutionEngine -> Broker -> Order

## Decisao

Integrar `RiskEngine` ao `LiveTradingEngine` **preservando compatibilidade
com o fluxo legado**. Escolhida a opcao de escopo minimo (apenas A,
sem wiring completo de RiskManager).

### Mudancas

**1. `src/engine/mt5_bridge.py`**
- `MT5ExecutionEngine` ganha `execute_order(order, bar)`:
  extrai `bar["close"]` e delega para `adapter.execute_order(order, price)`
- `execute_signal` mantido para compatibilidade

**2. `src/engine/live_engine.py`**
- Novo parametro opcional `risk_engine=None`
- `process_bar` bifurca:
  - Se `risk_engine is not None`: chama `_process_with_risk_engine`
  - Senao: chama `_process_legacy` (comportamento original preservado)
- `_process_with_risk_engine`:
  - Calcula `price = bar["close"]`
  - Calcula `balance` via `_current_balance()` (le `execution_engine.portfolio.equity`
    com fallback para `balance`, `cash`, ou 10000.0)
  - Chama `risk_engine.generate_order(signal, price, balance)`
  - Se `None` -> incrementa `signals_rejected_risk`, retorna `None`
  - Se Order -> chama `execution_engine.execute_order(order, bar)` (se existir)
    ou fallback para `execute_signal`
- `_process_legacy` preserva integralmente o comportamento anterior

**3. `src/main.py`**
- Import adicionado: `from src.risk.engine import RiskEngine`
- `build_system` instancia `risk_engine = RiskEngine()`
- Passado para `LiveTradingEngine(..., risk_engine=risk_engine)`

**4. `tests/test_live_engine.py`**
- 3 testes legado mantidos (nao quebraram)
- 3 testes novos cobrindo o fluxo `risk_engine`:
  - gera Order e executa via `execute_order` (verifica quantity=2.0, SL/TP)
  - rejeicao -> `None` + `signals_rejected_risk` incrementado
  - balance vem de `execution_engine.portfolio.equity` (50000.0)

## Compatibilidade

- `LiveTradingEngine(risk_engine=None)` -> comportamento original
- `LiveTradingEngine(risk_engine=...)` -> novo fluxo
- `MT5ExecutionEngine` mantem `execute_signal` e adiciona `execute_order`
- `build_system` passa `risk_engine` sempre; `risk_manager` continua `None`
- 167 testes passando (eram 164; +3 do novo fluxo)

## Consequencias

- `RiskEngine` agora gera Order com SL/TP + PositionSizer ✅
- Fluxo alinhado com secao 33 do framework ✅
- Compatibilidade com codigo legado preservada ✅
- Nenhum teste quebrado ✅
- P3.c fechado (parcialmente)

## Nao corrigido (escopo de milestones futuros)

- **RiskManager wiring**: `RiskManager` (com `can_take_trade`,
  `update_state`) continua sem ser usado em producao. Requer alimentar
  `daily_pnl_pct` e `open_positions_count` no caminho critico, o que
  introduz estado mutavel. Milestone futuro.
- **P3.b**: `quantity` continua sendo calculada pelo `PositionSizer` do
  `RiskEngine` agora (nao mais de `signal.metadata["quantity"]`), mas a
  logica de position sizing ainda nao considera risco por trade real do
  portfolio. Fica para refinamento.
- **Signal bypass**: `RiskEngine.generate_order` retorna `None` se
  `signal.direction == NEUTRAL`. A estrategia atual (MLSignalStrategy)
  so emite BUY/SELL, entao isso nao afeta. Mas estrategias futuras
  precisam respeitar esse contrato.

## Alternativas descartadas

- **Opcao B (wiring completo de RiskManager)**: rejeitada por introduzir
  estado mutavel no caminho critico (race condition potencial) e por
  exigir refatoracao do `KillSwitch`.
- **Deletar `execute_signal` e migrar tudo para `execute_order`**:
  rejeitada por quebrar compatibilidade com testes existentes e com
  `CLI runner`.
- **Injetar RiskEngine dentro de MT5ExecutionEngine**: rejeitada por
  violar separacao de camadas (execution nao deve decidir risco).

## Estado residual (backlog)

Atualizar `docs/roadmap.md`:
- P3.c: ✅ resolvido (RiskEngine integrado)
- Novo item: RiskManager wiring (media prioridade)
- Novo item: position sizing real por portfolio (media prioridade)