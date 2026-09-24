"""
HTTP API (FastAPI) - camada fina sobre APIGateway.

Expoe endpoints HTTP que delegam ao APIGateway existente. Nao substitui
o APIGateway (classes Python), apenas o encapsula.

Design:
  - Uma unica instancia de APIGateway, criada lazy e cacheada em app.state
  - Endpoints de leitura: /health, /status, /metrics, /performance
  - Endpoints de acao: /paper/start, /paper/stop
  - Dashboard HTML estatico em / (src/api/static/index.html)
  - Sem autenticacao (fica para milestone futuro)
  - Sem WebSocket / streaming (fica para milestone futuro)

Uso:
    uvicorn src.api.http:app --reload

    ou programaticamente:
        from fastapi.testclient import TestClient
        from src.api.http import app
        client = TestClient(app)
        client.get("/health")
"""
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from src.api.app import APIGateway


logger = logging.getLogger(__name__)


app = FastAPI(
    title="Day Trade AI Platform API",
    description="API HTTP para telemetria, saude e relatorios executivos.",
    version="1.0.0",
)


STATIC_DIR = Path(__file__).parent / "static"


# ---------------------------------------------------------------------------
# Gateway lazy (uma instancia por app)
# ---------------------------------------------------------------------------

def get_gateway(request: Request) -> APIGateway:
    """
    Retorna o APIGateway cacheado em app.state. Cria na primeira chamada.
    """
    gateway = getattr(request.app.state, "gateway", None)
    if gateway is None:
        gateway = APIGateway()
        request.app.state.gateway = gateway
    return gateway


def set_gateway(gateway: APIGateway) -> None:
    """
    Injeta um APIGateway externo (util em testes para evitar build_system()).
    """
    app.state.gateway = gateway


# ---------------------------------------------------------------------------
# Dashboard (HTML estatico)
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    """
    Serve o dashboard HTML estatico.
    O proprio HTML consulta /health, /metrics, /status, /performance
    e os endpoints /paper/* via fetch.
    """
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="dashboard nao encontrado")
    return HTMLResponse(content=index.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Endpoints de leitura
# ---------------------------------------------------------------------------

@app.get("/health")
def health(request: Request) -> Dict[str, Any]:
    """Estado de saude dos componentes do sistema."""
    try:
        gateway = get_gateway(request)
        return gateway.get_health()
    except Exception as exc:
        logger.exception("Erro em /health")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/metrics")
def metrics(request: Request) -> Dict[str, Any]:
    """Resumo de metricas coletadas pela telemetria."""
    try:
        gateway = get_gateway(request)
        return gateway.get_metrics()
    except Exception as exc:
        logger.exception("Erro em /metrics")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/status")
def status(request: Request) -> Dict[str, Any]:
    """
    Estado resumido do sistema: modo de operacao, engine rodando, etc.
    """
    try:
        gateway = get_gateway(request)
        system = gateway.system
        config = system.get("config")
        engine = system.get("engine")
        kill_switch = system.get("kill_switch")

        return {
            "environment": getattr(config, "environment", None),
            "trading_mode": getattr(config, "trading_mode", None),
            "engine_running": getattr(engine, "is_running", False),
            "kill_switch_max_daily_loss": getattr(
                kill_switch, "max_daily_loss", None
            ),
        }
    except Exception as exc:
        logger.exception("Erro em /status")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/performance")
def performance(
    request: Request,
    format: str = Query("json", pattern="^(json|markdown)$"),
) -> Dict[str, Any]:
    """
    Relatorio de performance no formato solicitado (json ou markdown).
    """
    try:
        gateway = get_gateway(request)
        return gateway.get_performance_report(format_type=format)
    except Exception as exc:
        logger.exception("Erro em /performance")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Endpoints de acao
# ---------------------------------------------------------------------------

@app.post("/paper/start")
def paper_start(request: Request) -> Dict[str, Any]:
    """Inicia a engine em modo paper."""
    try:
        gateway = get_gateway(request)
        engine = gateway.system.get("engine")
        if engine is None:
            raise HTTPException(status_code=503, detail="Engine nao disponivel")

        if getattr(engine, "is_running", False):
            return {"status": "already_running"}

        engine.start()
        return {"status": "started"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em /paper/start")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/paper/stop")
def paper_stop(request: Request) -> Dict[str, Any]:
    """Para a engine."""
    try:
        gateway = get_gateway(request)
        engine = gateway.system.get("engine")
        if engine is None:
            raise HTTPException(status_code=503, detail="Engine nao disponivel")

        if not getattr(engine, "is_running", False):
            return {"status": "already_stopped"}

        engine.stop()
        return {"status": "stopped"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em /paper/stop")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Entry point: python -m src.api.http
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.http:app", host="127.0.0.1", port=8000, reload=False)