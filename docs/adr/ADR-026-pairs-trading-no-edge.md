# ADR-026 - Pairs trading nao encontrou edge em acoes B3

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

Apos os achados do ADR-020 (sem edge direcional) e ADR-025 (edge de
volatilidade marginal nao operavel), o milestone 22 testou a hipotese
de **cointegracao em pares** como fonte alternativa de edge
market-neutral.

Motivacao:
- Literatura academica documenta pairs trading como estrategia
  market-neutral robusta
- Acoes brasileiras (ITUB4/BBDC4, PETR3/PETR4, etc.) sao candidatas
  naturais por compartilharem setor/empresa
- Spread de par nao depende de direcao do mercado

## Implementacao

### Modulo `src/portfolio/cointegration.py`
- `CointegrationTester`: teste de Engle-Granger (OLS + ADF nos residuos)
- `_estimate_half_life`: AR(1) sobre residuos, com cap pratico em 1000 barras
- `build_spread`, `zscore`: construcao de serie de spread normalizada
- `screen_pairs`: wrapper que testa todos os pares em um dict, pre-filtrando
  por correlacao de log-returns para eficiencia

### Script `scripts/screen_pairs.py`
- Busca candles de N simbolos no MT5
- Alinha por timestamps comuns (cointegracao exige alinhamento)
- Roda screen_pairs e reporta pares cointegrados ordenados por p-value
- Salva JSON em `models/benchmarks/pairs_screen_*.json`

### Cobertura de testes
`tests/test_cointegration.py`: 18 testes
- Validacao de parametros
- Deteccao de cointegracao em series sinteticas
- Rejeicao de random walks independentes
- Half-life (nao pode ser absurdo)
- Serializacao
- Construcao de spread, z-score
- screen_pairs (deteccao, nao-falsos-positivos, ordenacao)

## Experimentos

| Conjunto | Timeframe | N pares testados | Cointegrados |
|---|---|---|---|
| 8 blue chips | M15 | 21 | 1 (ITUB4/BBDC4, p=0.046) |
| ITUB4/BBDC4 | M5 | 1 | 0 |
| ITUB4/BBDC4 | M30 | 1 | 0 |
| ITUB4/BBDC4 | H1 | 1 | 0 |
| WINV26/INDV26 | M15 | 1 | 1 (hedge=1.0 exato, NAO tradeable) |
| PETR3/PETR4/ITUB3/ITUB4 | M15 | 6 | 0 |
| Blue chips (min_corr=0.5) | M15 | 10 | 0 |
| Blue chips D1 | D1 | 10 | 0 |

## Interpretacao

### 1. O unico "achado" e falso positivo por multiple testing
- 21 pares testados em M15 com threshold p < 0.05
- Esperado por puro acaso: ~1 falso positivo
- ITUB4/BBDC4 em M15: p = 0.046 (raspando o threshold)
- NAO confirma em M5, M30, H1 -> falso positivo

### 2. WIN/IND nao e pairs trading
- hedge_ratio = 1.0000 exato (mesmo indice em escalas diferentes)
- half_life = None (sem reversao)
- Spread = tracking error puro, nao tradeable

### 3. ON/PN (PETR3/PETR4, ITUB3/ITUB4) nao cointegram intraday
- Surpreendente dado que sao a mesma empresa
- Provavel razao: microestrutura (diferentes liquidities, spread,
  horarios de leilao) contamina intraday

### 4. D1 tambem nao cointegra nas 5 blue chips testadas
- 1248 observacoes alinhadas (5 anos)
- Nenhum par passa em p < 0.05

## Decisao

**Pairs trading nao funciona em acoes B3 no periodo testado.**
Nao operar.

**Nao tentar "consertar"** ajustando janela, threshold ou simbolos
seria fishing. Os testes foram abrangentes o suficiente.

## Consequencias

- Modulo de cointegracao implementado e testado ✅
- Script de screener reutilizavel ✅
- Achado honesto: nenhum par tradeable nas B3 ✅
- 310 passed, 4 skipped (eram 292; +18)
- +1 modulo em `src/portfolio/`
- +1 script, +1 arquivo de testes

## Nao coberto (backlog)

- **Pairs em futuros diferentes vencimentos** (calendar spread):
  WINV26 vs WINZ26, WDOU26 vs WDOX26. Nao testado.
- **Universo maior de acoes**: existem ~100 acoes liquidas na B3,
  testamos 8. Mas cointegracao requer liquidez; se blue chips nao
  mostram, small caps provavelmente tambem nao.
- **Cointegracao em BOVA11 vs composicao**: ETF vs cesta de acoes
- **Modelos multivariados** (Johansen test): encontra multiplas
  relacoes cointegradas simultaneamente. Substituir Engle-Granger
  (par-a-par) por Johansen (N-a-N) poderia encontrar estruturas
  maiores.

## Licao

**Cointegracao nao e universal.** Pairs trading funciona em
mercados com baixa eficiencia e alta friccao; B3 moderna (2026)
com HFT e liquidez alta e eficiente intraday. A tecnica esta
correta, o mercado e que nao oferece a oportunidade.

Referencias cruzadas: ADR-020 (sem direcional), ADR-023/025
(volatilidade marginal), ADR-026 (pairs sem edge).