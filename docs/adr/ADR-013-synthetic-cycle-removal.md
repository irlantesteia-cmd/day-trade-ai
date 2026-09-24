# ADR-013 - Remocao do ciclo senoidal do gerador sintetico

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

O gerador `candles_sinteticos()` (em `scripts/train_model_v3.py`) incluia
um componente senoidal deterministico:

```python
cycle = 0.0005 * np.sin(2 * np.pi * i / 200.0)
ret = 0.3 * prev_ret + cycle + np.random.randn() * 0.0008
Esse ciclo foi originalmente adicionado no M2 com a intencao de "dar ao
modelo algo para aprender". Provou-se uma armadilha.

Evidencia
M2 (basic_v1, com ciclo)
Edge sintetico: -30.64 p.p.

MT5 real: -8.60 p.p.

Conclusao ingenua: "features basic sao ruins"

M8 (technical_v1, com ciclo)
Edge sintetico: +17.29 p.p. (14/14 folds positivos)

MT5 real: -9.40 p.p. (31/194 folds positivos)

Suspeita levantada

Analise de autocorrelacao (M8)
Serie	lag-1	lag-200
Sintetico SEM ciclo	0.29	—
Sintetico COM ciclo	0.49	0.33
O lag-200 autocorr = 0.33 e a assinatura do ciclo de 200 candles. RSI,
SMA e ATR (periodos ~14) detectam facilmente "onde estamos no ciclo",
inflando o edge artificialmente.

M9 (technical_v1, SEM ciclo)
Edge sintetico: -6.39 p.p. (15/44 folds positivos)

Autocorr lag-200: -0.0046 (sem ciclo, confirmado)

Consistente com MT5 real

Decisao
Remover o componente senoidal do candles_sinteticos(). Manter apenas
AR(1) puro com ruido gaussiano:
ret = 0.3 * prev_ret + np.random.randn() * 0.0008
Caracteristicas do novo gerador:

Autocorr lag-1 ≈ 0.29 (inercia AR)

Autocorr lag-200 ≈ 0 (sem componente deterministica)

Volatilidade ~0.0008 (proximo ao WIN$ M1)

Consequencias
Dataset sintetico passa a ser benchmark honesto para o pipeline

Edge +17 p.p. do M8 documentado como artefato em ADR-012 (preservado)

Novos treinos sinteticos refletem realidade (edge proximo de 0 ou negativo)

195 testes continuam passando

Pipeline ML permanece sem edge comprovado (PHASE 14 parcial)

Nao coberto (backlog)
scripts/train_model.py (v2) ainda contem o mesmo ciclo senoidal.
E codigo morto (nao importado por ninguem em src/), mas permanece no
repo. Cleanup em milestone futuro.

models/logistic_v1.pkl (artefato do v2, com ciclo) continua em
models/. src/main.py::_load_strategy() ainda aponta para ele via
MODEL_PATH default. Decisao pendente: deletar ou migrar para
models/registry/logistic_v3_technical__v1/.

Adicionar teste automatico que detecte ciclo deterministico
(autocorr lag-N acima de threshold) em datasets sinteticos futuros.

Alternativas descartadas
Manter o ciclo mas documentar: rejeitada por continuar induzindo a
erro em experimentos futuros.

Adicionar ciclo "mais sutil": rejeitada. Qualquer componente
deterministico no gerador cria artefato detectavel por features
tecnicas.

Deletar candles_sinteticos completamente: rejeitada porque e
util como benchmark rapido (dataset de controle). So precisa ser
honesto.

Licao
Dados sinteticos precisam ser realisticamente ruidosos. Caso
contrario, o modelo overfitta ao artefato do gerador e mascara a
ausencia de sinal real. Testar o pipeline com dados reais (MT5) e
obrigatorio antes de qualquer conclusao sobre edge.

Referencia cruzada: ADR-012 (technical features), secao 73 do framework
("Nunca tratar backtest como garantia de resultado futuro").