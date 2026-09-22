import pytest
from src.domain.models import Position
from src.engine.reconciler import PositionReconciler, ReconciliationMismatch


class DummyPortfolio:
    def __init__(self, positions=None):
        self.positions = positions or {}


def test_reconciler_in_sync():
    portfolio = DummyPortfolio({"WIN": Position(symbol="WIN", quantity=10.0)})
    reconciler = PositionReconciler(portfolio)

    broker_positions = {"WIN": 10.0}
    mismatches = reconciler.reconcile(broker_positions)

    assert len(mismatches) == 0


def test_reconciler_mismatch_and_ghost():
    portfolio = DummyPortfolio({"WIN": Position(symbol="WIN", quantity=10.0)})
    reconciler = PositionReconciler(portfolio)

    broker_positions = {"WIN": 5.0, "PETR4": 100.0}
    mismatches = reconciler.reconcile(broker_positions)

    assert len(mismatches) == 2

    mismatches_by_sym = {m.symbol: m for m in mismatches}
    assert mismatches_by_sym["WIN"].reason == "Quantity mismatch"
    assert mismatches_by_sym["PETR4"].reason == "Ghost position on broker"


def test_reconciler_missing_on_broker():
    portfolio = DummyPortfolio({"VALE3": Position(symbol="VALE3", quantity=50.0)})
    reconciler = PositionReconciler(portfolio)

    broker_positions = {}
    mismatches = reconciler.reconcile(broker_positions)

    assert len(mismatches) == 1
    assert mismatches[0].symbol == "VALE3"
    assert mismatches[0].reason == "Position missing on broker"