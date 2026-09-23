# ADR-006 - Consolidacao de engine.py / executor.py

- **Status**: Aceito
- **Data**: 2026-09-23

## Contexto

Existiam dois arquivos definindo a mesma classe `ExecutionEngine`:

- `src/execution/engine.py`
- `src/execution/executor.py`

Ambos tinham assinatura `__init__(initial_balance, broker, portfolio)` e
metodo `process_order(order, current_price) -> Order`. As diferencas eram:

**engine.py:**
- Imports nao usados (`Optional`, `Dict`, `Any`, `PositionSide`, `OrderDirection`)
- Fazia `self.broker.portfolio = self.portfolio` (sincronizacao broker/engine)

**executor.py:**
- Sem imports nao usados
- Salvaguardas defensivas de portfolio:
    - `if not hasattr(cash) and hasattr(balance): cash = balance`
    - `if not hasattr(positions): positions = {}`

Importadores:
- `src/backtest/engine.py` -> `executor`
- `tests/test_execution.py` -> **ambos** (linha 3 e linhas 41/81)
- `tests/test_pipeline.py` -> `engine`

## Decisao

Consolidar em **`src/execution/engine.py`** (nome canonico, consistente com
`risk/engine.py`, `backtest/engine.py`, `live_engine.py`).

### Mudancas

1. `src/execution/engine.py` recebe:
   - Salvaguardas defensivas do antigo `executor.py`
   - Sincronizacao `self.broker.portfolio = self.portfolio` (comportamento
     herdado do antigo `engine.py`)
   - Imports nao usados removidos

2. `src/backtest/engine.py` passa a importar de `engine`

3. `tests/test_execution.py`:
   - Import no topo atualizado para `engine`
   - Import redundante dentro de uma funcao removido

4. `src/execution/executor.py` **deletado**

### Comportamento

O contrato publico de `ExecutionEngine` nao mudou. Todos os testes
continuam passando (164 passed).

## Consequencias

- Um unico `ExecutionEngine` canonico ✅
- Codigo morto removido ✅
- Salvaguardas defensivas preservadas ✅
- Sincronizacao broker/engine preservada ✅
- ADR-005 (interface Broker) respeitado ✅

## Alternativas descartadas

- **Manter `executor.py`**: rejeitada por manter duplicacao.
- **Manter `engine.py` como canonico sem salvaguardas**: rejeitada
  porque quebraria o comportamento esperado por `test_execution.py::test_paper_execution_slippage_and_fees`
  (broker sem portfolio proprio ficaria desincronizado do engine).
- **Criar um terceiro arquivo e migrar tudo**: rejeitada por complexidade
  desnecessaria.

## Estado residual (backlog)

- A duplicacao de nomes `PortfolioManager` (`src/execution/portfolio.py`
  vs `src/portfolio/manager.py`) continua. Milestone 4.C vai tratar.