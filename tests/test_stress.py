import pytest
from src.validation.stress import MonteCarloSimulator, StressTester


def test_monte_carlo_simulation():
    pnl_history = [100.0, -50.0, 200.0, -20.0, 50.0]
    mc = MonteCarloSimulator(num_simulations=100, seed=123)
    res = mc.simulate_equity_curves(pnl_history, initial_capital=1000.0)
    
    assert "p5" in res and "p50" in res and "p95" in res
    assert len(res["p50"]) == len(pnl_history) + 1
    assert res["p5"][0] == 1000.0
    assert res["p95"][-1] >= res["p5"][-1]


def test_stress_tester():
    pnls = [100.0, -100.0, 50.0]
    shocked = StressTester.apply_shock(pnls, slippage_multiplier=2.0, loss_amplifier=1.0)
    assert shocked[0] == 50.0
    assert shocked[1] == -200.0