import pytest
from src.cli.formatter import StatusFormatter
from src.main import run_app


def test_status_formatter_output():
    system, _ = run_app()
    summary = StatusFormatter.format_summary(system)

    assert "DAY TRADE AI PLATFORM STATUS" in summary
    assert "Environment    : DEVELOPMENT" in summary
    assert "Engine Running : True" in summary
    assert "Bars Processed : 1" in summary
    assert "Orders Executed: 1" in summary