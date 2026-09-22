import pytest
from src.api.app import APIGateway


def test_api_gateway_health():
    gateway = APIGateway()
    health = gateway.get_health()
    assert isinstance(health, dict)


def test_api_gateway_metrics():
    gateway = APIGateway()
    metrics = gateway.get_metrics()
    assert isinstance(metrics, dict)


def test_api_gateway_performance_report_json():
    gateway = APIGateway()
    res = gateway.get_performance_report(format_type="json")
    assert res["format"] == "json"
    assert "total_trades" in res["content"]


def test_api_gateway_performance_report_markdown():
    gateway = APIGateway()
    res = gateway.get_performance_report(format_type="markdown")
    assert res["format"] == "markdown"
    assert "# 📊 Relatório Executivo de Performance" in res["content"]