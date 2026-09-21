import math
from typing import List
from .base import BaseModel


class LogisticRegressionModel(BaseModel):
    def __init__(self, learning_rate: float = 0.01, epochs: int = 1000):
        if learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        if epochs <= 0:
            raise ValueError("epochs must be positive")
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.weights: List[float] = []
        self.bias: float = 0.0
        self.is_fitted: bool = False

    def _sigmoid(self, z: float) -> float:
        if z < -40.0:
            return 0.0
        if z > 40.0:
            return 1.0
        return 1.0 / (1.0 + math.exp(-z))

    def fit(self, X: List[List[float]], y: List[int]) -> None:
        if not X or not y:
            raise ValueError("X and y cannot be empty")
        if len(X) != len(y):
            raise ValueError("Length mismatch between X and y")

        n_samples = len(X)
        n_features = len(X[0])

        self.weights = [0.0] * n_features
        self.bias = 0.0

        for _ in range(self.epochs):
            dw = [0.0] * n_features
            db = 0.0

            for i in range(n_samples):
                linear_pred = self.bias + sum(w * x for w, x in zip(self.weights, X[i]))
                y_pred = self._sigmoid(linear_pred)
                error = y_pred - y[i]

                for j in range(n_features):
                    dw[j] += error * X[i][j]
                db += error

            for j in range(n_features):
                self.weights[j] -= self.learning_rate * (dw[j] / n_samples)
            self.bias -= self.learning_rate * (db / n_samples)

        self.is_fitted = True

    def predict_proba(self, X: List[List[float]]) -> List[float]:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction")
        if not X:
            return []

        probas = []
        for sample in X:
            linear_pred = self.bias + sum(w * x for w, x in zip(self.weights, sample))
            probas.append(self._sigmoid(linear_pred))
        return probas

    def predict(self, X: List[List[float]], threshold: float = 0.5) -> List[int]:
        probas = self.predict_proba(X)
        return [1 if p >= threshold else 0 for p in probas]