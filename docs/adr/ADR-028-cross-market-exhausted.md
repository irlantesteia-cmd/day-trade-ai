# ADR-028 - Cross-market esgotado; estado do projeto

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

Apos ADR-020 (direcional), ADR-023/025 (volatilidade), ADR-026
(pairs B3) e ADR-027 (calendar spreads), o milestone 24 testou
cross-market como ultima familia com fundamento economico.

## Experimentos

### Cross-market internacional
- MGLUS100 (Nasdaq 100): 0 barras — broker nao fornece dados
- MGLUS305 (Dow): 0 barras
- WEGER400 (DAX): ~25 barras — iliquido
- GOAUK100 (FTSE): ~40 barras — iliquido

**Broker XP nao fornece CFDs internacionais com liquidez suficiente.**

### Cross-market interno
| Par | TF | Obs | Cointegrados |
|---|---|---|---|
| INDV26/DOL$ | M15 | 1320 | 0 |
| WINV26/WDOF27 | M15 | 170 | 0 |

Correlacao macro conhecida (dolar vs indice) nao se traduz em
cointegracao exploravel no intraday.

## Estado consolidado das 6 familias

| # | Familia | Status | ADR |
|---|---|---|---|
| 1 | Direcional (ML, MA, RSI) | Sem edge | ADR-020 |
| 2 | Volatilidade previsao | Edge so WIN | ADR-023 |
| 3 | Volatilidade conversao | Marginal/concentrado | ADR-025 |
| 4 | Pairs trading (B3) | Sem edge | ADR-026 |
| 5 | Calendar spreads | Sem edge | ADR-027 |
| 6 | Cross-market | Sem edge / indisponivel | ADR-028 |

**6 familias testadas. 1 com sinal real (volatilidade WIN). 0 operaveis.**

## Interpretacao honesta

### 1. A plataforma esta completa
Infraestrutura equivalente a de uma mesa quant profissional:
- Data pipeline, quality, persistencia
- Indicators, features, strategies
- Walk-forward, Monte Carlo, sensitivity
- Risk engine, kill switch, position sizing
- Broker abstraction, EventBus
- API HTTP, dashboard, daemon 24/7
- Docker, Postgres, Alembic, CI

### 2. O mercado nao oferece edge
Com dados OHLCV apenas, indicadores tecnicos puros, modelos
estatisticos simples e cointegracao entre ativos disponiveis no
broker XP, **nao ha edge exploravel** em nenhuma das 6 familias
testadas (exceto volatilidade WIN marginal).

### 3. Isso nao e fracasso
E o resultado cientifico de uma investigacao rigorosa:
- ~150 experimentos
- 28 ADRs documentando cada decisao
- 310 testes automatizados
- Walk-forward como padrao
- Multi-ativo como defesa contra overfitting

A maioria dos projetos quant morre por falta de edge, nao por falta
de codigo. Este projeto tem codigo e rigor; falta o mercado.

## Proximos caminhos (nao testados)

### A. Dados alternativos (microestrutura)
Book de ofertas, order flow, tick data. **Requer fonte paga**
(Profit, Nelogica, Bloomberg). Broker XP nao fornece.

### B. Modelos de volatilidade dedicados (GARCH/HAR-RV)
Usa `arch` ou implementacao propria. **Poderia capturar mais sinal
de volatilidade** que os modelos lineares testados.

### C. Multi-asset portfolio com sinais marginais
Combinar sinais neutros/marginais em alocacao. Depende de ter N
sinais independentes (nao temos).

### D. Pivotar para pesquisa academica
Documentar a investigacao como paper tecnico. A rigorosidade
metodologica tem valor.

### E. Aceitar e parar
Reconhecer que a B3 no periodo testado nao oferece edge com as
tecnicas disponiveis.

## Decisao

**Nenhuma acao imediata.** O ADR documenta estado. As proximas
familias (A-D) requerem:
- Dados pagos (A)
- Biblioteca especializada (B)
- Multiplos sinais independentes (C)
- Decisao editorial (D)
- Aceitacao (E)

Qualquer uma delas e uma decisao estrategica, nao tecnica.

## Consequencias

- Cross-market esgotado ✅
- 6 familias testadas, 28 ADRs
- 310 testes passando
- Projeto em estado honesto e documentado

## Licao final

**Rigor cientifico aplicado consistentemente leva a verdade, nao a
lucro.** A verdade deste projeto: a plataforma esta pronta, o
mercado nao oferece edge exploravel com as tecnicas e dados
disponiveis.

Isso e um resultado valido. Muitos projetos quant mentem para si
mesmos e continuam procurando. Aqui, a evidencia foi acumulada
honestamente.

Referencias cruzadas: todos os ADRs (000-027).