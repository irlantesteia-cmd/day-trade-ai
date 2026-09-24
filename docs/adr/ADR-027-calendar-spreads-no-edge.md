# ADR-027 - Calendar spreads nao tem edge exploravel

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

O ADR-026 (M22) descartou pairs trading em acoes B3. O milestone 23
testou a hipotese final de cointegracao: **calendar spreads** —
diferenca entre dois vencimentos do MESMO contrato futuro.

Motivacao teorica:
- Ambos os vencimentos seguem o mesmo underlying
- Spread teorico = carry (juros, dividendos, conveniencia)
- Deveria ser estacionario (cointegrado por construcao)
- Estrategia institucional real (term structure trading)

## Experimentos

### WINV26/WINZ26 (mini indice)

| TF  | N obs | hedge | ADF-p | half-life |
|-----|-------|-------|-------|-----------|
| M15 | 1818  | 0.9849| 0.0060| **0.5**   |
| M30 | 1057  | 0.9847| 0.0317| **0.4**   |
| H1  | 649   | -     | n.s.  | -         |
| D1  | 94    | -     | n.s.  | -         |

### WDOV26/WDOX26 (mini dolar)

| TF  | N obs | hedge | ADF-p | half-life |
|-----|-------|-------|-------|-----------|
| M15 | 1006  | 0.9920| 0.000002 | **0.2** |

### Outros

- INDV26/INDZ26: INDZ26 ilíquido (3-4 barras), não testável
- WDOU26: não existe no broker (correto: WDOV26, WDOX26, WDOZ26)

## Interpretacao

### 1. Cointegracao trivial

Os pares de calendar spread sao "cointegrados" no sentido estatistico
(ADF p < 0.05). MAS:

- hedge_ratio ~0.985-0.992 (proximo de 1.0)
- half_life 0.2-0.5 barras (reversao DENTRO de 1 candle)

Nao ha tempo fisico para entrar e sair. O "spread" e essencialmente
ruido bid-ask entre dois contratos que rastreiam o mesmo preco base.

### 2. Por que acontece

Para futuros do mesmo underlying:
  - Ambos os precos = F(S, t) com mesmo S (spot) e t diferentes
  - O basis teorico e determinado por juros/carry
  - No curto prazo (intraday), juros/carry sao CONSTANTES
  - Logo, o spread nao tem dinamica propria — so tracking error

Isso e estrutural, nao um artefato do periodo testado. Nao vai
melhorar com mais dados ou outro timeframe.

### 3. Comparacao com pairs de acoes

Pares de acoes diferentes tem spread com FUNDAMENTO (setor, macro),
portanto alguma dinamica propria. Mas ja mostramos no ADR-026 que
nem isso gera edge nas blue chips.

Calendar spread e ainda mais fraco porque o spread nao tem fundamento
proprio — e puro bid-ask noise.

## Decisao

**Nao operar calendar spreads neste broker.** Nao ha edge exploravel.
Nao tentar "consertar" — e limitacao estrutural da classe de ativo.

## Consequencias

- 5 familias de cointegracao testadas, todas negativas
- FASE 14 (ML) continua parcial
- 310 passed, 4 skipped (não mudou)
- +1 ADR

## Backlog (nao coberto)

- **Calendar spread em mercados com term structure mais rica**:
  commodities fisicas (oil, agricolas) tem basis com contango/backwardation
  dinamico. Mas o broker XP nao oferece esses.
- **Cointegracao multivariada (Johansen)**: poderia encontrar
  combinacoes lineares de 3+ ativos cointegradas. Escopo de pesquisa.

## Licao

**Cointegracao "estatistica" nao implica "operacional".** Um par
pode ter ADF-p < 0.001 e ainda assim ser impossivel de operar
(half-life < 1 barra). A cointegracao util requer:
  - half-life em faixa tradeable (10-100 barras)
  - hedge_ratio != 1 exatamente
  - spread com fundamento economico

Referencias cruzadas: ADR-026 (pairs B3), ADR-020 (direcional).