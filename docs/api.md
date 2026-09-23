# API

## Estado atual

**Importante:** a "API" atual **nao e HTTP**. E um conjunto de classes Python
que expoem funcionalidades programaticamente. Nao ha servidor web.

Uma futura PHASE 16 substituira isto por FastAPI (ver `docs/roadmap.md`).

## APIGateway

Localizacao: `src/api/app.py`

Uso:

```python
from src.api import APIGateway

gateway = APIGateway()

# Health
gateway.health()  # dict com status do sistema

# Metricas
gateway.metrics()  # dict com contadores e gauges

# Relatorio de performance (JSON)
gateway.performance_report(fmt="json")

# Relatorio de performance (Markdown)
gateway.performance_report(fmt="markdown")

WebhookDispatcher
Localizacao: src/api/webhook.py

Uso:

python
from src.api import WebhookDispatcher

dispatcher = WebhookDispatcher(url="https://...")

# Envia alerta
dispatcher.send_alert({"level": "CRITICAL", "message": "..."})

# Envia relatorio
dispatcher.send_report({"pnl": 123.45, "sharpe": 1.2})
Testes
text
tests/test_api.py       # APIGateway
tests/test_webhook.py   # WebhookDispatcher
Endpoints planejados (PHASE 16)
Conforme secao 41 do framework:

Metodo	Rota	Descricao
GET	/health	Estado do sistema
GET	/status	Machine state
GET	/market	Estado de mercado
GET	/signals	Sinais recentes
GET	/strategies	Estrategias ativas
GET	/positions	Posicoes abertas
GET	/orders	Ordens
GET	/portfolio	Estado do portfolio
GET	/performance	Metricas
GET	/risk	Estado de risco
POST	/backtest	Disparar backtest
POST	/paper/start	Iniciar paper trading
POST	/paper/stop	Parar paper trading
POST	/strategies/{id}/enable	Ativar estrategia
POST	/strategies/{id}/disable	Desativar estrategia
Estes endpoints ainda NAO existem.

text

---

**Depois de salvar, rode apenas este comando e cole o output:**

```powershell
Get-Item docs\api.md | Select-Object Name, Length
Get-Content docs\api.md -TotalCount 5