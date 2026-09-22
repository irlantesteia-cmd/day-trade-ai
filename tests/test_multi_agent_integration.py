import pytest
from src.main import build_system, run_app
from src.agents.auditor import TradeAuditor
from src.agents.trainer import AutoRetrainer


def test_build_system_contains_agents():
    system = build_system()
    assert "auditor" in system
    assert "retrainer" in system
    assert isinstance(system["auditor"], TradeAuditor)
    assert isinstance(system["retrainer"], AutoRetrainer)


def test_run_app_executes_feedback_loop():
    system, order = run_app()
    auditor = system["auditor"]

    assert len(auditor.trade_history) == 1
    assert auditor.trade_history[0]["symbol"] == "WIN"
    assert auditor.trade_history[0]["pnl"] == 10.0