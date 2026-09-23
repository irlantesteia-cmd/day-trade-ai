# Desenvolvimento

## Ambiente

- Windows 10/11 (para MT5) ou Linux/macOS (modo paper)
- Python 3.10+ (recomendado 3.12)
- PowerShell ou bash
- VSCode recomendado

## Setup

```powershell
git clone https://github.com/irlantesteia-cmd/day-trade-ai.git
cd day-trade-ai

python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -e ".[dev,mt5]"

Testes
powershell
# Suite completa
pytest tests/ -v

# Arquivo especifico
pytest tests/test_risk.py -v

# Com cobertura (requer pytest-cov)
pip install pytest-cov
pytest tests/ --cov=src --cov-report=term-missing
Padrao obrigatorio: todos os 132 testes devem passar antes de commit.

Convencoes de Codigo
Commits
Formato: <tipo>(<escopo>): <descricao>

Tipos aceitos:

feat - nova funcionalidade

fix - correcao

docs - documentacao

test - testes

refactor - refatoracao sem mudanca de comportamento

chore - manutencao

Exemplos:

text
feat(risk): adicionar SL/TP dinamico via ATR
fix(cli): restaurar default do argparse
docs(adr): adicionar ADR-002 sobre config duplicado
Evitar: mensagens genericas (update, fix bug, DeepSeek, hsbvdhw).

Branches
main - estavel, sempre passa em CI

feature/<nome> - desenvolvimento

fix/<nome> - correcoes

CI (GitHub Actions)
Arquivo: .github/workflows/ci.yml

Roda em:

push para main ou master

pull requests

Passos:

Setup Python 3.12

pip install . pytest pytest-cov

pytest --maxfail=1 --disable-warnings

Verificacao de deployment readiness

Atencao: o CI roda em ubuntu-latest, onde MetaTrader5 nao tem wheel.
Por isso MT5 e optional dependency ([mt5]).

Docker
powershell
# Build
docker build -t day-trade-ai .

# Run
docker run --rm day-trade-ai
docker-compose disponivel em docker-compose.yml.

Estrutura de Testes
Arquivo	Escopo
test_domain.py	Entidades (Candle, Signal, Order, Position)
test_indicators.py	SMA, EMA, RSI, MACD, ATR, BB, VWAP
test_features.py	Extratores e pipeline
test_strategies.py	MA, RSI, ML
test_risk.py	Risk manager, position sizing, SL/TP
test_execution.py	PaperBroker, P&L, slippage, fees
test_validation.py	OOS, walk-forward, leakage
test_backtest.py	Backtest engine
test_timeseries.py	Resampling, rolling windows
test_data_engine.py	Providers, quality, persistence
test_e2e_integration.py	Fluxo completo do sistema
test_multi_agent_integration.py	build_system + feedback loop
test_kill_switch.py	Circuit breaker
test_health.py	SystemHealthMonitor
test_telemetry.py	Metricas
test_cli.py, test_cli_formatter.py	CLI
test_api.py, test_webhook.py	API Gateway e webhooks
test_package_build.py	Integridade do pacote
test_ci_workflow.py	Validacao do workflow CI
Criando uma Nova Estrategia
Criar arquivo em src/strategies/<nome>.py

Implementar generate_signal(bar: dict) -> Signal | None

Registrar em src/strategies/registry.py

Adicionar teste em tests/test_strategies.py

Documentar em docs/

Criando um Novo Indicador
Arquivo em src/indicators/<categoria>.py

Registrar em src/indicators/registry.py

Adicionar teste em tests/test_indicators.py

Cobrir caso de dados insuficientes (retornar None)

Debugging
Ver pipeline em tempo real
powershell
$env:LOG_LEVEL = "DEBUG"
python -m src.cli --mode paper --symbol WIN$ --log-level DEBUG
Forcar sinal (com threshold baixo)
powershell
$env:BUY_THRESHOLD = "0.45"
$env:SELL_THRESHOLD = "0.35"
python -m src.cli --mode paper_mt5 --symbol WIN$
Remove-Item Env:\BUY_THRESHOLD
Remove-Item Env:\SELL_THRESHOLD
Verificar carregamento do modelo
powershell
python -c "from src.main import build_system; sys = build_system(); s = sys['engine'].strategy; print(type(s).__name__)"
Notas sobre Encoding (IMPORTANTE)
Ao editar arquivos deste projeto:

Use VSCode, nunca notepad

Salve sempre como UTF-8 (sem BOM)

Prefira ASCII puro em arquivos .md e .py

Se aparecer mojibake (anaГѓВЎlise), o arquivo foi salvo com encoding errado

Verificar encoding de um arquivo:

powershell
Get-Content <arquivo> -Encoding UTF8 | Select-Object -First 5
text

---

**Depois de salvar, rode apenas este comando e cole o output:**

```powershell
Get-Item docs\development.md | Select-Object Name, Length
Get-Content docs\development.md -TotalCount 5