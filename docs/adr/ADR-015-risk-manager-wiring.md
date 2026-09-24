# ADR-015 - Wiring parcial do RiskManager

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

O ADR-008 (integracao do RiskEngine ao pipeline) deixou documentado que
`RiskManager` (com `can_take_trade`, `update_state`) nao era alimentado
em producao. O `RiskEngine.generate_order` chama `self.manager.can_take_trade()`,
mas como `update_state` nunca era chamado, o estado permanecia zerado:
daily_pnl_pct = 0.0
open_positions_count = 0

Resultado: `can_take_trade()` sempre retornava `True`. Os limites
`max_open_positions` e `max_daily_drawdown_pct` nunca ativavam em
producao (apenas nos testes unitarios que chamavam `update_state`
manualmente).

## Decisao

Implementar **wiring parcial**: sincronizar apenas `open_positions_count`
a cada barra. `daily_pnl_pct` permanece `0.0` neste milestone.

### Justificativa

**open_positions_count:**
- Fonte de verdade clara: `execution_engine.portfolio.positions`
- Sem estado adicional necessario
- Sem decisao de design pendente

**daily_pnl_pct:**
- Nao existe rastreador de PnL diario no sistema
- Requer decisao de design (dono do estado, reset diario, comparacao
  com equity de referencia)
- Introduziria estado mutavel no caminho critico
- Vai alem do escopo de "wiring" — e um subsistema novo

Segue Regra n. 1 do framework (nao construir tudo de uma vez).

### Mudancas

**1. `src/engine/live_engine.py`**

Novos helpers:
- `_current_open_positions() -> int`: conta posicoes em
  `execution_engine.portfolio.positions`
- `_sync_risk_manager_state() -> None`: chama
  `risk_engine.manager.update_state(daily_pnl_pct=0.0, open_positions_count=N)`
  com fallback silencioso (incrementa `total_errors` em falha)

`_process_with_risk_engine` chama `_sync_risk_manager_state()` antes de
`risk_engine.generate_order(...)`.

Docstring do modulo atualizada, mencionando a limitacao e referenciando
este ADR.

**2. `tests/test_live_engine.py`**

3 testes novos:
- `test_risk_manager_update_state_called_each_bar`: verifica que
  `update_state` e chamado a cada barra com valores corretos
- `test_risk_manager_blocks_when_max_positions_reached`: portfolio com
  `max_open_positions` ativo bloqueia geracao
- `test_risk_manager_allows_when_below_max_positions`: N < max permite

Usam `SpyRiskManager` e `RiskEngineWithSpyManager` (fakes que respeitam
o contrato real).

## Comportamento novo

Antes:
bar chega -> generate_order -> can_take_trade() SEMPRE True

Depois:
bar chega -> sync(open_positions_count) -> generate_order
-> can_take_trade() reflete portfolio real

`max_open_positions` agora funciona em producao.

## Nao coberto (backlog)

### 1. `max_daily_drawdown_pct` continua inativo

Requer `DailyPnLTracker`:
- Decide dono do estado (KillSwitch? RiskManager?)
- Decide reset (meia-noite do mercado? primeiro trade do dia?)
- Rastreia equity de referencia
- Atualiza a cada barra

Subsistema novo. Milestone futuro.

### 2. Duas fontes de protecao de drawdown

Existem hoje:
- `KillSwitch.check_daily_pnl(pnl)` — protecao externa, chamada manual
- `RiskManager.max_daily_drawdown_pct` — protecao interna, inativa

Precisam ser coordenadas (nao duplicadas). Ver ADR-008 e este ADR.

### 3. Contagem de posicoes so reflete portfolio local

Se houver posicoes abertas no MT5 nao registradas no portfolio local
(ex: ordens manuais, reconexao), a contagem fica errada. Precisa
integrar com `reconciler.py` (existe em `src/engine/reconciler.py`).

## Consequencias

- `max_open_positions` funcional em producao ✅
- `daily_pnl_pct` documentado como inativo ✅
- Nenhuma regressao (198 testes passando; eram 195; +3)
- Estado mutavel nao introduzido no caminho critico ✅
- `RiskManager` agora tem 1 das 2 protecoes ativas

## Alternativas descartadas

- **Implementar wiring completo (Opcao B)**: rejeitada por exigir
  decisao de design de DailyPnLTracker (dono, reset) e introduzir
  estado mutavel.
- **Nao fazer nada**: rejeitada por deixar `max_open_positions` inativo.
- **Acoplar RiskManager ao KillSwitch diretamente**: rejeitada por
  misturar responsabilidades (KillSwitch e global, RiskManager e por
  trade).

## Evidencia

Suite: 198 passed (195 + 3 novos)
Testes especificos: `tests/test_live_engine.py::test_risk_manager_*`