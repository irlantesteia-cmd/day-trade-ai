import pytest
from src.validation.sensitivity import SensitivityAnalyzer, SensitivityResult


def dummy_flat_eval(params: dict) -> float:
    p1 = params.get("fast_period", 10)
    p2 = params.get("slow_period", 50)
    return 100.0 - (p1 * 0.1) - (p2 * 0.05)


def dummy_spiky_eval(params: dict) -> float:
    p1 = params.get("fast_period", 10)
    return 500.0 if p1 == 10 else 10.0


def test_sensitivity_analyzer_flat_plateau():
    grid = {
        "fast_period": [9, 10, 11],
        "slow_period": [48, 50, 52],
    }
    analyzer = SensitivityAnalyzer(dummy_flat_eval)
    res = analyzer.analyze(grid)

    assert isinstance(res, SensitivityResult)
    assert len(res.results) == 9
    assert res.mean_score > 90.0
    assert res.stability_index > 0.95
    assert res.best_params["fast_period"] == 9


def test_sensitivity_analyzer_spiky_overfit():
    grid = {"fast_period": [8, 9, 10, 11, 12]}
    analyzer = SensitivityAnalyzer(dummy_spiky_eval)
    res = analyzer.analyze(grid)

    assert res.best_params["fast_period"] == 10
    assert res.stability_index < 0.50


def test_sensitivity_analyzer_invalid_grid():
    analyzer = SensitivityAnalyzer(dummy_flat_eval)
    with pytest.raises(ValueError):
        analyzer.analyze({})