from src.domain.enums import OrderSide, OrderType, PositionSide
from src.domain.models import Order
from src.execution.executor import ExecutionEngine


def test_paper_execution_buy_order():
    engine = ExecutionEngine(initial_balance=10000.0)
    order = Order(
        symbol="WIN",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=2.0,
    )

    executed_order = engine.process_order(order, current_price=100.0)

    assert executed_order is not None
    assert executed_order.status.value == "FILLED"
    assert "WIN" in engine.portfolio.positions
    assert engine.portfolio.positions["WIN"].quantity == 2.0
    assert engine.portfolio.positions["WIN"].side == PositionSide.LONG


def test_paper_execution_pnl_realization():
    engine = ExecutionEngine(initial_balance=10000.0)

    # 1. Compra de 2 contratos a 100.0
    buy_order = Order(symbol="WIN", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=2.0)
    engine.process_order(buy_order, current_price=100.0)

    # 2. Venda de fecho de 2 contratos a 110.0 (Lucro de 2 * 10 = R$ 20)
    sell_order = Order(symbol="WIN", side=OrderSide.SELL, order_type=OrderType.MARKET, quantity=2.0)
    engine.process_order(sell_order, current_price=110.0)

    assert "WIN" not in engine.portfolio.positions
    assert engine.portfolio.cash == 10020.0
    assert engine.portfolio.equity == 10020.0


def test_paper_execution_short_order_and_pnl():
    from src.execution.engine import ExecutionEngine
    from src.domain.enums import OrderDirection, OrderType, PositionSide
    from src.domain.models import Order

    engine = ExecutionEngine(initial_balance=10000.0)

    # 1. Abertura de posicao SHORT (venda a 100.0)
    sell_order = Order(
        symbol="WIN",
        side=OrderDirection.SELL,
        order_type=OrderType.MARKET,
        quantity=1.0,
    )
    executed_order = engine.process_order(sell_order, current_price=100.0)

    assert executed_order is not None
    assert executed_order.status.value == "FILLED"
    assert "WIN" in engine.portfolio.positions

    pos = engine.portfolio.positions["WIN"]
    assert pos.quantity == 1.0

    # 2. Fechamento da posicao com compra a 90.0 (Lucro de +10.0 na queda)
    buy_order = Order(
        symbol="WIN",
        side=OrderDirection.BUY,
        order_type=OrderType.MARKET,
        quantity=1.0,
    )
    engine.process_order(buy_order, current_price=90.0)

    # Saldo final = 10010.0 (10000 inicial + 10 de lucro)
    current_cash = getattr(
        engine.portfolio, "cash", getattr(engine.portfolio, "balance", 0.0)
    )
    assert current_cash == 10010.0


def test_paper_execution_slippage_and_fees():
    from src.execution.broker import PaperBroker
    from src.execution.engine import ExecutionEngine
    from src.domain.enums import OrderDirection, OrderType
    from src.domain.models import Order

    # Slippage de 0.5 por ponto e R$ 1.00 de taxa por contrato
    broker = PaperBroker(initial_balance=10000.0, slippage=0.5, fee_per_contract=1.0)
    engine = ExecutionEngine(initial_balance=10000.0, broker=broker)

    order = Order(
        symbol="WIN",
        side=OrderDirection.BUY,
        order_type=OrderType.MARKET,
        quantity=2.0,
    )
    executed = engine.process_order(order, current_price=100.0)

    # Preco executado = 100.0 + 0.5 (slippage) = 100.5
    assert executed.price == 100.5
    assert engine.portfolio.positions["WIN"].entry_price == 100.5

    # Saldo = 10000 - (2 contratos * R$ 1.00 taxa) = 9998.0
    current_cash = getattr(engine.portfolio, "cash", getattr(engine.portfolio, "balance", 0.0))
    assert current_cash == 9998.0