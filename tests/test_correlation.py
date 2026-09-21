import pytest
from src.portfolio.correlation import CorrelationMatrixCalculator, PortfolioRiskAggregator


def test_correlation_matrix_calculator():
    calc = CorrelationMatrixCalculator()
    data = {
        "WIN": [0.01, 0.02, -0.01, 0.03],
        "WDO": [-0.01, -0.02, 0.01, -0.03],  # Perfeitamente negativamente correlacionado
        "PETR4": [0.01, 0.02, -0.01, 0.03],  # Perfeitamente positivamente correlacionado
    }

    matrix = calc.calculate_matrix(data)

    assert pytest.approx(matrix["WIN"]["WIN"], 0.001) == 1.0
    assert pytest.approx(matrix["WIN"]["WDO"], 0.001) == -1.0
    assert pytest.approx(matrix["WIN"]["PETR4"], 0.001) == 1.0


def test_portfolio_risk_aggregator_diversification():
    aggregator = PortfolioRiskAggregator()

    returns_data = {
        "WIN": [0.01, 0.02, -0.01, 0.03],
        "WDO": [-0.01, -0.02, 0.01, -0.03],
    }
    weights = {"WIN": 0.5, "WDO": 0.5}
    volatilities = {"WIN": 0.02, "WDO": 0.02}

    # Com correlação -1.0 e pesos iguais, a volatilidade agregada da carteira deve ser 0.0
    port_vol = aggregator.calculate_portfolio_volatility(weights, volatilities, returns_data)
    assert pytest.approx(port_vol, abs=1e-5) == 0.0


def test_correlation_invalid_inputs():
    calc = CorrelationMatrixCalculator()
    with pytest.raises(ValueError):
        calc.calculate_matrix({})

    with pytest.raises(ValueError):
        calc.calculate_matrix({"WIN": [0.01, 0.02], "WDO": [0.01]})