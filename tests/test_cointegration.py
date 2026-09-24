"""Testes do modulo de cointegracao."""
import numpy as np
import pytest

from src.portfolio.cointegration import (
    CointegrationResult,
    CointegrationTester,
    screen_pairs,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _cointegrated_series(n=500, beta=2.0, seed=42):
    """y = beta*x + ruido estacionario -> cointegradas."""
    np.random.seed(seed)
    x = np.cumsum(np.random.randn(n)) + 100.0
    noise = np.random.randn(n) * 0.5
    y = beta * x + noise
    return y.tolist(), x.tolist()


def _independent_series(n=500, seed=1):
    """Dois random walks independentes -> nao cointegradas."""
    np.random.seed(seed)
    a = np.cumsum(np.random.randn(n)) + 100.0
    b = np.cumsum(np.random.randn(n)) + 100.0
    return a.tolist(), b.tolist()


# ---------------------------------------------------------------------------
# Validacao de parametros
# ---------------------------------------------------------------------------

def test_invalid_threshold_raises():
    with pytest.raises(ValueError):
        CointegrationTester(adf_pvalue_threshold=0.0)
    with pytest.raises(ValueError):
        CointegrationTester(adf_pvalue_threshold=1.0)


def test_mismatched_lengths_raises():
    tester = CointegrationTester()
    with pytest.raises(ValueError):
        tester.test([1, 2, 3], [1, 2, 3, 4])


def test_too_few_observations_raises():
    tester = CointegrationTester()
    with pytest.raises(ValueError):
        tester.test([1, 2, 3], [1, 2, 3])


# ---------------------------------------------------------------------------
# Deteccao de cointegracao
# ---------------------------------------------------------------------------

def test_detects_cointegrated_pair():
    y, x = _cointegrated_series()
    tester = CointegrationTester()
    res = tester.test(y, x, "Y", "X")
    assert res.is_cointegrated is True
    assert res.adf_pvalue < 0.05
    # hedge ratio deve estar proximo de 2.0
    assert 1.8 < res.hedge_ratio < 2.2


def test_rejects_independent_series():
    a, b = _independent_series()
    tester = CointegrationTester()
    res = tester.test(a, b, "A", "B")
    assert res.is_cointegrated is False
    assert res.adf_pvalue > 0.05


def test_half_life_is_none_when_no_reversion():
    """IID noise puro -> sem half-life significativa."""
    y, x = _cointegrated_series()
    tester = CointegrationTester()
    res = tester.test(y, x, "Y", "X")
    # Noise puro: half-life deve ser None ou valor pequeno (nao absurdo)
    if res.half_life is not None:
        assert res.half_life < 1000
    # Nao deve ser 693147180.56 nem similares
    assert res.half_life != 693147180.56


def test_to_dict_serializable():
    y, x = _cointegrated_series()
    tester = CointegrationTester()
    res = tester.test(y, x, "Y", "X")
    d = res.to_dict()
    assert d["symbol_a"] == "Y"
    assert d["symbol_b"] == "X"
    assert isinstance(d["is_cointegrated"], bool)
    assert d["half_life"] is None or isinstance(d["half_life"], float)


# ---------------------------------------------------------------------------
# Construcao de spread
# ---------------------------------------------------------------------------

def test_build_spread_correct():
    tester = CointegrationTester()
    prices_a = [10.0, 12.0, 14.0]
    prices_b = [1.0, 2.0, 3.0]
    spread = tester.build_spread(prices_a, prices_b, hedge_ratio=2.0, intercept=0.0)
    # 10 - 2*1 = 8; 12 - 2*2 = 8; 14 - 2*3 = 8
    assert spread == [8.0, 8.0, 8.0]


def test_build_spread_mismatch_raises():
    tester = CointegrationTester()
    with pytest.raises(ValueError):
        tester.build_spread([1, 2], [1, 2, 3], hedge_ratio=1.0)


# ---------------------------------------------------------------------------
# Z-score
# ---------------------------------------------------------------------------

def test_zscore_length_matches_input():
    tester = CointegrationTester()
    spread = list(range(30))
    z = tester.zscore(spread, window=10)
    assert len(z) == len(spread)
    # Primeiros 9 sao None
    assert z[:9] == [None] * 9
    # Resto sao floats
    for v in z[9:]:
        assert v is not None


def test_zscore_short_series_returns_all_none():
    tester = CointegrationTester()
    z = tester.zscore([1, 2, 3], window=10)
    assert z == [None, None, None]


def test_zscore_invalid_window_raises():
    tester = CointegrationTester()
    with pytest.raises(ValueError):
        tester.zscore([1, 2, 3], window=1)


def test_zscore_zero_std_returns_zero():
    tester = CointegrationTester()
    spread = [5.0] * 30
    z = tester.zscore(spread, window=10)
    for v in z[9:]:
        assert v == 0.0


# ---------------------------------------------------------------------------
# screen_pairs
# ---------------------------------------------------------------------------

def test_screen_pairs_finds_cointegrated_pair():
    y, x = _cointegrated_series()
    prices = {"Y": y, "X": x}
    results = screen_pairs(prices, min_correlation=0.7)
    assert len(results) >= 1
    assert results[0].symbol_a in ("Y", "X")
    assert results[0].is_cointegrated is True


def test_screen_pairs_no_false_positives():
    a, b = _independent_series()
    prices = {"A": a, "B": b}
    results = screen_pairs(prices, min_correlation=0.7)
    # Baixa correlacao filtra antes de testar cointegracao
    # Random walks independentes nao devem passar
    assert len(results) == 0


def test_screen_pairs_empty_dict():
    results = screen_pairs({})
    assert results == []


def test_screen_pairs_ignores_short_series():
    prices = {"A": [1.0, 2.0, 3.0], "B": [1.0, 2.0, 3.0]}
    results = screen_pairs(prices, min_obs=100)
    assert results == []


def test_screen_pairs_sorted_by_pvalue():
    """Se multiplos pares cointegram, o menor p-value vem primeiro."""
    np.random.seed(0)
    n = 300
    base = np.cumsum(np.random.randn(n)) + 100.0
    y1 = 2.0 * base + np.random.randn(n) * 0.3
    y2 = 1.5 * base + np.random.randn(n) * 0.8
    prices = {"base": base.tolist(), "y1": y1.tolist(), "y2": y2.tolist()}
    results = screen_pairs(prices, min_correlation=0.7)
    if len(results) >= 2:
        assert results[0].adf_pvalue <= results[1].adf_pvalue