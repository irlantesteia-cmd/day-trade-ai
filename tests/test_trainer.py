import pytest
from src.agents.auditor import TradeAuditor
from src.agents.trainer import AutoRetrainer
from src.domain.enums import OrderStatus, SignalDirection
from src.domain.models import Order


def test_auto_retrainer_insufficient_samples():
    retrainer = AutoRetrainer(min_samples=5)
    result = retrainer.evaluate_and_retrain([])
    assert result["retrained"] is False
    assert "Amostras insuficientes" in result["reason"]


def test_auto_retrainer_successful_retrain():
    auditor = TradeAuditor()
    retrainer = AutoRetrainer(min_samples=3)

    for i in range(3):
        order = Order(
            symbol="WIN$",
            direction=SignalDirection.BUY,
            quantity=1.0,
            price=100.0 + i,
            status=OrderStatus.FILLED,
        )
        features = {"f1": 1.0 + i, "f2": 2.0 * i}
        pnl = 50.0 if i % 2 == 0 else -20.0
        auditor.record_trade(order, features, expected_price=100.0, pnl=pnl)

    result = retrainer.evaluate_and_retrain(auditor.trade_history)
    assert result["retrained"] is True
    assert result["samples_used"] == 3
    assert "model_weights" in result