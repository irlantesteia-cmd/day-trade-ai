import pytest
from src.models.logistic import LogisticRegressionModel


def test_logistic_regression_fit_and_predict():
    X = [[1.0, 2.0], [2.0, 3.0], [-1.0, -2.0], [-2.0, -3.0]]
    y = [1, 1, 0, 0]

    model = LogisticRegressionModel(learning_rate=0.1, epochs=2000)
    model.fit(X, y)

    assert model.is_fitted
    preds = model.predict(X)
    probas = model.predict_proba(X)

    assert len(preds) == 4
    assert preds == [1, 1, 0, 0]
    assert probas[0] > 0.5
    assert probas[2] < 0.5


def test_unfitted_model_raises_error():
    model = LogisticRegressionModel()
    with pytest.raises(RuntimeError):
        model.predict([[1.0, 2.0]])


def test_invalid_hyperparameters():
    with pytest.raises(ValueError):
        LogisticRegressionModel(learning_rate=-0.01)

    with pytest.raises(ValueError):
        LogisticRegressionModel(epochs=0)