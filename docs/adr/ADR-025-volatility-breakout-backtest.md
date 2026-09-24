# ADR-025 - Backtest da VolatilityBreakoutStrategy

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

O ADR-023 documentou um sinal de volatilidade real para o WIN em
horizonte curto (H=3..5), com edge preditivo modesto (+3 a +6 p.p.).

O milestone 21 tentou converter esse sinal em uma estrategia
executavel (VolatilityBreakoutStrategy) e medir PnL liquido com
custos (spread + comissao).

## Implementacao

### VolatilityBreakoutStrategy

Regra:
  - Pre-requisito: volatilidade expandindo
    (range_atual / range_medio_20 >= vol_threshold)
  - Direcao via breakout:
    - close > max(high) dos 20 candles anteriores -> BUY
    - close < min(low) dos 20 candles anteriores -> SELL
    - Caso contrario -> NEUTRAL
  - Metadata inclui `atr` para o RiskEngine calcular SL/TP

### Backtest

- Sem look-ahead (indicadores e features com janela candles[:i+1])
- Custos: spread 5 pontos + comissao R$1/contrato
- Multiplicador WIN: R$0.20/ponto
- 1 contrato, 1 posicao por vez
- SL/TP opcional via ATR (3x SL / 6x TP)
- Saidas: SL, TP, sinal oposto, max_hold

### Walk-forward

5 e 10 janelas consecutivas independentes (cada uma com capital
inicial proprio). Mede consistencia no tempo.

## Resultados

### Sintetico (GARCH-like + momentum)

+94.05% | 256 trades | PF 1.49 | Sharpe 8.66
**Nao e evidencia** — o gerador sintetico foi construido com
volatility clustering + momentum AR(1), favorecendo a estrategia.

### MT5 WINV26 M5 - full window (8508 candles)
| Config | PnL | Trades | Win% | PF | DD | Sharpe |
|---|---|---|---|---|---|---|
| Sem SL/TP | +7.52% | 285 | 48.07% | 1.08 | 16.80% | 1.42 |
| SL=1.5x TP=3x | -7.70% | 353 | 37.39% | 0.97 | 15.71% | -1.07 |
| **SL=3x TP=6x** | **+12.39%** | 305 | 45.25% | 1.12 | 12.09% | 2.15 |

SL/TP largo (3x/6x) melhora todas as metricas. SL apertado
(1.5x/3x) piora (stops prematuros).

### MT5 WINV26 M5 - walk-forward 5 janelas
| Fold | PnL% | PF | Sharpe |
|---|---|---|---|
| 0 | +10.29% | 1.42 | 6.89 |
| 1 | -3.31% | 0.86 | -3.81 |
| 2 | +2.00% | 1.14 | 2.06 |
| 3 | +3.47% | 1.18 | 2.67 |
| 4 | -0.88% | 0.98 | 0.40 |
| **media** | **+2.31%** | - | - |

3/5 folds positivos. Fold 0 concentra quase todo o lucro.

### MT5 WINV26 M5 - walk-forward 10 janelas
| Fold | PnL% | PF | Sharpe |
|---|---|---|---|
| 0 | +13.79% | 2.17 | 14.31 |
| 1 | -2.46% | 0.84 | -4.13 |
| 2 | +3.80% | 1.46 | 5.95 |
| 3 | -6.39% | 0.39 | -17.91 |
| 4 | +0.82% | 1.13 | 1.73 |
| 5 | -0.51% | 0.97 | -0.76 |
| 6 | +0.24% | 1.04 | 0.65 |
| 7 | +2.28% | 1.24 | 3.06 |
| 8 | -1.01% | 0.93 | -1.25 |
| 9 | +0.95% | 1.12 | 2.40 |
| **media** | **+1.15%** | - | - |

6/10 folds positivos. Fold 0 sozinho = +13.79%. Folds 1-9 somados
= -2.28%. Media dos 9 folds SEM fold 0 = -0.25%.

### Sensibilidade a vol_threshold (full window)
| vol_thr | PnL | Trades | PF | Sharpe |
|---|---|---|---|---|
| 1.2 | +15.37% | 324 | 1.14 | 2.44 |
| 1.3 | +12.39% | 305 | 1.12 | 2.15 |
| 1.5 | +13.38% | 255 | 1.15 | 2.42 |
| 2.0 | +13.98% | 156 | 1.24 | 2.98 |

Todos positivos numa faixa estreita. Nao e overfitting ao parametro.

## Diagnostico honesto

### 1. O edge existe mas e marginal
- Full-window: +12.39% em 8508 candles M5 (aprox 30 dias)
- Walk-forward (media honesta): +1.15% a +2.31%

### 2. Concentracao em 1 fold
- Walk-forward 10: fold 0 sozinho = +13.79%
- Folds 1-9 somados = -2.28% (basicamente neutro)

Sem o fold 0, a estrategia e estatisticamente neutra.

### 3. Problema de conversao
- ADR-023 media edge preditivo de +3 a +6 p.p.
- A conversao em PnL liquido consome a maior parte desse edge:
  - Spread + comissao
  - Estouros de stop
  - Drawdown intra-trade

### 4. Sinal e fragil ao tempo
- Folds individuais variam de -6.39% a +13.79%
- Desvio padrao alto (4.96% nos 10 folds)
- Sharpe dos folds (excluindo outlier): proximo de zero

## Decisao

**Nao operar com essa estrategia.** Razoes:

1. Concentracao em 1 fold indica dependencia de regime especifico
2. Edge medio em walk-forward (1.15% em 30 dias) nao compensa
   complexidade operacional
3. Alto desvio entre folds significa risco alto para retorno baixo
4. Spread real da XP pode ser maior que os 5 pontos modelados
   (invertendo o sinal)
5. Nao ha robustez a regimes historicos diferentes

**Nao tentar "consertar"** ajustando parametros — seria fishing
(mesma logica do ADR-020).

## Consequencias

- VolatilityBreakoutStrategy implementada e testada ✅
- Backtest com custos + SL/TP + walk-forward ✅
- Achado honesto: edge marginal nao operavel ✅
- FASE 14 (ML) permanece PARCIAL
- 292 passed, 4 skipped (eram 280; +12)
- +1 estrategia em `src/strategies/`
- +2 scripts (`backtest_volatility_breakout.py`, `walk_forward_vb.py`)

## Nao coberto (backlog)

- **GARCH / HAR-RV dedicado**: modelo estatistico especializado
  poderia capturar mais do sinal de volatilidade
- **Estrategia nao-direcional** (straddle/strangle): nao aposta em
  direcao, apenas em volatilidade — teoricamente mais alinhada com
  o sinal do ADR-023
- **Microestrutura**: order flow, bid/ask imbalance
- **Pares / cointegracao**: pairs trading com WIN vs IND
- **Multi-ativo portfolio**: mesmo sinal marginal em varios ativos
  pode ter efeito portfolio

## Licao

**Edge preditivo != edge lucrativo.** Um sinal estatisticamente
significante (ADR-023) pode nao sobreviver a custos, execucao,
drawdown e concentracao temporal. A conversao de previsao em PnL e
onde a maioria dos sinais morre.

**Walk-forward com janelas independentes revela concentracao.**
Full-window infla o PnL por compounding e mascara distribuicao
temporal. Sempre usar walk-forward para validar edge real.

Referencias cruzadas: ADR-003, ADR-020, ADR-022, ADR-023.