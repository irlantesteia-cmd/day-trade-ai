# ADR-032 - Funding rate arbitrage: primeiro edge estrutural

- **Status**: Aceito
- **Data**: 2026-09-25

## Contexto

Apos 9 familias testadas e nenhum edge (ADRs 020, 022, 025, 026, 028,
029, 030, 031), o milestone 28 testou funding rate arbitrage em
perpetuos Binance.

Diferente das estrategias anteriores:
- **Nao tenta prever preco**
- **Nao tenta prever volatilidade**
- **Nao tenta prever cointegracao**
- **Coleta um pagamento mecanico do protocolo**

Mecanismo:
- Perpetuos tem funding a cada 8h
- Quando positivo: longs pagam shorts
- Estrategia: SHORT perp + LONG spot (delta-neutro) coleta funding
- Estrategia institucional chamada "cash-and-carry"

## Implementacao

### `src/adapters/binance_futures_adapter.py`
- `BinanceFuturesAdapter`
- `get_current_funding(symbol)` — mark, index, lastFundingRate
- `get_funding_history(symbol, limit, start, end)` — historico
- `funding_stats(symbol, lookback_days)` — media, mediana, p05/p95,
  % positivo, anualizado, hint de estrategia
- `list_perpetual_symbols()` — contratos PERPETUAL ativos USDT

### Scripts
- `scripts/analyze_funding.py`: analise de 15 simbolos em 30d
- `scripts/funding_long_history.py`: consistencia em 30/90/180/365d
- `scripts/backtest_funding_arb.py`: simulacao cash-and-carry com custos

## Resultados

### Funding atual (30d, 15 simbolos)

Top 5 maiores (candidatos cash-and-carry):
| Symbol | Anualizado | % pos |
|---|---|---|
| MATICUSDT | +10.95% | 100% | (suspeito - ver abaixo)
| DOGEUSDT | +7.24% | 96% |
| LTCUSDT | +7.22% | 96% |
| BTCUSDT | +6.62% | 99% |
| LINKUSDT | +6.08% | 88% |

Bottom (reverse):
| TRXUSDT | -16.56% | 30% |

### Consistencia (30d vs 365d)

BTCUSDT:
- 30d: +6.62%, 98.9% positivo
- 90d: +6.67%, 99.3% positivo
- 180d: +3.74%, 79.4% positivo
- 365d: +3.07%, 74.6% positivo

Funding e estruturalmente positivo mas varia por regime:
- Regime atual (30-90d): ~6.6% anualizado
- Ultimo ano: ~3% anualizado

### Backtest cash-and-carry (180d, com custos)

Roundtrip cost: 0.16% (spot taker + futures taker, 2 pernas)

| Symbol | PnL % | Anual % | Max DD % | % neg |
|---|---|---|---|---|
| BTCUSDT | +1.48% | +3.03% | 0.44% | 19.4% |
| ETHUSDT | +1.02% | +2.08% | 0.34% | 23.4% |
| LINKUSDT | +2.12% | +4.34% | 0.18% | 15.8% |
| DOGEUSDT | +1.86% | +3.81% | 0.19% | 21.6% |
| LTCUSDT | +1.35% | +2.75% | 0.19% | 27.2% |

**5/5 positivos.** Drawdowns < 0.5%.

## Interpretacao

### 1. Primeiro edge genuinamente estrutural
Diferente de todos os 9 experimentos anteriores, este nao depende de
previsao. A fonte de retorno e um pagamento mecanico do protocolo
de perpetuos.

### 2. Magnitude modesta mas real
Retorno anualizado 2-4% com DD < 0.5%. Sharpe estimado > 5. Nao e
"vira dinheiro", mas e consistente e escalavel.

### 3. Baixa correlacao com outras estrategias
Funding arb e neutro em direcao, volatilidade e correlacao. Portfolio
diversification real.

### 4. Varia por regime
Regime atual (30-90d) da ~6% no BTC. Ultimo ano: ~3%. Isso e esperado:
quando mercado esta em bull, funding fica mais positivo.

## Caveats criticos

### 1. MATICUSDT (ignorar)
Mesmo +10.95% em todas as janelas e suspeito. MATIC foi renomeado
para POL em 2024. Endpoint pode retornar dados obsoletos. **Nao usar.**

### 2. Capital efetivo
Modelamos o capital todo no notional da posicao. Na pratica:
- Precisa comprar spot (50% do capital)
- Precisa depositar margem no perp (50% do capital)
- ROI sobre capital TOTAL seria ~50% do modelado

Ajuste: retornos reais ~1-2% ao ano, nao 3-4%.

### 3. Risco de liquidacao
O short no perp pode ser liquidado se preco subir muito sem
rebalanceamento. Precisa de:
- Margem com folga (ex: 50% do capital)
- Rebalanceamento periodico se preco se mover
- Ou usar margem cross em vez de isolada

### 4. Risco de exchange
Binance pode:
- Congelar saques (caso historico: 2023)
- Alterar taxas de funding
- Suspender contratos
Isso e risco nao-modelado.

### 5. Risco de regime
365d de dados. Se funding virar persistentemente negativo por
6+ meses, a estrategia perde dinheiro.

### 6. Custo de oportunidade do capital
Capital alocado em funding arb nao esta em outras estrategias.
Em bull market, o "custo de oportunidade" e enorme.

## Decisao

**Implementar em paper trading.** Razao:
- Primeiro edge real do projeto
- Pode ser validado em tempo real sem risco
- Custo de implementacao e baixo (o adapter ja existe)

**Nao operar com capital real ainda.** Razao:
- Precisa validar taxas reais (nao so as do perfil default)
- Precisa validar execution de 2 pernas em tempo real
- Precisa gerenciar margem e rebalanceamento

## Consequencias

- Primeiro ADR com edge positivo e consistente ✅
- Infraestrutura Binance Futures adicionada ✅
- `BinanceFuturesAdapter` reutilizavel ✅
- 3 scripts de analise ✅
- 318 passed, 4 skipped
- +1 adapter, +3 scripts

## Proximos passos

1. **Paper trading de funding arb**: daemon que registra funding
   coletado sem dinheiro real (1-2 semanas)
2. **Comparar** o funding coletado vs funding esperado
3. **Decidir** se vai para capital real (pequeno primeiro)

Referencias cruzadas: todos os ADRs (000-031).