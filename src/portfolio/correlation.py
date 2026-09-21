import math
from typing import Dict, List


class CorrelationMatrixCalculator:
    @staticmethod
    def _mean(series: List[float]) -> float:
        return sum(series) / len(series)

    @staticmethod
    def _std(series: List[float], mean_val: float) -> float:
        n = len(series)
        if n <= 1:
            return 0.0
        var = sum((x - mean_val) ** 2 for x in series) / (n - 1)
        return math.sqrt(var)

    def calculate_matrix(self, returns_data: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
        if not returns_data:
            raise ValueError("returns_data cannot be empty")

        symbols = list(returns_data.keys())
        length = len(returns_data[symbols[0]])

        for sym, rets in returns_data.items():
            if len(rets) != length:
                raise ValueError(f"Length mismatch in returns for symbol {sym}")
            if len(rets) < 2:
                raise ValueError("At least 2 data points required to calculate correlation")

        means = {sym: self._mean(rets) for sym, rets in returns_data.items()}
        stds = {sym: self._std(rets, means[sym]) for sym, rets in returns_data.items()}

        matrix: Dict[str, Dict[str, float]] = {s1: {} for s1 in symbols}

        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                if i == j:
                    matrix[sym1][sym2] = 1.0
                elif j < i:
                    matrix[sym1][sym2] = matrix[sym2][sym1]
                else:
                    std1 = stds[sym1]
                    std2 = stds[sym2]
                    if std1 == 0.0 or std2 == 0.0:
                        matrix[sym1][sym2] = 0.0
                    else:
                        cov = sum(
                            (returns_data[sym1][k] - means[sym1]) * (returns_data[sym2][k] - means[sym2])
                            for k in range(length)
                        ) / (length - 1)
                        corr = cov / (std1 * std2)
                        matrix[sym1][sym2] = max(-1.0, min(1.0, corr))

        return matrix


class PortfolioRiskAggregator:
    def __init__(self, correlation_calculator: CorrelationMatrixCalculator = None):
        self.corr_calc = correlation_calculator or CorrelationMatrixCalculator()

    def calculate_portfolio_volatility(
        self,
        weights: Dict[str, float],
        volatilities: Dict[str, float],
        returns_data: Dict[str, List[float]],
    ) -> float:
        symbols = list(weights.keys())
        for sym in symbols:
            if sym not in volatilities or sym not in returns_data:
                raise KeyError(f"Missing volatility or returns data for symbol: {sym}")

        matrix = self.corr_calc.calculate_matrix(returns_data)

        port_variance = 0.0
        for sym1 in symbols:
            w1 = weights[sym1]
            v1 = volatilities[sym1]
            for sym2 in symbols:
                w2 = weights[sym2]
                v2 = volatilities[sym2]
                corr = matrix[sym1][sym2]
                port_variance += w1 * w2 * v1 * v2 * corr

        return math.sqrt(max(0.0, port_variance))