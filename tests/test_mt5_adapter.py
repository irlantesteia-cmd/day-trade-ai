from unittest.mock import patch, MagicMock
from src.adapters.mt5_adapter import MT5Adapter
from src.domain.models import Signal, SignalDirection, OrderStatus

def test_mt5_adapter_execute_signal():
    adapter = MT5Adapter()
    adapter.initialize()

    signal = Signal(
        symbol="WIN$",
        direction=SignalDirection.BUY,
        confidence=0.9,
        metadata={"price": 100.0},
    )
    bar = {"symbol": "WIN$", "close": 105.0}

    # Simula resposta de sucesso do MetaTrader 5 (TRADE_RETCODE_DONE = 10009)
    mock_result = MagicMock()
    mock_result.retcode = 10009
    mock_result.price = 105.0

    with patch("MetaTrader5.order_send", return_value=mock_result):
        order = adapter.execute_signal(signal, bar)
        assert order.symbol == "WIN$"
        assert order.direction == SignalDirection.BUY
        assert order.status == OrderStatus.FILLED