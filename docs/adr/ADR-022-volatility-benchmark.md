# ADR-022 - Benchmark de previsao de volatilidade (nao-direcional)

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

Apos o ADR-020 consolidar "nenhuma estrategia direcional tem edge em
nenhum ativo/timeframe testado", foi testada uma hipotese alternativa
cientificamente suportada:

**Volatilidade tem memoria (volatility clustering, Engle 1982).**
Se verdadeira, e previsivel mesmo quando direcao nao e.

Target binario:
    label = 1 se |close[t+H] - close[t]| / close[t] > threshold
    label = 0 caso contrario

Threshold: mediana dos movimentos absolutos futuros (balanceia classes
em ~50/50).

Features: 4 features de volatilidade (src/features/volatility.py):
  - realized_vol_20: std de log returns em 20 barras
  - vol_ratio_5_20: vol curta / vol longa (expansao vs contracao)
  - range_ratio_14: media de (high-low)/close
  - bb_width_20: largura das bandas de Bollinger normalizada

Modelo: LogisticRegressionModel (mesmo do pipeline ML direcional).

## Metodologia

- Walk-forward: train=500, test=100, epochs=500, lr=0.3
- Mesmo rigor do ADR-019 (benchmark de estrategias)
- 4 combinacoes testadas: WINV26 M5/M15, PETR4 M5, WDOX26 M5

## Resultados

| Ativo   | TF  | Amostras | Threshold | Edge medio | Folds +      |
|---------|-----|----------|-----------|------------|--------------|
| WINV26  | M5  | 8468     | 0.111%    | **+4.87**  | **56/79 (71%)** |
| PETR4   | M5  | 19970    | 0.168%    | -1.91      | 66/194 (34%) |
| WDOX26  | M5  | 2226     | 0.086%    | +0.94      | 10/17 (59%)  |
| WINV26  | M15 | 3119     | 0.214%    | -0.77      | 14/26 (54%)  |

Criterio ADR-003: edge > +1.5 p.p. e >40% folds positivos.

## Interpretacao

### 1. Nao generaliza
Apenas 1 das 4 combinacoes atinge o criterio (WINV26 M5). As outras
3 sao: negativa, marginalmente positiva, neutra.

### 2. Padrao de falso positivo por selecao
Se o experimento tivesse sido restrito a WINV26 M5, o resultado
(+4.87 p.p., 71% folds) pareceria uma descoberta. Mas o teste
multi-ativo/timeframe mostrou que o sinal evapora.

Isso e exatamente o que o framework alerta (secao 27, overfitting;
secao 73, nao tratar backtest como garantia).

### 3. Hipotese cientifica continua valida, mas features sao fracas
Volatility clustering e um fato empirico estabelecido (Bollerslev 1986,
GARCH literature). MAS: as features simples usadas (RV, vol ratio,
range ratio, BB width) nao capturam o sinal de forma robusta em
walk-forward OOS.

Razao provavel: o modelo logistico com essas 4 features aprende
padroes especificos da amostra de treino que nao generalizam. Modelos
especializados de volatilidade (GARCH, EGARCH, HAR-RV) sao a
ferramenta adequada — e teriam que ser implementados como componente
proprio (nao como features de um modelo logistico).

### 4. WINV26 M5 pode ter edge real, mas com ressalvas
E possivel que WINV26 M5 (+4.87) tenha edge real, especifico deste
contrato. Mas com 1/4 de confirmacao, nao ha evidencia suficiente
para operar.

Amostras grandes de mais ativos/timeframes seriam necessarias para
distinguir "sinal real" de "coincidencia".

## Decisao

**Nao operar com base nesse resultado.** A hipotese de volatilidade
previsivel permanece aberta, mas o approach testado (features simples
+ logístico) nao demonstrou robustez.

**Nao insistir** ajustando features ou hiperparâmetros — seria
fishing (mesma logica do ADR-020).

## Consequencias

- Infraestrutura de features de volatilidade criada ✅
- Script `benchmark_volatility.py` reutilizavel ✅
- Achado honesto documentado ✅
- FASE 14 permanece PARCIAL ✅
- 280 passed, 4 skipped (nao mudou; sem novos testes formais ainda)
- +1 arquivo em `src/features/`, +1 script

## Nao coberto (backlog)

- **Modelos dedicados de volatilidade** (GARCH, EGARCH, HAR-RV):
  requer implementacao especifica. Nao e "feature", e modelo proprio.
- **Threshold dinamico**: hoje o threshold e a mediana global. Poderia
  ser condicionado a regime.
- **Horizonte diferente**: testamos apenas H=5. Horizontes maiores
  (H=20) poderiam ter mais sinal (menos ruido).
- **Features adicionais**: intraday high-low, Parkinson volatility,
  Garman-Klass, realized semivariance (up vs down moves).
- **Detector de regime**: separar trending vs ranging antes de
  aplicar o modelo.

## Licao

**Dados multi-ativo sao a defesa mais barata contra falso positivo.**
O WINV26 M5 isolado pareceria uma descoberta; o teste multi-ativo
revelou que e variacao estatistica.

Esta licao se soma ao ADR-020: nao basta "achar um resultado positivo",
e preciso confirmar que ele generaliza.

Referencias cruzadas: ADR-003, ADR-012, ADR-019, ADR-020.