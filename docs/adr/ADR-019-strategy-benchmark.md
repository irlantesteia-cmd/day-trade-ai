# ADR-019 - Benchmark de estrategias nao-ML

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

Apos os experimentos de ML (ADR-012, ADR-013, ADR-014), o modelo
logistico com features tecnicas permanecia sem edge comprovado em
WINV26 (edge -3.88 a -9.40 p.p. dependendo do timeframe).

Nunca haviam sido testadas em walk-forward as duas estrategias nao-ML
ja implementadas:
- `MovingAverageCrossoverStrategy` (BUY se sma_fast > sma_slow)
- `RSIMeanReversionStrategy` (BUY se RSI <= 30, SELL se RSI >= 70)

Pergunta a responder: **alguma estrategia existente tem edge?**

## Decisao

Criar `scripts/benchmark_strategies.py` reutilizando a infraestrutura
dos ADRs anteriores (walk-forward de janelas 100, horizonte 5, edge
sobre baseline).

### Implementacao

**`scripts/benchmark_strategies.py`** (novo):
- Reutiliza `candles_sinteticos` (AR(1) puro, sem ciclo) e `candles_mt5`
  (com `--timeframe`) do `train_model_v3.py`
- `strategy_predictions(candles, strategy, indicator_engine, ...)`:
  para cada candle i, computa `IndicatorEngine.compute_all` na janela
  `candles[:i+1]` (sem look-ahead), chama `strategy.evaluate`, extrai
  label (BUY=1, SELL=0, NEUTRAL=None)
- `walk_forward_accuracy(predictions, test_window=100)`: divide em folds
  de 100; em cada fold considera apenas predicoes ativas (label != None);
  calcula acc, baseline (max(pos_rate, 1-pos_rate)) e edge_pp
- Folds com menos de 5 predicoes ativas sao ignorados
- Salva JSON em `models/benchmarks/`

**`tests/test_benchmark_strategies.py`** (novo, 10 testes):
- candles_sinteticos basico
- signal_to_label: BUY, SELL, NEUTRAL, None
- strategy_predictions retorna campos esperados
- walk_forward_accuracy: acc/baseline/edge, ignora neutral,
  calcula edge corretamente

### Ajuste em RSI Mean Reversion

`RSIMeanReversionStrategy` e instanciado no benchmark com
`rsi_key="rsi"` (nao o default `"rsi_14"`), porque
`IndicatorEngine.compute_all()` retorna a chave `"rsi"`.
A estrategia em si nao foi alterada.

## Resultados (WINV26)

| Estrategia      | TF  | Folds | Edge medio | Folds +    | Total preds |
|-----------------|-----|-------|------------|------------|-------------|
| MA_CROSSOVER    | M5  | 85    | -6.21 p.p. | 17/85 (20%)| 8448        |
| RSI_REVERSION   | M5  | 85    | -13.13 p.p.| 24/85 (28%)| 2393        |
| MA_CROSSOVER    | M15 | 32    | -6.84 p.p. |  5/32 (16%)| 3109        |
| RSI_REVERSION   | M15 | 31    | -9.87 p.p. |  9/31 (29%)| 961         |

Comparacao com modelo ML logistico (M10):
- ML logístico M5:  -7.48 p.p. | 15/79 (19%)
- ML logístico M15: -3.88 p.p. |  9/26 (35%)

## Interpretacao

**1. Nenhuma estrategia tem edge.**

Todas as metricas sao negativas. Nenhum timeframe/estrategia atinge o
criterio do ADR-003 (edge > +1.5 p.p., >40% folds positivos).

**2. Ordem "simples -> complexo" se confirma parcialmente.**

O modelo logistico com features tecnicas tem edge menos negativo que
MA/RSI em M15 (-3.88 vs -6.84 e -9.87). Em M5, ML logístico (-7.48)
tambem e comparavel a MA (-6.21).

Conclusao: o pipeline ML nao esta pior que alternativas mais simples;
o problema e a ausencia de sinal no instrumento testado.

**3. RSI_REVERSION e pior que MA_CROSSOVER.**

Reversao a media perde em mercados com micro-tendencia. Esperado em
timeframes curtos.

**4. Nenhuma regra foi invertida por engano.**

Se MA e RSI fossem anti-preditivas (regras invertidas), suas edges
seriam sistematicamente negativas em valor alto (ex: -30 p.p.). Os
valores (-6 a -13) sao consistentes com "sem edge, apenas desperdicio
de sinal".

## Consequencias

- Resposta definitiva: **nenhuma estrategia testada tem edge em WINV26**
- Pipeline ML nao e pior que alternativas classicas
- FASE 14 (ML) permanece PARCIAL
- 234 passed, 4 skipped (eram 224; +10)
- 2 arquivos novos: `scripts/benchmark_strategies.py` e
  `tests/test_benchmark_strategies.py`

## Nao coberto (backlog)

- **Ativos alternativos**: nenhum teste em outros contratos (WDO, IND,
  PETR4) — o broker tem estes simbolos, mas o escopo do M15 foi
  minimal (WINV26)
- **Timeframes maiores**: M30, H1 nao testados (historico limitado)
- **Parametros alternativos**: MA com periodos diferentes (5/20, 10/50),
  RSI com niveis diferentes (20/80) — nao testados
- **Combinacao MA + RSI**: consensus entre estrategias nao avaliado
- **Custos**: benchmark nao considera spread/commission (assume edge
  teorico; na pratica o edge real seria ainda pior)

## Alternativas descartadas

- **Adicionar scikit-learn e testar Random Forest antes do benchmark**:
  rejeitada por violar ordem "simples -> complexo". Benchmark primeiro
  da linha de base; se MA/RSI tambem nao tem edge, o problema nao e
  o modelo.
- **Testar apenas 1 timeframe**: rejeitada por limitar conclusao.
- **Alterar parametros ate encontrar edge**: rejeitada por ser
  overfitting do walk-forward (mesmo problema que ADR-012 alertou).
- **Usar `OutOfSampleSplitter` em vez de walk-forward**: rejeitada por
  walk-forward ser mais robusto (multi-fold, nao apenas 1 split).

## Licao

Confirmacao adicional de que o problema nao e o modelo. Se MA Crossover
classico (regra milenar) nao tem edge em WINV26, e porque o instrumento
atual nao oferece sinal exploravel por indicadores tecnicos puros. O
passo seguinte honesto seria:
- Testar em outros instrumentos (WDO, IND, PETR4)
- Ou aceitar que este broker/contrato/instrumento nao tem edge com
  as ferramentas testadas

Referencias cruzadas: ADR-003 (criterio de aceitacao), ADR-012, ADR-013,
ADR-014.