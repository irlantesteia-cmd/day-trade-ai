# ADR-030 - ETFs nao tem edge; 8 familias testadas

- **Status**: Aceito
- **Data**: 2026-09-25

## Contexto

Apos ADR-028 (cross-market) e ADR-029 (regime filter), o milestone 26
testou ETFs como ultimo reduto de ativos no broker XP/B3.

ETFs testados:
- GOLD11 (ouro)
- BOVA11 (Ibovespa)
- ETHA39 (Ethereum)

## Resultados

| ETF | Estrategia | Folds | Edge medio | Folds + |
|---|---|---|---|---|
| GOLD11 | MA_CROSSOVER | 50 | -8.33 | 4/50 |
| GOLD11 | RSI_REVERSION | 50 | -12.08 | 13/50 |
| BOVA11 | MA_CROSSOVER | 50 | -8.98 | 7/50 |
| BOVA11 | RSI_REVERSION | 50 | -8.78 | 14/50 |
| ETHA39 | MA_CROSSOVER | 50 | -7.21 | 11/50 |
| ETHA39 | RSI_REVERSION | 50 | -9.98 | 13/50 |

Todos negativos. Consistente com todos os ativos anteriores.

## Balanco consolidado

### 8 familias testadas

| # | Familia | Ativos | Timeframes | Resultado |
|---|---|---|---|---|
| 1 | Direcional (ML, MA, RSI) | 6+ | M1-M30, H1, D1 | Sem edge |
| 2 | Volatilidade preditiva | 4 ativos | M5-M15 | Edge so WIN M5 H=3 |
| 3 | Volatilidade conversao | WINV26 | M5 | Marginal/concentrado |
| 4 | Pairs trading B3 | 8 acoes | M5-D1 | 0 pares tradeable |
| 5 | Calendar spreads | WIN, WDO | M15-M30 | half-life < 1 |
| 6 | Cross-market | B3 + CFDs | M15 | 0 ou indisponivel |
| 7 | Regime filter | WINV26 | M5 | 2/5 folds honesto |
| 8 | ETFs | 3 ETFs | M15 | Sem edge |

### Universo testado

- **Acoes**: PETR3, PETR4, VALE3, ITUB3, ITUB4, BBDC4, BBAS3,
  ABEV3, B3SA3 (9)
- **Futuros**: WIN, WDO, IND (multi-vcto)
- **ETFs**: BOVA11, GOLD11, ETHA39 (3)
- **Cross-market**: US100, US30, GER40, UK100 (iliquidos)

**Total**: ~20 ativos, 8 familias de estrategia, centenas de
combinacoes testadas.

## Interpretacao

### 1. A plataforma esta completa
Toda a infraestrutura de uma mesa quant profissional:
- Data pipeline, quality, persistencia
- Indicators, features (4 familias), strategies (4)
- Walk-forward, Monte Carlo, sensitivity, cointegracao
- Risk engine, kill switch, position sizing, broker abstraction
- EventBus, API HTTP, dashboard, daemon 24/7
- Docker, Postgres, Alembic, CI

### 2. O universo disponivel nao oferece edge
Com dados OHLCV apenas, indicadores tecnicos puros, modelos
estatisticos simples, cointegracao entre ativos disponiveis,
e filtros de regime, **nao ha edge exploravel** em nenhuma das
8 familias testadas.

Exceto: volatilidade preditiva do WIN M5 H=3..5 (edge +4-6 p.p.),
mas a conversao em PnL e marginal (ADR-025).

### 3. Por que (provavel)
- B3 moderna (2026) e eficiente intraday
- HFT e market makers absorvem oportunidades rapidamente
- Broker XP nao oferece acesso a mercados alternativos (forex,
  cripto spot, commodities)
- Dados OHLCV sao publicos e amplamente explorados

## Decisao

**Nao operar.** Nenhuma estrategia tem edge robusto e replicavel.

**Nao tentar mais variacoes** de:
- Parametros (lookback, threshold)
- Timeframes (todos testados)
- Simbolos (universo esgotado no broker)
- Modelos simples (todos testados)

Seria fishing. A evidencia e clara.

## Caminhos restantes (nao sao mais "milestones")

### A. Dados alternativos
- **Microestrutura**: book, order flow, tick data
- **Dados pagos**: Profit Pro, Bloomberg, Refinitiv
- **Custo**: R$ 500-2000/mes
- **Probabilidade de edge**: media (dados privados tem valor)

### B. Modelos especializados
- **GARCH/HAR-RV dedicado**: para o sinal de volatilidade
- **Random Forest / XGBoost**: para direcao com features melhores
- **Custo**: tempo de implementacao + tuning
- **Probabilidade**: baixa-media (features simples ja falharam)

### C. Execution overlay
- **Position sizing dinâmico** com previsao de volatilidade
- **VWAP/TWAP** com limit orders
- **Reducao de custos** operacionais
- **Custo**: medio
- **Probabilidade**: media (ataca gargalo conhecido)

### D. Pesquisa academica
- Documentar investigacao como paper tecnico
- Rigor metodologico tem valor
- **Custo**: tempo de escrita
- **Probabilidade**: N/A (nao e objetivo financeiro)

### E. Novo broker/mercado
- Abrir conta em broker que oferece forex/cripto spot
- Acesso a mercados menos eficientes
- **Custo**: setup + capital
- **Probabilidade**: media-alta

## Licao final

**A plataforma esta pronta. O mercado disponivel nao tem edge.**

Isso e um resultado valido e honesto. Muitos projetos quant
fracassam por nao aceitar esse tipo de evidencia e continuar
iterando infinitamente.

A investigacao cobriu 8 familias, ~20 ativos, ~30 ADRs, ~150
experimentos. Cada um foi conduzido com rigor (walk-forward,
multi-ativo, sem look-ahead). Nenhum passou.

Referencias cruzadas: todos os ADRs (000-029).