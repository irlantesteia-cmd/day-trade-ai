from datetime import datetime
import pytest
from src.models.logistic import LogisticRegressionModel
from src.strategies.ml_strategy import MLSignalStrategy
from src.domain.enums import SignalType


@pytest.fixture
def fitted_model():
    X = [[1.0, 2.0], [2.0, 3.0], [-1.0, -2.0], [-2.0, -3.0]]
    y = [1, 1, 0, 0]
    model = LogisticRegressionModel(learning_rate=0.1, epochs=2000)
    model.fit(X, y)
    return model


def test_ml_strategy_buy_signal(fitted_model):
    strategy = MLSignalStrategy(
        model=fitted_model,
        feature_keys=["f1", "f2"],
        buy_threshold=0.60,
        sell_threshold=0.40,
    )
    bar = {
        "symbol": "WIN",
        "timestamp": datetime(2026, 1, 1, 10, 0),
        "close": 100.0,
        "f1": 2.0,
        "f2": 3.0,
    }
    sig = strategy.generate_signal(bar)

    assert sig is not None
    assert sig.symbol == "WIN"
    assert sig.direction == SignalType.BUY
    assert sig.metadata["price"] == 100.0


def test_ml_strategy_sell_signal(fitted_model):
    strategy = MLSignalStrategy(
        model=fitted_model,
        feature_keys=["f1", "f2"],
        buy_threshold=0.60,
        sell_threshold=0.40,
    )
    bar = {
        "symbol": "WIN",
        "timestamp": datetime(2026, 1, 1, 10, 0),
        "close": 100.0,
        "f1": -2.0,
        "f2": -3.0,
    }
    sig = strategy.generate_signal(bar)

    assert sig is not None
    assert sig.direction == SignalType.SELL


def test_ml_strategy_invalid_model_or_params(fitted_model):
    unfitted = LogisticRegressionModel()
    with pytest.raises(ValueError, match="fitted"):
        MLSignalStrategy(unfitted, feature_keys=["f1"])

    with pytest.raises(ValueError, match="greater than"):
        MLSignalStrategy(fitted_model, feature_keys=["f1"], buy_threshold=0.40, sell_threshold=0.60)