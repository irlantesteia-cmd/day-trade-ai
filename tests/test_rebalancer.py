import pytest
from src.portfolio.manager import AssetAllocation
from src.portfolio.rebalancer import PortfolioRebalancer, RebalanceOrder


def test_rebalancer_generates_orders_on_drift():
    rebalancer = PortfolioRebalancer(tolerance_threshold=0.05)

    current_positions = {"WIN": 10.0, "WDO": 0.0}
    current_prices = {"WIN": 100.0, "WDO": 10.0}
    total_equity = 2000.0

    target_allocations = {
        "WIN": AssetAllocation(symbol="WIN", weight=0.25, target_capital=500.0),
        "WDO": AssetAllocation(symbol="WDO", weight=0.75, target_capital=1500.0),
    }

    # WIN atual: 10 * 100 = 1000 (50% do capital). Alvo: 25%. Drift = 25% (>= 5%) -> Vender WIN
    # WDO atual: 0 (0% do capital). Alvo: 75%. Drift = 75% (>= 5%) -> Comprar WDO
    orders = rebalancer.calculate_rebalance(
        current_positions, current_prices, target_allocations, total_equity
    )

    assert len(orders) == 2

    win_order = next(o for o in orders if o.symbol == "WIN")
    assert win_order.action == "SELL"
    assert win_order.quantity == 5.0  # Vender 5 WIN para reduzir de 1000 para 500

    wdo_order = next(o for o in orders if o.symbol == "WDO")
    assert wdo_order.action == "BUY"
    assert wdo_order.quantity == 150.0  # Comprar 150 WDO para subir de 0 para 1500


def test_rebalancer_ignores_minor_drift():
    rebalancer = PortfolioRebalancer(tolerance_threshold=0.10)

    current_positions = {"WIN": 5.0}  # 5 * 100 = 500 (50% do capital)
    current_prices = {"WIN": 100.0}
    total_equity = 1000.0

    target_allocations = {
        "WIN": AssetAllocation(symbol="WIN", weight=0.45, target_capital=450.0),  # Drift = 5% (< 10%)
    }

    orders = rebalancer.calculate_rebalance(
        current_positions, current_prices, target_allocations, total_equity
    )

    assert len(orders) == 0


def test_rebalancer_invalid_inputs():
    rebalancer = PortfolioRebalancer(tolerance_threshold=0.05)

    with pytest.raises(ValueError):
        PortfolioRebalancer(tolerance_threshold=1.5)

    with pytest.raises(ValueError):
        rebalancer.calculate_rebalance({}, {}, {}, total_equity=-100.0)

    with pytest.raises(ValueError):
        rebalancer.calculate_rebalance(
            {"WIN": 10.0}, {"WIN": 0.0}, {}, total_equity=1000.0
        )