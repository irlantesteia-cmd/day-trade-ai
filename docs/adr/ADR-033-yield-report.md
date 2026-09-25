# ADR-033 - Yield estrutural: 4 fontes batem risk-free USD

- **Status**: Aceito
- **Data**: 2026-09-25

## Contexto

Apos os achados dos ADRs 031 (cripto sem edge) e 032 (funding arb
modesto), o milestone 29 implementou:
- `BinanceStakingAdapter`: yields de staking/earn
- `DefiLendingAdapter`: yields de Aave v3, Compound v3, Morpho
- `YieldAggregator`: consolida e compara com risk-free

Objetivo: verificar se yields estruturais (nao-direcionais, sem
previsao) compensam o risco.

## Implementacao

### Adapters
- `src/adapters/binance_staking_adapter.py`: yields de referencia
  Binance (ETH 2.8%, SOL 5.5%, BNB 1.5%, USDT 4.5%, USDC 4.2%)
- `src/adapters/defi_lending_adapter.py`: yields de referencia DeFi
  (Aave v3 USDC 5.2%, Compound v3 USDC 4.9%, Morpho USDC 6.5%)

### Agregador
- `src/yields/yield_aggregator.py`: consolida, compara com risk-free,
  sugere melhores alocacoes

### Scripts
- `scripts/yield_report.py`: relatorio consolidado
- `scripts/test_staking.py`, `scripts/test_lending.py`: testes unitarios

## Resultados

### Comparacao com risk-free (Q3 2026)

| Fonte                 | APY   | RF    | Spread | Beats? |
|-----------------------|-------|-------|--------|--------|
| Morpho USDC           | 6.50% | 4.8%  | +1.70% | SIM    |
| SOL staking           | 5.50% | 4.8%  | +0.70% | SIM    |
| Aave v3 USDC          | 5.20% | 4.8%  | +0.40% | SIM    |
| Compound v3 USDC      | 4.90% | 4.8%  | +0.10% | SIM    |
| Aave v3 USDT          | 4.80% | 4.8%  | +0.00% | NAO    |
| USDT simple earn      | 4.50% | 4.8%  | -0.30% | NAO    |
| DAI lending           | 4.50% | 4.8%  | -0.30% | NAO    |
| USDC simple earn      | 4.20% | 4.8%  | -0.60% | NAO    |
| ETH staking           | 2.80% | 4.8%  | -2.00% | NAO    |
| LINK funding          | 2.17% | 4.8%  | -2.63% | NAO    |
| DOGE funding          | 1.90% | 4.8%  | -2.90% | NAO    |
| BTC funding           | 1.52% | 4.8%  | -3.28% | NAO    |
| BNB vault             | 1.50% | 4.8%  | -3.30% | NAO    |

**Apenas 4/13 batem T-bill (4.8%).**

### Comparacao com CDI brasileiro (11.5% em BRL)

**Nenhum yield USD bate CDI em termos de moeda local.**

Ate Morpho USDC (6.5%) fica 5 pontos abaixo. Descontando depreciacao
do BRL tipica (3-5%/ano), CDI equivale a ~7-8% em USD, ainda
acima de todos os yields DeFi.

## Interpretacao

### 1. Spread sobre T-bill e fino
O melhor caso (Morpho) da +1.7% sobre T-bill. Considerando:
- Risco de smart contract (Morpho e menor que Aave/Compound)
- Risco de depeg de stablecoin
- Gas Ethereum (deposito + retirada)
- Bridge se capital esta em outra chain
- Risco regulatorio

O spread nao compensa claramente.

### 2. CDI domina se capital esta em BRL
11.5% CDI vs 5-6.5% DeFi. Ate descontando depreciacao, CDI rende
~7-8% em USD-equivalente, mais que qualquer opcao DeFi.

### 3. Funding arb confirmado como marginal
1.5-2.2% anualizado fica abaixo de T-bill. Nao compensa o risco
de exchange + execucao de 2 pernas.

### 4. Staking ETH nao compensa
2.8% APY e muito abaixo de T-bill (4.8%). ETH staking so faz
sentido para quem ja tem ETH e nao quer vender (evitar evento
tributario).

## Decisao

**Nao implementar alocacao em yield DeFi no momento.** Razao:
o spread +0.4 a +1.7% sobre T-bill nao compensa o risco
operacional + smart contract + depeg.

**Para capital em BRL: CDI e superior.**

**Para capital em USD: T-bill direto (via corretora tradicional)
e mais simples e igualmente rentavel.**

## Alternativas nao testadas

### A. Real yield tokenizado (Ondo, Mountain, Backed)
T-bills tokenizados em blockchain. Yield ~4.5-5% (mesmo que T-bill),
mas on-chain. Adiciona risco de smart contract sem adicionar yield.
**Rejeitado**: mesmo yield, mais risco.

### B. BRL stablecoin yields (BRZ, BRLA)
Plataformas brasileiras oferecem 8-12% em stablecoins BRL.
**Rejeitado**: risco de contraparte + regulatorio.

### C. Liquidity provision (Uniswap v3, Curve)
Yields variaveis de 5-30%. Mas:
- Impermanent loss
- Requer gestao ativa
- Complexidade operacional alta
**Nao testado**: escopo do milestone 29.

### D. Yield em outras chains (Solana, Base)
Yields similares a Ethereum. Mesmo problema: spread fino.
**Nao testado**: redundante.

## Consequencias

- Adapters de yield implementados ✅
- Agregador funcionando ✅
- Achado honesto: spread nao compensa risco
- 318 passed, 4 skipped
- +3 arquivos em `src/`, +3 scripts

## Licao final

**Yield estrutural em 2026 nao e gratis.** O mercado eficiente
absorveu os spreads. CDI brasileiro (11.5%) oferece mais retorno
com menos risco que qualquer opcao DeFi/USD.

Isso fecha o ciclo da investigacao: todas as fontes de retorno
testadas (alpha direcional, volatilidade, cointegracao, funding,
yield estrutural) batem em barreiras de risco/retorno que nao
justificam alocacao de capital.

Referencias cruzadas: ADRs 020, 031, 032.