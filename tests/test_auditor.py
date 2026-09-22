import pytest
from src.agents.auditor import TradeAuditor
from src.domain.enums import OrderStatus, SignalDirection
from src.domain.models import Order


def test_auditor_record_trade_and_summary():
    auditor = TradeAuditor()
    order = Order(
        symbol="WIN$",
        direction=SignalDirection.BUY,
        quantity=1.0,
        price=100.5,
        status=OrderStatus.FILLED,
    )

    features = {"rsi": 30.0, "sma": 100.0}
    record = auditor.record_trade(order, features, expected_price=100.0, pnl=50.0)

    assert record["symbol"] == "WIN$"
    assert record["slippage"] == 0.5
    assert record["pnl"] == 50.0

    summary = auditor.get_performance_summary()
    assert summary["total_trades"] == 1
    assert summary["win_rate"] == 1.0
    assert summary["total_pnl"] == 50.0