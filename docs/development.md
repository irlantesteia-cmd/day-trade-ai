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