"""Testes de sanidade do script de benchmark de estrategias."""
from datetime import datetime, timedelta, timezone

import pytest

from scripts.benchmark_strategies import (
    build_strategies,
    candles_sinteticos,
    signal_to_label,
    strategy_predictions,
    walk_forward_accuracy,
)
from src.domain.enums import SignalDirection, SignalType, Timeframe
from src.domain.models import Candle, Signal
from src.indicators.engine import IndicatorEngine


def test_candles_sinteticos_basic():
    candles = candles_sinteticos(100)
    assert len(candles) == 100
    assert all(c.symbol == "SYNTH" for c in candles)


def test_signal_to_label_buy():
    sig = Signal(
        symbol="WIN",
        direction=SignalDirection.BUY,
        confidence=0.8,
    )
    assert signal_to_label(sig) == 1


def test_signal_to_label_sell():
    sig = Signal(
        symbol="WIN",
        direction=SignalDirection.SELL,
        confidence=0.8,
    )
    assert signal_to_label(sig) == 0


def test_signal_to_label_neutral_returns_none():
    sig = Signal(
        symbol="WIN",
        direction=SignalDirection.NEUTRAL,
        confidence=0.0,
    )
    assert signal_to_label(sig) is None


def test_signal_to_label_none_signal():
    assert signal_to_label(None) is None


def test_strategy_predictions_returns_list():
    candles = candles_sinteticos(200)
    strategies = build_strategies()
    engine = IndicatorEngine()
    preds = strategy_predictions(
        candles,
        strategies["MA_CROSSOVER"],
        engine,
        min_history=30,
        horizon=5,
    )
    assert len(preds) > 0
    for p in preds:
        assert "index" in p
        assert "label" in p
        assert "actual" in p
        assert "timestamp" in p
        assert p["actual"] in (0, 1)
        assert p["label"] in (0, 1, None)


def test_walk_forward_accuracy_basic():
    preds = [
        {"index": i, "label": 1, "actual": 1, "timestamp": None}
        for i in range(50)
    ]
    folds = walk_forward_accuracy(preds, test_window=20, min_predictions_per_fold=5)
    # 50 preds / 20 = 3 folds (2 completos + 1 parcial de 10)
    assert len(folds) == 3
    for f in folds:
        assert f["acc"] == 1.0
        assert f["baseline"] == 1.0
        assert f["edge_pp"] == 0.0


def test_walk_forward_accuracy_ignores_neutral():
    preds = [{"index": i, "label": None, "actual": 1, "timestamp": None} for i in range(50)]
    folds = walk_forward_accuracy(preds, test_window=20, min_predictions_per_fold=5)
    assert folds == []


def test_walk_forward_accuracy_computes_edge():
    # 10 preds com actuals mistos: 7 "sobe", 3 "desce" -> baseline = 0.7
    # 6 corretos -> acc = 0.6 -> edge = -10 p.p.
    preds = (
        # 5 corretos (label=1, actual=1)
        [{"index": i, "label": 1, "actual": 1, "timestamp": None} for i in range(5)]
        # 1 correto (label=0, actual=0)
        + [{"index": 5, "label": 0, "actual": 0, "timestamp": None}]
        # 2 errados (label=1, actual=0)
        + [{"index": i, "label": 1, "actual": 0, "timestamp": None} for i in range(6, 8)]
        # 2 errados (label=0, actual=1)
        + [{"index": i, "label": 0, "actual": 1, "timestamp": None} for i in range(8, 10)]
    )
    folds = walk_forward_accuracy(preds, test_window=10, min_predictions_per_fold=5)
    assert len(folds) == 1
    assert folds[0]["acc"] == 0.6
    assert folds[0]["baseline"] == 0.7
    assert folds[0]["edge_pp"] == pytest.approx(-10.0, abs=0.01)


def test_build_strategies_keys():
    strategies = build_strategies()
    assert "MA_CROSSOVER" in strategies
    assert "RSI_REVERSION" in strategies