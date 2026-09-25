# ADR-031 - Cripto nao tem edge exploravel com as tecnicas testadas

- **Status**: Aceito
- **Data**: 2026-09-25

## Contexto

Apos esgotar o universo B3 (ADR-028) e as 8 familias de estrategia
(ADR-030), o milestone 27 adicionou suporte a Binance via API publica.

Motivacao:
- Cripto e mercado 24/7, sem gaps
- Menos dominado por HFT institucional
- Historicamente documentado como mercado com ineficiencias
- Acesso gratuito via API publica

## Implementacao

### `src/adapters/binance_adapter.py`
- `BinanceDataProvider(MarketDataProvider)`:
  - `fetch_candles(symbol, timeframe, start, end, limit)`
  - `fetch_latest_bars(symbol, timeframe, n)` — conveniencia
  - `fetch_latest_bar(symbol, timeframe)` — compatibilidade MT5Adapter
  - `get_symbol_info(symbol)` — exchange info
- Mapeamento Timeframe -> intervalo Binance: M1->1m, M5->5m, M15->15m,
  H1->1h, D1->1d
- httpx.Client reutilizavel, context manager

### Testes
`tests/test_binance_adapter.py`: 8 testes (mocked httpx)
- Mapeamento de timeframe
- Parser de kline
- fetch_latest_bars, fetch_latest_bar, fetch_candles
- Context manager fecha client

### Scripts
- `scripts/benchmark_crypto.py`: roda MA/RSI em qualquer par Binance
- `scripts/screen_pairs_crypto.py`: cointegracao em N pares cripto
- `scripts/walkforward_cointegration_crypto.py`: split 70/30 para validar

## Experimentos

### Direcional (MA, RSI)
BTCUSDT M5: MA -9.48 (7/50 folds+) | RSI -3.10 (17/49)
Consistente com B3 (ADR-020). Sem edge.

### Cointegracao whole-window (parece promissor)
M15: 7 pares cointegrados (de 45 testados)
D1: 10 pares cointegrados

Sugeria sinal forte. MAS:

### Cointegracao walk-forward (split 70/30)
10/10 pares FALHARAM:
- ADA/LINK: p 0.016 -> 0.964
- SOL/LINK: p 0.028 -> 0.296
- Outros 8 nem cointegravam no treino

## Interpretacao

### 1. Os "7 pares cointegrados" em M15 eram multiple testing
45 testes x p<0.05 => ~2.25 falsos positivos esperados.
Observados: 7 (acima do esperado).
Walk-forward mostrou: 0/10 sobrevivem.

### 2. Hedge ratios absurdos revelam artefato
- ETH/ADA D1: HR = 1329
- BTC/SOL D1: HR = 404
- BTC/ADA D1: HR = 15026

Esses numeros nao tem significado economico. Sao o resultado de
regredir precos correlacionados em escalas muito diferentes. Nao
e cointegracao real, e correlacao espuria.

### 3. Cripto tem a mesma eficiencia que B3 em timeframes intraday
O mercado cripto de 2026 tem HFT institucional suficiente para
arbitrar ineficiencias intraday. As oportunidades que existiam
em 2017-2020 nao existem mais.

### 4. Volume 24/7 nao ajuda
Nao ha gaps, mas isso nao cria edge — apenas remove uma fonte
de risco.

## Balanco de 9 familias testadas

| # | Familia | Universo | Resultado |
|---|---|---|---|
| 1 | Direcional (ML, MA, RSI) | B3 | Sem edge |
| 2 | Volatilidade preditiva | B3 | Edge so WIN M5 H=3 |
| 3 | Volatilidade conversao | B3 | Marginal/concentrado |
| 4 | Pairs trading | B3 | Sem edge |
| 5 | Calendar spreads | B3 futuros | Sem edge |
| 6 | Cross-market | B3 + CFDs | Sem edge / indisponivel |
| 7 | Regime filter | B3 | 2/5 folds honesto |
| 8 | ETFs | B3 ETFs | Sem edge |
| 9 | **Cripto** | **Binance** | **Sem edge** |

## Decisao

**Nao operar com as tecnicas testadas em nenhum dos universos.**
A plataforma esta completa; o edge nao aparece.

**Nao tentar mais variacoes** seria fishing. A evidencia acumulada
em 9 familias, ~30 ativos, 4 timeframes e 2 brokers e clara.

## Consequencias

- Infraestrutura funciona em multiplos brokers (MT5 + Binance) ✅
- `BinanceDataProvider` reutilizavel para futuros experimentos ✅
- Achado honesto: cripto nao e diferente de B3 em timeframes intraday
- 9 familias testadas, todas negativas ou marginais
- 318 passed, 4 skipped (eram 310; +8)
- +1 adapter, +1 test file, +3 scripts

## Nao coberto (backlog)

- **Dados de microestrutura**: order flow, book depth, funding rates
- **Derivativos cripto**: futuros perpetuos, options, funding rate arb
- **DEX / on-chain**: dados on-chain, MEV, arbitragem
- **Pares exóticos**: stablecoin arbitrage, wrapped tokens
- **Tempo**: cripto muda rapido; oportunidades de 2024 podem voltar

## Licao

**Um mercado ser "novo" ou "volatil" nao significa que ele tenha edge.**
Cripto em 2026 e tao eficiente quanto B3 intraday. As oportunidades
existiram em 2017-2020, mas o HFT institucional as absorveu.

Multiplos universos testados (B3, cripto) com metodologia rigorosa
(walk-forward, multi-timeframe) chegam ao mesmo resultado: sem edge
com dados OHLCV e indicadores tecnicos puros.

Referencias cruzadas: ADRs 020, 022, 025, 026, 028, 029, 030.