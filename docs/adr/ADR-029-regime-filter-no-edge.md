# ADR-029 - Filtro de regime nao tem edge robusto

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

O milestone 25 testou se o filtro de volatilidade transforma a
estrategia MA Crossover (edge -6.21 em WINV26 M5) em operavel.

Motivacao:
- Analise retrospectiva por tercis mostrou padrao monotono:
  - low vol: PF 0.87 | -13.97%
  - mid vol: PF 0.96 | -5.26%
  - high vol: PF 1.12 | +25.99%
- Sugeriu filtro "so opera em high vol"

## Metodologia

### Analise retrospectiva (com look-ahead)
`scripts/regime_split_analysis.py`:
  - Roda MA em toda a serie
  - Para cada trade, faz lookup do realized_vol_20 na entrada
  - Divide em tercis low/mid/high do total

**Problema:** tercis do total usam trades futuros. Em producao,
nao sabemos de antemao quais trades serao "high vol".

### Walk-forward honesto (sem look-ahead)
`src/strategies/regime_filtered_ma.py`:
  - A cada candle, computa realized_vol_20 dos candles ANTERIORES
  - Threshold = percentil 66 sobre rolling lookback de 500 vols
  - So opera se vol atual > threshold

`scripts/walk_forward_regime_filtered.py`:
  - 5 janelas consecutivas independentes
  - Cada janela com capital inicial proprio

## Resultados

### Analise retrospectiva (M25) - COM look-ahead
Bucket | PF | PnL | Trades
low | 0.87 | -13.97% | 398
mid | 0.96 | -5.26% | 397
high | 1.12 | +25.99% | 398
Walk-forward retrospectivo: high vol +8.13% medio | 4/5 folds+

### Walk-forward honesto (M25.8) - SEM look-ahead
Fold | Trades | PnL% | PF | Sharpe
0 | 75 | -2.16% | 0.98 | -0.32
1 | 70 | +8.22% | 1.33 | 5.09
2 | 85 | -4.81% | 0.89 | -2.89
3 | 71 | +23.25% | 1.73 | 11.28
4 | 84 | -3.91% | 0.94 | -1.66
PnL medio: +4.12% | Folds positivos: **2/5**

## Interpretacao

### 1. Look-ahead inflacionou o edge
Retrospectivo (com look-ahead): 4/5 folds positivos
Honesto (sem look-ahead): 2/5 folds positivos

A diferenca e o look-ahead. Tercis do whole-window "sabem" quais
trades vao vencer. Threshold rolante nao sabe.

### 2. Concentracao em 1 fold (padrao conhecido)
- Fold 3 sozinho: +23.25%
- Folds 0+1+2+4 somados: -2.66%

Sem o fold 3, o filtro e neutro.

Este e o mesmo padrao do ADR-025 (VolatilityBreakout): concentracao
em 1 janela especifica.

### 3. Filtro reduz trades mas nao melhora PF
- Sem filtro: 1198 trades | PF 1.01
- Com filtro: 385 trades | PF medio 1.13, mas 2/5 folds negativos

O filtro corta 2/3 dos trades e melhora marginalmente o PF. Mas a
variancia entre folds e alta demais.

## Decisao

**Nao operar com filtro de regime.** Razoes:
1. Walk-forward honesto: 2/5 folds positivos
2. Concentracao em 1 fold (padrao de fragilidade)
3. Filtro melhora marginalmente mas nao o suficiente

**Nao tentar "consertar"** ajustando percentil, lookback ou
timeframe — seria fishing (mesma logica dos ADRs 020, 022, 025).

## Consequencias

- RegimeFilteredMAStrategy implementada e testada ✅
- Dois scripts novos (analise retrospectiva + WF honesto) ✅
- Achado honesto: look-ahead inflacionou o edge ✅
- 7 familias testadas, todas negativas ou marginais
- 310 passed, 4 skipped (nao mudou)
- +2 scripts, +1 estrategia

## Licao

**Look-ahead bias e sutil e perigoso.** Uma analise retrospectiva
aparentemente correta (tercis por bucket) pode usar informacao do
futuro. Sempre que possivel, usar threshold rolante e walk-forward
honesto.

Segunda licao: **concentracao em 1 fold e o sinal mais confiavel de
falso edge.** Se 1 janela carrega a estrategia, e regime especifico
ou sorte, nao edge real.

Referencias cruzadas: ADR-020 (sem direcional), ADR-025 (concentracao),
ADR-026 (pairs), ADR-028 (cross-market).