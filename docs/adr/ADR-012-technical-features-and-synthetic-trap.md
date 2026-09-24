# ADR-012 - Features tecnicas, armadilha do dataset sintetico e resultado honesto

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

O Milestone 2 (ADR-003) entregou o pipeline de ML completo:
FeatureSetRegistry, DatasetBuilder versionado, WalkForwardSplitter,
ModelRegistry. Mas o modelo logistico treinado com features "basic v1"
(log_returns + morfologia + time-of-day) teve edge NEGATIVO:
- Sintetico: -30.64 p.p.
- WIN$ M1: -8.60 p.p.

O Milestone 8 testou a hipotese H1: features tecnicas (RSI, SMA, ATR)
ajudam.

## Descobertas

### 1. Extratores tecnicos estavam desconectados do engine

Os extratores em `src/features/technical.py` esperavam chaves que o
`IndicatorEngine.compute_all()` nao gera:

| Extrator (antes) | Esperava | Engine fornecia |
|---|---|---|
| NormalizedRSIExtractor | `rsi_14` | `rsi` |
| SMADistanceExtractor | `sma_20` | `sma_fast`, `sma_slow`, `sma_10`, `sma_30` |
| BollingerPercentBExtractor | `bb_20` | (nao gerado) |

Isso explica porque nunca eram usados: falhavam silenciosamente
retornando `{feature: None}`.

### 2. Correcao (Opcao A do milestone)

- `NormalizedRSIExtractor` default: `"rsi_14"` -> `"rsi"`
- `SMADistanceExtractor` default: `"sma_20"` -> `"sma_fast"`
- Novo `ATRNormalizedExtractor` (feature `atr_norm`)
- `BollingerPercentBExtractor` mantido, documentado como "requer indicador custom"

### 3. Novos FeatureSets e helper

- `technical_v1()`: 8 features (2 log_returns + 3 morfologia + 3 tecnicas)
- `records_from_candles_with_indicators()`: calcula indicadores por candle
  com janela `candles[:i+1]` (sem look-ahead), remove records com
  features `None`
- `scripts/train_model_v3.py --feature-set basic|technical`
- `--model-id` default agora inclui o feature set

### 4. Resultado sintetico (suspeito)
FeatureSet: technical v1 (8 features)
Dataset: 1965 amostras | 50.8% positivos
Walk-forward: 14 folds

Edge medio: +17.29 p.p.
Folds positivos: 14/14 (100%)


**Todo fold positivo com edge > +2 p.p.** e um sinal classico de
overfitting a um padrao deterministico do dataset.

### 5. Resultado real (WINV26 M1, 20000 candles)
Dataset: 19965 amostras | 49.1% positivos
Walk-forward: 194 folds

Edge medio: -9.40 p.p.
Folds positivos: 31/194 (16%)

Consistente com o "basic v1" (-8.60 p.p.). Features tecnicas NAO
adicionam edge em M1 do mini-indice.

### 6. Confirmacao do artefato sintetico

Analise de autocorrelacao:

| Serie | lag-1 | lag-200 |
|---|---|---|
| Sintetico sem ciclo | 0.29 | — |
| Sintetico com ciclo | 0.49 | 0.33 |

O gerador `candles_sinteticos()` embute `cycle = 0.0005 * sin(2*pi*i/200)`.
Com features de periodo 14 (RSI, SMA, ATR), o modelo detecta "onde
esta no ciclo" com precisao quase perfeita. **Isso nao e edge real.**

## Decisao

1. Documentar honestamente: **o modelo logistico com features tecnicas
   nao tem edge em WINV26 M1**.
2. Manter a infraestrutura (FeatureSet, records, script) que esta
   correta e testada.
3. Nao fazer deploy deste modelo.
4. Corrigir o gerador sintetico em milestone futuro: remover o ciclo
   ou usa-lo apenas em testes que o declarem explicitamente.

## Consequencias

- `technical_v1` esta funcional e testado (14 testes em test_feature_sets.py)
- Pipeline ML continua sem edge comprovado
- PHASE 14 permanece PARCIAL
- 195 testes passando (eram 189; +6)
- Aprendizado: **dados sinteticos precisam ser realisticamente
  ruidosos**; caso contrario, o modelo overfitta ao artefato do
  gerador e mascara a ausencia de sinal

## Nao coberto (backlog)

- Testar `basic v1` + `technical v1` com timeframes maiores (M5, M15)
  — decisao de produto, fica para milestone futuro
- Testar modelos mais expressivos (Random Forest, Gradient Boosting)
  — precisa scikit-learn
- Adicionar features de regime (volatilidade, tendencia) como filtro
- Detector de ciclo/regime como pre-processamento

## Alternativas descartadas

- **Declarar vitoria com edge sintetico +17 p.p.**: rejeitada por
  violar a secao 73 do framework ("Nunca tratar backtest como garantia
  de resultado futuro. Nunca assumir que uma IA consegue prever o
  mercado de forma garantida.")
- **Reverter technical_v1 por ter edge negativo**: rejeitada por ser
  conhecimento valido. O feature set esta correto; o problema e o
  sinal do mercado.
- **Ajustar hiperparametros ate edge ficar positivo**: rejeitada por
  ser overfitting do walk-forward.

## Evidencia

Logs:
- Sintetico `basic`: 14 folds, edge -21.29 p.p.
- Sintetico `technical`: 14 folds, edge +17.29 p.p. (artefato)
- MT5 `technical` (WINV26 M1): 194 folds, edge -9.40 p.p.
- Analise de autocorrelacao confirmando ciclo deterministico

Modelo salvo em: `models/registry/logistic_v3_technical__v1/`