# ADR-023 - Investigacao profunda do sinal de volatilidade

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

O ADR-022 (M18) testou previsao de volatilidade em 4 ativos/timeframes.
Apenas WINV26 M5 atingiu o criterio ADR-003 (edge +4.87 p.p., 71% folds).
Os outros 3 ficaram neutros ou negativos.

Hipotese A: o +4.87 e variacao estatistica (falso positivo por selecao).
Hipotese B: o +4.87 e edge real, especifico do WIN.

Milestone 19 testou Hipotese A/B com 3 experimentos adicionais:
  1. WINZ26 M5 (vencimento diferente, mesmo instrumento)
  2. WINV26 M5 H=3 (horizonte mais curto)
  3. WINV26 M5 H=10 (horizonte mais longo)

## Resultados

### Experimento 1: WINZ26 M5 (H=5)
Amostras: 4441 | Threshold: 0.139%
Edge medio: +3.31 p.p. | Folds positivos: 22/39 (56%)

**Interpretacao:** confirma parcialmente. Mesmo instrumento,
vencimento diferente, edge na mesma direcao. Valor menor (3.31 vs
4.87), possivelmente porque WINZ26 tem menos liquidez/historico.

### Experimento 2: WINV26 M5 H=3 (horizonte curto)
Amostras: 8473 | Threshold: 0.082%
Edge medio: +5.73 p.p. | Folds positivos: 61/79 (77%)

**Interpretacao:** confirma e MELHORA. Horizonte mais curto
amplifica o sinal. Coerente com volatility clustering: quanto mais
proximo do evento, maior a memoria.

### Experimento 3: WINV26 M5 H=10 (horizonte longo)
Amostras: 8467 | Threshold: 0.167%
Edge medio: +0.85 p.p. | Folds positivos: 40/79 (51%)

**Interpretacao:** o sinal DECAI para quase neutro em H=10.
Confirma que a memoria de volatilidade no WIN tem janela curta
(3-5 candles M5 = 15-25 min).

## Sintese

| Teste                  | Edge medio | Folds +      | Conclusao |
|------------------------|------------|--------------|-----------|
| WINV26 M5 H=5 (base)   | +4.87      | 56/79 (71%)  | positivo  |
| WINZ26 M5 H=5          | +3.31      | 22/39 (56%)  | positivo  |
| WINV26 M5 H=3          | **+5.73**  | **61/79 (77%)** | positivo |
| WINV26 M5 H=10         | +0.85      | 40/79 (51%)  | neutro    |
| PETR4 M5 H=5 (M18)     | -1.91      | 66/194 (34%) | negativo  |
| WDOX26 M5 H=5 (M18)    | +0.94      | 10/17 (59%)  | neutro    |

## Conclusao

**Hipotese B confirmada parcialmente.**

O sinal de volatilidade e REAL para o WIN (mini-indice), com as
seguintes caracteristicas:

1. **Especifico do WIN**: nao generaliza para PETR4 nem WDOX26
2. **Especifico de horizonte curto**: H=3..5 tem sinal, H=10 decai
3. **Consistente entre vencimentos**: WINV26 e WINZ26 concordam
4. **Edge modesto**: +3 a +6 p.p. sobre baseline

Isso NAO e um edge forte. Mas tambem NAO e ruido puro. E um sinal
exploravel para trading de volatilidade **apenas se os custos
operacionais forem menores que o edge**.

## Ressalvas criticas

### 1. Custos operacionais nao considerados
O benchmark atual mede apenas edge preditivo, nao edge liquido.
Spread tipico do WIN M5: ~0.05%-0.10% por operacao. Corretagem: ~R$1
por contrato. Se 50% dos folds sao positivos com edge +5 p.p., o
lucro liquido depende da taxa de acerto por trade individual, nao
por fold.

### 2. Oportunidades escassas
O modelo preve "movimento grande vs pequeno". Uma estrategia de
volatilidade correspondente (ex: breakout) pode gerar poucas
oportunidades por dia. O edge total pode nao compensar o esforco.

### 3. Sem teste de robustez a spread
O benchmark assume preco de mercado puro. Com spread, o label
"movimento grande" muda. Testes com bid/ask real seriam necessarios.

### 4. Sem teste em regimes diferentes
O periodo testado (2026) e especifico. Nao testamos 2023, 2024,
ou outros regimes de mercado.

## Decisao

**Nao operar com base neste sinal ainda.** As razoes:

1. Edge modesto (+3-5 p.p.) provavelmente e absorvido por custos
2. Nao ha estrategia de execucao implementada (breakout, straddle)
3. Nao ha teste de bid/ask real
4. Falta teste em regimes historicos diferentes

**Registrar como "descoberta parcial"** e documentar caminhos
futuros para quem quiser investigar mais.

## Caminhos futuros (nao implementados)

- **Modelo GARCH/HAR-RV** dedicado (em vez de logístico + features)
- **Estrategia de breakout baseada em expansao de volatilidade**
- **Testes com bid/ask real** (spread modelado)
- **Testes em multiplos regimes** (2023, 2024, 2025)
- **Backtest do sinal convertido em PnL** (com custos)

## Consequencias

- Descoberta documentada honestamente ✅
- Infraestrutura de features de volatilidade validada ✅
- 280 passed, 4 skipped (nao mudou; sem novos testes formais) ✅
- ADR-020 (direcao sem edge) permanece
- ADR-022 (volatilidade generica) refinado por este ADR

## Licao

**Investigar o unico sinal positivo vale a pena.** O ADR-022 sozinho
teria deixado "1/4 confirmou, provavel ruido". Mas a investigacao
mostrou que o sinal e real *para um instrumento especifico*. Sem essa
investigacao, teriamos jogado fora uma pista legitima.

Referencias cruzadas: ADR-003, ADR-020, ADR-022.