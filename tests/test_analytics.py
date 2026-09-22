import pytest
from src.analytics.reporter import PerformanceReporter


def test_empty_report():
    reporter = PerformanceReporter()
    report = reporter.generate_report([])
    assert report["total_trades"] == 0
    assert report["win_rate"] == 0.0
    assert report["total_pnl"] == 0.0


def test_report_metrics_calculation():
    reporter = PerformanceReporter()
    trades = [
        {"pnl": 100.0},
        {"pnl": -50.0},
        {"pnl": 150.0},
        {"pnl": -30.0},
    ]
    report = reporter.generate_report(trades)

    assert report["total_trades"] == 4
    assert report["win_rate"] == 0.5
    assert report["total_pnl"] == 170.0
    assert report["profit_factor"] == pytest.approx(250.0 / 80.0, 0.01)
    assert report["max_drawdown"] == 50.0
    assert report["expectancy"] > 0