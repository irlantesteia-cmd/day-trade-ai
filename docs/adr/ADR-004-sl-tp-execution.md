# ADR-004 - SL/TP no caminho de execucao MT5

- **Status**: Aceito
- **Data**: 2026-09-23

## Contexto

Auditoria identificou tres problemas no caminho de execucao de ordens:

- **P3.a** `MT5Adapter.execute_signal` enviava ordens ao MT5 **sem stop_loss
  nem take_profit**, mesmo com `SLTPCalculator` disponivel no projeto
- **P3.b** `quantity` era hard-coded em `1.0`, ignorando `PositionSizer`
- **P3.c** `RiskEngine.generate_order()` (que produz uma `Order` completa com
  SL/TP/quantity) existia mas nao era chamado em nenhum ponto do pipeline;
  o `LiveTradingEngine` chamava `adapter.execute_signal(signal, bar)`
  diretamente

Isso era um risco severo: qualquer ordem real ficaria sem protecao.

## Decisao

Corrigir **apenas P3.a** neste milestone (escopo minimo, Regra n. 1).

Mudancas:

1. `MT5Adapter.__init__` aceita `risk_config: Optional[RiskConfig]`
2. `MT5Adapter` instancia `SLTPCalculator(self.risk_config)`
3. Novo metodo privado `MT5Adapter._compute_sltp(signal, entry_price)`:
   - Le `signal.metadata["atr"]` se existir
   - Delega para `SLTPCalculator.calculate`
   - Fallback para `default_sl_pct` se calculator falhar
4. `MT5Adapter.execute_signal`:
   - Calcula `stop_loss` e `take_profit`
   - Adiciona campos `"sl"` e `"tp"` no request ao MT5
   - Retorna `Order` com `stop_loss` e `take_profit` preenchidos
5. `quantity` passa a ser lida de `signal.metadata["quantity"]` (fallback 1.0)

## Cobertura de testes

`tests/test_mt5_adapter.py` agora tem 7 testes:

1. `test_mt5_adapter_execute_signal` (existente, mantido)
2. `test_execute_signal_buy_with_atr_computes_sltp`
3. `test_execute_signal_sell_with_atr_computes_sltp`
4. `test_execute_signal_without_atr_uses_default_pct`
5. `test_request_includes_sl_tp_fields` (inspeciona o request enviado)
6. `test_quantity_taken_from_metadata`
7. `test_execute_signal_rejected_when_not_connected`

## Nao corrigido (escopo de milestones futuros)

- **P3.c** `RiskEngine.generate_order()` continua sem ser chamado pelo
  pipeline. O `LiveTradingEngine` chama `adapter.execute_signal(signal, bar)`
  diretamente. Refatorar isso e uma mudanca arquitetural maior (envolve
  `LiveTradingEngine`, `MT5ExecutionEngine` e `RiskEngine`) que deve ser
  tratada em milestone dedicado.

  Efeito residual: em producao, `quantity` continua 1.0 por padrao porque
  nenhuma estrategia popula `signal.metadata["quantity"]`. `PositionSizer`
  existe mas nao e usado.

## Consequencias

- Ordens enviadas ao MT5 agora tem SL/TP definidos ✅
- `Order` retornada carrega metadados completos (SL/TP) ✅
- Risco operacional imediato mitigado ✅
- Divida arquitetural P3.c registrada em `docs/roadmap.md` como problema
  conhecido, a resolver em milestone posterior

## Alternativas descartadas

- **Corrigir P3.a + P3.b + P3.c de uma vez**: rejeitada por violar Regra n. 1
  (nao construir tudo de uma vez). Mudanca de 3 pecas ao mesmo tempo dificulta
  isolamento de bugs futuros
- **Manter SL/TP hard-coded no adapter, sem calculator**: rejeitada porque
  duplicaria logica ja existente em `SLTPCalculator`
- **Passar `Order` pronta para o adapter (em vez de `Signal`)**: mudanca
  correta, mas pertence a P3.c (milestone futuro)
```text

---

**Depois de salvar, rode apenas este comando e cole o output:**

```powershell
Get-Item docs\adr\ADR-004-sl-tp-execution.md | Select-Object Name, Length