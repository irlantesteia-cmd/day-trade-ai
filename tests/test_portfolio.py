import pytest
from src.portfolio.manager import PortfolioManager, AssetAllocation


def test_portfolio_manager_equal_weight():
    pm = PortfolioManager(total_capital=100000.0)
    allocs = pm.allocate_equal_weight(["WIN", "WDO", "PETR4", "VALE3"])

    assert len(allocs) == 4
    assert allocs["WIN"].weight == 0.25
    assert allocs["WIN"].target_capital == 25000.0


def test_portfolio_manager_max_weight_cap():
    pm = PortfolioManager(total_capital=100000.0, max_asset_weight=0.30)
    allocs = pm.allocate_equal_weight(["WIN", "WDO"])

    # 1/2 = 0.50, mas deve ser limitado pelo cap de 0.30
    assert allocs["WIN"].weight == 0.30
    assert allocs["WIN"].target_capital == 30000.0


def test_portfolio_manager_custom_weights():
    pm = PortfolioManager(total_capital=100000.0)
    allocs = pm.allocate_custom_weights({"WIN": 3.0, "WDO": 1.0})

    assert allocs["WIN"].weight == 0.75
    assert allocs["WIN"].target_capital == 75000.0
    assert allocs["WDO"].weight == 0.25
    assert allocs["WDO"].target_capital == 25000.0


def test_portfolio_manager_invalid_inputs():
    with pytest.raises(ValueError):
        PortfolioManager(total_capital=-100.0)

    pm = PortfolioManager(total_capital=10000.0)
    with pytest.raises(ValueError):
        pm.allocate_equal_weight([])

    with pytest.raises(ValueError):
        pm.allocate_custom_weights({"WIN": -1.0})