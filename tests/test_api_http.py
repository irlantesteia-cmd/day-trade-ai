"""Testes da API HTTP (FastAPI) - camada sobre APIGateway."""
import pytest
from fastapi.testclient import TestClient

from src.api.app import APIGateway
from src.api.http import app, set_gateway


@pytest.fixture
def client():
    """TestClient com APIGateway real injetado (evita rebuild em cada request)."""
    gateway = APIGateway()
    set_gateway(gateway)
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Endpoints de leitura
# ---------------------------------------------------------------------------

def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_metrics_endpoint(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_status_endpoint(client):
    r = client.get("/status")
    assert r.status_code == 200
    data = r.json()
    assert "environment" in data
    assert "trading_mode" in data
    assert "engine_running" in data


def test_performance_json_default(client):
    r = client.get("/performance")
    assert r.status_code == 200
    data = r.json()
    assert data["format"] == "json"
    assert "total_trades" in data["content"]


def test_performance_markdown(client):
    r = client.get("/performance?format=markdown")
    assert r.status_code == 200
    data = r.json()
    assert data["format"] == "markdown"
    assert "content" in data


def test_performance_invalid_format(client):
    r = client.get("/performance?format=xml")
    assert r.status_code == 422  # validation error


# ---------------------------------------------------------------------------
# Endpoints de acao
# ---------------------------------------------------------------------------

def test_paper_start_and_stop(client):
    # Estado inicial (engine provavelmente parada)
    r_start = client.post("/paper/start")
    assert r_start.status_code == 200
    assert r_start.json()["status"] in ("started", "already_running")

    r_stop = client.post("/paper/stop")
    assert r_stop.status_code == 200
    assert r_stop.json()["status"] in ("stopped", "already_stopped")


def test_paper_start_idempotent(client):
    client.post("/paper/start")
    r = client.post("/paper/start")
    assert r.status_code == 200
    assert r.json()["status"] == "already_running"

    client.post("/paper/stop")


def test_paper_stop_idempotent(client):
    client.post("/paper/stop")
    r = client.post("/paper/stop")
    assert r.status_code == 200
    assert r.json()["status"] == "already_stopped"


# ---------------------------------------------------------------------------
# OpenAPI schema
# ---------------------------------------------------------------------------

def test_openapi_schema_available(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert "paths" in schema
    assert "/health" in schema["paths"]
    assert "/performance" in schema["paths"]