# ADR-014 - Experimento multi-timeframe (M1, M5, M15)

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

Apos o ADR-012 (features tecnicas) e ADR-013 (remocao do ciclo
sintetico), a PHASE 14 (ML) continuava sem edge comprovado em M1.
O Milestone 10 testou a hipotese H2: **timeframes maiores reduzem
ruido e podem revelar edge.**

## Decisao

Adicionar suporte a `--timeframe` em `scripts/train_model_v3.py` e
rodar walk-forward em M1, M5 e M15 com o mesmo pipeline (technical_v1,
horizonte 5, lr 0.3, epochs 500).

## Implementacao

**1. `scripts/train_model_v3.py`**
- Novo mapa `TIMEFRAME_MAP` (M1, M5, M15, M30, H1)
- `candles_mt5(symbol, n, timeframe)` usa a constante correta do MT5
- Novo argumento `--timeframe` no argparse
- `--model-id` default agora inclui timeframe: `logistic_v3_<feature_set>_<tf>`
- Metadados do modelo incluem `timeframe` em `parameters`

**2. Sem mudanca em `src/`**
- Feature set, DatasetBuilder, WalkForwardSplitter, ModelRegistry
  permaneceram intactos

## Resultados (WINV26, 20000 candles solicitados)

| Timeframe | Candles | Amostras | Edge medio | Folds positivos |
|---|---|---|---|---|
| M1 | 19.965 | 19.965 | **-9.40 p.p.** | 31/194 (16%) |
| M5 | 8.433 | 8.433 | **-7.48 p.p.** | 15/79 (19%) |
| M15 | 3.103 | 3.103 | **-3.88 p.p.** | 9/26 (35%) |

## Interpretacao

### 1. Tendencia clara
Quanto maior o timeframe, menos negativo o edge. Progressao:
`-9.40 -> -7.48 -> -3.88 p.p.`

### 2. Ainda sem edge real
O criterio do ADR-003 (edge > +1.5 p.p., folds positivos > 40%) **nao
foi atingido em nenhum timeframe**. M15 chega a 35% de folds positivos,
mas o edge ainda e -3.88 p.p. (i.e., pior que sempre apostar na classe
majoritaria).

### 3. Historico limitado em M15
O MT5 so forneceu 3.103 candles M15 (vs. 19.965 em M1). Isso e limitacao
do broker para o contrato atual (WINV26). Para M30/H1, o historico
seria ainda menor.

### 4. Modelo logistico simples tem limite
Em M1/M5/M15, o modelo logistico com 8 features tecnicas nao captura
padrao suficiente. Nao e bug — e limitacao da combinacao
(modelo + features) testada.

## Conclusao honesta

**O modelo logistico simples com features tecnicas nao tem edge
comprovado em WINV26 em M1, M5 ou M15.**

A tendencia de melhora com timeframe maior e interessante mas nao
suficiente para operar. Proximos passos exigiriam:
- Modelos mais expressivos (Random Forest, Gradient Boosting)
- Features de regime (volatilidade, tendencia)
- Timeframes maiores (H1, H4) com mais historico
- Consideracao de spread e custos no treino

## Consequencias

- PHASE 14 permanece PARCIAL
- Infraestrutura multi-timeframe agora disponivel (`--timeframe`)
- 3 modelos versionados adicionais em `models/registry/`:
  - `logistic_v3_technical__v1` (M1, edge -9.40)
  - `logistic_v3_technical_M5__v1` (M5, edge -7.48)
  - `logistic_v3_technical_M15__v1` (M15, edge -3.88)
- Nenhum modelo deve ser usado em producao (todos com edge negativo)
- 195 testes passando (nenhuma regressao)

## Nao coberto (backlog)

- Testar modelos nao-lineares (precisa scikit-learn)
- Adicionar features de regime como filtro
- Testar M30/H1/H4 (historico limitado no broker atual)
- Considerar spread/commission no dataset
- Testar com outros contratos (WINFUT, IND) para comparar

## Licao

**Nenhum timeframe compensa um modelo fraco + features fracas.**
A melhora com timeframe e consistente com a literatura (microestrutura
domina em timeframes curtos), mas o efeito e modesto.

Referencias cruzadas:
- ADR-003 (criterio de aceitacao do modelo)
- ADR-012 (technical features)
- ADR-013 (remocao do ciclo sintetico)