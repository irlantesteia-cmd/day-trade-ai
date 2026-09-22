from unittest.mock import patch, MagicMock
from src.adapters.mt5_adapter import MT5Adapter
from src.domain.models import Signal, SignalDirection, OrderStatus


def test_mt5_execution_engine_execute():
    engine = MT5Adapter()
    engine.initialize()

    signal = Signal(
        symbol="WIN$",
        direction=SignalDirection.BUY,
        confidence=0.8,
        metadata={},
    )
    bar = {"symbol": "WIN$", "close": 100.0}

    # Simula resposta de sucesso do MetaTrader 5 (TRADE_RETCODE_DONE = 10009)
    mock_result = MagicMock()
    mock_result.retcode = 10009
    mock_result.price = 100.0

    with patch("MetaTrader5.order_send", return_value=mock_result):
        order = engine.execute_signal(signal, bar)
        assert order.symbol == "WIN$"
        assert order.status == OrderStatus.FILLED