# Day Trade AI Platform

Plataforma quantitativa modular para análise de mercado, backtesting,
paper trading e execução assistida por Machine Learning.

**Status atual:** FASES 1–13 do roadmap concluídas. FASE 14 (ML) em andamento.
Live trading desabilitado por padrão.

---

## Princípios

- **Separação absoluta de responsabilidades** — dado, análise, estratégia, sinal,
  risco e execução são camadas independentes
- **Preservação de capital antes de maximização de retorno**
- **Sem look-ahead bias** — validado por testes específicos
- **Sem overfitting** — walk-forward e out-of-sample como padrão
- **Sem martingale** — position sizing baseado em risco fixo por trade
- **Auditabilidade** — toda decisão gera evento rastreável

---

## Arquitetura (visão de alto nível)

Data → Quality → Store → TimeSeries → Indicators/Features
↓
Strategy/AI
↓
Signal
↓
Risk Engine
↓
Execution / Broker
↓
Paper Broker | MT5 Broker


Detalhes em [`docs/architecture.md`](docs/architecture.md).

---

## Requisitos

- Python 3.10+
- Windows (para integração MT5) ou Linux/macOS (modo paper)
- Git

---

## Instalação

```powershell
# 1. Clonar
git clone https://github.com/irlantesteia-cmd/day-trade-ai.git
cd day-trade-ai

# 2. Ambiente virtual
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Dependências (core)
pip install -e .

# 4. (Opcional) Suporte MetaTrader 5 — apenas Windows
pip install -e ".[mt5]"

# 5. (Opcional) Ferramentas de desenvolvimento
pip install -e ".[dev]"