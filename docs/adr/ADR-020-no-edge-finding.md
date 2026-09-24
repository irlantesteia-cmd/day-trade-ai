# ADR-020 - Nenhuma estrategia testada tem edge (achado consolidado)

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

Ao longo dos milestones M8 (ML technical_v1), M10 (multi-timeframe),
M15 (benchmark de estrategias nao-ML) e M16 (benchmark multi-ativo),
foram testadas ~20 combinacoes de:

- 4 familias de estrategia (ML logistico, MA Crossover, RSI Reversion,
  e o FeatureMLStrategy que envolve ML)
- 5 ativos (WINV26, WDOX26, PETR4, VALE3, ITUB4)
- 4 timeframes (M1, M5, M15, M30)
- 2 horizontes de previsao (5, 20 candles)

**Todas as ~20 combinacoes resultaram em edge medio NEGATIVO.**

## Inventario completo

### ML logistico (8 features: log_returns + morfologia + RSI/SMA/ATR)
| Ativo | TF | Horizon | Edge | Folds + |
|---|---|---|---|---|
| WINV26 | M1 | 5 | -9.40 | 31/194 (16%) |
| WINV26 | M5 | 5 | -7.48 | 15/79 (19%) |
| WINV26 | M15 | 5 | -3.88 | 9/26 (35%) |

### MA Crossover
| Ativo | TF | Horizon | Edge | Folds + |
|---|---|---|---|---|
| WINV26 | M5 | 5 | -6.21 | 17/85 (20%) |
| WDOX26 | M5 | 5 | -6.83 | 7/23 (30%) |
| PETR4 | M5 | 5 | -6.54 | 44/200 (22%) |
| VALE3 | M5 | 5 | -7.09 | 41/200 (20%) |
| ITUB4 | M5 | 5 | -7.58 | 25/200 (12%) |
| PETR4 | M15 | 5 | -9.03 | 30/200 (15%) |
| PETR4 | M30 | 5 | -7.27 | 33/183 (18%) |
| PETR4 | M5 | 20 | -13.92 | 25/200 (12%) |

### RSI Reversion
| Ativo | TF | Horizon | Edge | Folds + |
|---|---|---|---|---|
| WINV26 | M5 | 5 | -13.13 | 24/85 (28%) |
| WDOX26 | M5 | 5 | -11.29 | 8/22 (36%) |
| PETR4 | M5 | 5 | -9.22 | 64/198 (32%) |
| VALE3 | M5 | 5 | -9.43 | 53/200 (26%) |
| ITUB4 | M5 | 5 | -8.87 | 57/198 (29%) |
| PETR4 | M15 | 5 | -7.43 | 64/200 (32%) |
| PETR4 | M30 | 5 | -8.78 | 58/182 (32%) |
| PETR4 | M5 | 20 | -13.13 | 75/197 (38%) |

## Interpretacao

### 1. Padrao uniforme
A edge media oscila entre -3.88 e -13.92 p.p., sem nenhuma combinacao
positiva. A variancia entre ativos e MENOR que a variancia dentro de
um unico fold — indicando que a edge negativa e propriedade da
estrategia/timeframe, nao do ativo.

### 2. Nao e o modelo
Tres familias diferentes (tendencia, reversao, ML) produzem o mesmo
resultado. Se o problema fosse apenas o modelo logistico, MA/RSI
teriam dado edge positivo em alguns ativos.

### 3. Nao e o ativo
Cinco ativos de classes diferentes (indice, dolar, acoes) produzem
o mesmo resultado. Se o problema fosse WINV26 (especifico), PETR4
teria dado edge positivo.

### 4. Nao e o timeframe
M1, M5, M15, M30 produzem o mesmo resultado. Nao ha "timeframe certo".

### 5. Nao e o horizonte
Horizonte 5 e 20 produzem edge negativo. Horizonte 20 e PIOR
(-13.92 vs -6.54 em MA M5). Mais tempo = mais incerteza, nao menos.

### 6. Compatibilidade com eficiencia de mercado
O resultado e consistente com a hipotese de mercado fracamente
eficiente: preco passado nao prediz preco futuro de forma exploravel
por indicadores tecnicos puros em horizontes curtos.

## Decisao

**Aceitar o achado.** Nao ha edge comprovado em nenhuma das combinacoes
testadas. Nao vamos continuar testando variacoes da mesma hipotese
(mais ativos, mais timeframes, mais parametros) — isso seria fishing
e geraria falsos positivos.

Proximo passo e piv otar de abordagem (ver "Proximos caminhos").

## Consequencias

- FASE 14 (ML) nao pode ser concluida com esta abordagem
- FASE 20 (Live) permanece bloqueada
- Infraestrutura esta completa e correta (registry, walk-forward,
  features, pipeline)
- 234 passed, 4 skipped
- ADR-019 confirma empiricamente o resultado do ADR-014

## Proximos caminhos (ordenados por viabilidade)

### Caminho A — Volatility trading (nao-direcional)
Volatilidade TEM memoria (clustering). Prever "vai ter movimento
grande" e mais facil que prever direcao. Features: GARCH-like, ATR
historico, regime de volatilidade. Estrategia: breakout em expansao
de volatilidade, ou straddle/strangle.

### Caminho B — Deteccao de regime como filtro
Nao tenta prever direcao, mas contexto (trending/ranging/volatile).
Usado como filtro para estrategias existentes. Se MA funciona so em
trending, aplicar MA so quando regime = trending.

### Caminho C — Microestrutura / order flow
Precisa de dados de book/tick-by-tick. MT5 nao fornece diretamente.
Requer fonte de dados alternativa (Profit, Bloomberg, MetaTrader
tick data).

### Caminho D — Modelos nao-lineares mais expressivos
Random Forest, XGBoost, redes neurais. Baixa probabilidade de flip
significativo baseado em evidencia previa, mas vale uma rodada rapida.

### Caminho E — Aceitar o achado e construir infraestrutura 24/7
Sem edge, mas com operacao 24/7 em paper trading com estrategias
existentes. Objetivo: provar a infraestrutura operacional enquanto
pesquisa de edge continua em paralelo.

### Caminho F — Pivotar modelo de negocio
Em vez de previsao de direcao, focar em:
- Execucao otima (TWAP/VWAP)
- Arbitragem estatistica (pairs trading)
- Market making
Estes sao problemas diferentes, com bibliografia mais rica.

## Recomendacao

**Caminho E (infraestrutura) em paralelo com Caminho A (volatilidade).**

E: infraestrutura 24/7 e util independentemente de edge.
A: volatilidade e a unica familia de previsao com evidencia forte
   em literatura academica.

## Alternativas descartadas

- **Continuar testando variacoes da mesma hipotese**: rejeitada por
  violar rigor cientifico (fishing). O resultado ja e claro.
- **Forcar parametros ate dar positivo em algum fold**: rejeitada por
  ser overfitting puro.
- **Declarar o sistema "quebrado"**: rejeitada. O sistema esta correto;
  a ausencia de edge e uma descoberta, nao um bug.

## Licao

A plataforma faz o que deveria fazer: coleta dados, calcula features,
treina, valida em walk-forward, versiona, mede. E chegou a uma
conclusao honesta: **nao ha edge nas abordagens testadas**.

Isso e um resultado valido e util. Muitos projetos de trading
fracassam por nao aceitar esse tipo de evidencia. Aqui, o framework
explicitamente pediu honestidade (secao 73) e a evidencia foi coletada.

Referencias cruzadas: ADR-003, ADR-012, ADR-013, ADR-014, ADR-019.