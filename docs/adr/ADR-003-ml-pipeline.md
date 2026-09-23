# ADR-003 - Pipeline de ML e resultado do primeiro treino

- **Status**: Aceito
- **Data**: 2026-09-23

## Contexto

A FASE 14 (Machine Learning) estava marcada como parcial no roadmap.
Faltavam: Model Registry, Dataset versioning, FeatureSet versionado,
pipeline de treino reproduzivel e criterio de aceitacao mensuravel.

O Milestone 2 construiu essa infraestrutura e rodou o primeiro treino
formal com walk-forward em dados reais (WIN$ M1, 20000 candles).

## Decisao

### 1. Infraestrutura implementada

- `src/models/registry.py` - ModelRegistry + ModelMetadata
- `src/models/dataset.py` - DatasetBuilder com versionamento
- `src/features/sets.py` - FeatureSet + FeatureSetRegistry + records_from_candles
- `src/validation/splitter.py` - WalkForwardSplitter (ja existia)
- `scripts/train_model_v3.py` - Pipeline completo de treino

### 2. Criterio de aceitacao do modelo

Um modelo so deve ser considerado "operavel" se atender:

- Edge medio em walk-forward > +1.5 p.p.
- Folds positivos > 40% do total
- Aderencia entre treino e teste (sem colapso de accuracy)
- Estabilidade entre folds (baixa variancia do edge)

### 3. Resultado do primeiro treino honesto

**Dataset sintetico (5000 candles):**
- Edge medio: -30.64 p.p.
- Folds positivos: 1/44 (2%)
- Baseline por janela: 0.64 a 0.94
- Causa: gerador sintetico tem ciclo dominante + autocorrelacao

**Dataset real MT5 (WIN$ M1, 20000 candles):**
- Edge medio: -8.60 p.p.
- Folds positivos: 29/194 (15%)
- Baseline por janela: 0.51 a 0.88
- Causa: regime shift entre train (500c) e test (100c)

### 4. Diagnostico tecnico

O modelo logistico com features de log-return e morfologia de candle
nao tem poder preditivo em WIN$ M1. Analise dos folds revela:

- Quando baseline eh proximo de 0.50 (mercado equilibrado): modelo empata
- Quando baseline eh > 0.70 (regime definido): modelo erra sistematicamente

Isso indica que o modelo aprende a polaridade media do TRAIN, que
frequentemente eh OPOSTA a polaridade do TEST. Regressao logistica
simples nao detecta mudanca de regime.

### 5. Nao correcao neste milestone

A opcao de "consertar" o modelo agora foi rejeitada por violar a
Regra n. 1 do framework (nao construir tudo de uma vez). O Milestone 2
entrega infraestrutura, nao um modelo lucrativo.

## Consequencias

- Pipeline de ML esta pronto para proximos experimentos
- Modelo logistic_v3 v1 foi salvo em `models/registry/` mas NAO deve
  ser usado em producao (edge negativo)
- PHASE 14 permanece PARCIAL ate que um modelo com edge seja comprovado
- Proximos passos (ver `docs/roadmap.md`):
  - Novas features (indicadores tecnicos, volume, contexto)
  - Novos modelos (Random Forest, Gradient Boosting)
  - Deteccao de regime como filtro
  - Considerar timeframes maiores (M15, H1)

## Alternativas descartadas

- **Aceitar modelo com edge negativo**: rejeitada por violar preservacao de capital
- **Ajustar hiperparametros ate virar positivo**: rejeitada por ser overfitting
- **Testar apenas 1 fold e declarar sucesso**: rejeitada por falta de rigor
- **Aumentar train_window para 5000**: testavel em milestone futuro, mas nao resolve regime shift

## Evidencia

Logs dos treinos:
- Sintetico: 44 folds, edge -30.64 p.p., 1 positivo
- MT5 WIN$ M1: 194 folds, edge -8.60 p.p., 29 positivos

Modelo salvo em: `models/registry/logistic_v3__v1/`