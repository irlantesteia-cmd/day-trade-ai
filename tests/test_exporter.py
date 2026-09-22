import json
import pytest
from src.analytics.exporter import ExecutiveReportExporter


def test_export_to_json():
    exporter = ExecutiveReportExporter()
    data = {"total_trades": 5, "total_pnl": 250.0, "win_rate": 0.6}
    json_out = exporter.export_to_json(data)
    parsed = json.loads(json_out)
    assert parsed["total_trades"] == 5
    assert parsed["total_pnl"] == 250.0


def test_export_to_markdown():
    exporter = ExecutiveReportExporter()
    data = {
        "total_trades": 10,
        "total_pnl": 500.0,
        "win_rate": 0.7,
        "profit_factor": 2.1,
        "sharpe_ratio": 1.5,
        "max_drawdown": 100.0,
        "expectancy": 50.0,
    }
    md_out = exporter.export_to_markdown(data)
    assert "# 📊 Relatório Executivo de Performance" in md_out
    assert "**Total de Trades:** 10" in md_out
    assert "**PnL Total:** R$ 500.00" in md_out
    assert "**Win Rate:** 70.00%" in md_out