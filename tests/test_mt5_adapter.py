from unittest.mock import patch, MagicMock

import pytest

from src.adapters.mt5_adapter import MT5Adapter
from src.domain.models import Signal, SignalDirection, OrderStatus
from src.risk.config import RiskConfig


# ---------------------------------------------------------------------------
# Teste existente (mantido)
# ---------------------------------------------------------------------------

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

    mock_result = MagicMock()
    mock_result.retcode = 10009
    mock_result.price = 105.0

    with patch("MetaTrader5.order_send", return_value=mock_result):
        order = adapter.execute_signal(signal, bar)
        assert order.symbol == "WIN$"
        assert order.direction == SignalDirection.BUY
        assert order.status == OrderStatus.FILLED


# ---------------------------------------------------------------------------
# SL/TP - BUY com ATR
# ---------------------------------------------------------------------------

def test_execute_signal_buy_with_atr_computes_sltp():
    config = RiskConfig(reward_to_risk_ratio=2.0)
    adapter = MT5Adapter(risk_config=config)
    adapter.initialize()

    signal = Signal(
        symbol="WIN$",
        direction=SignalDirection.BUY,
        confidence=0.9,
        metadata={"atr": 10.0},  # ATR = 10 -> SL = 15 abaixo, TP = 30 acima
    )
    bar = {"symbol": "WIN$", "close": 100.0}

    mock_result = MagicMock()
    mock_result.retcode = 10009
    mock_result.price = 100.0

    with patch("MetaTrader5.order_send", return_value=mock_result):
        order = adapter.execute_signal(signal, bar)

    assert order.stop_loss is not None
    assert order.take_profit is not None
    # SL = entry - 1.5*ATR = 100 - 15 = 85
    assert order.stop_loss == pytest.approx(85.0, abs=0.01)
    # TP = entry + 1.5*ATR*2 = 100 + 30 = 130
    assert order.take_profit == pytest.approx(130.0, abs=0.01)


# ---------------------------------------------------------------------------
# SL/TP - SELL com ATR
# ---------------------------------------------------------------------------

def test_execute_signal_sell_with_atr_computes_sltp():
    config = RiskConfig(reward_to_risk_ratio=2.0)
    adapter = MT5Adapter(risk_config=config)
    adapter.initialize()

    signal = Signal(
        symbol="WIN$",
        direction=SignalDirection.SELL,
        confidence=0.9,
        metadata={"atr": 10.0},
    )
    bar = {"symbol": "WIN$", "close": 100.0}

    mock_result = MagicMock()
    mock_result.retcode = 10009
    mock_result.price = 100.0

    with patch("MetaTrader5.order_send", return_value=mock_result):
        order = adapter.execute_signal(signal, bar)

    # SELL: SL acima, TP abaixo
    assert order.stop_loss == pytest.approx(115.0, abs=0.01)
    assert order.take_profit == pytest.approx(70.0, abs=0.01)


# ---------------------------------------------------------------------------
# SL/TP - fallback sem ATR (usa default_sl_pct = 1.0%)
# ---------------------------------------------------------------------------

def test_execute_signal_without_atr_uses_default_pct():
    config = RiskConfig(default_sl_pct=1.0, reward_to_risk_ratio=2.0)
    adapter = MT5Adapter(risk_config=config)
    adapter.initialize()

    signal = Signal(
        symbol="WIN$",
        direction=SignalDirection.BUY,
        confidence=0.9,
        metadata={},  # sem ATR
    )
    bar = {"symbol": "WIN$", "close": 100.0}

    mock_result = MagicMock()
    mock_result.retcode = 10009
    mock_result.price = 100.0

    with patch("MetaTrader5.order_send", return_value=mock_result):
        order = adapter.execute_signal(signal, bar)

    # SL distance = 1% de 100 = 1.0 -> SL = 99.0
    # TP distance = 1.0 * 2 = 2.0 -> TP = 102.0
    assert order.stop_loss == pytest.approx(99.0, abs=0.01)
    assert order.take_profit == pytest.approx(102.0, abs=0.01)


# ---------------------------------------------------------------------------
# Request enviado ao MT5 contem sl e tp
# ---------------------------------------------------------------------------

def test_request_includes_sl_tp_fields():
    adapter = MT5Adapter()
    adapter.initialize()

    signal = Signal(
        symbol="WIN$",
        direction=SignalDirection.BUY,
        confidence=0.9,
        metadata={"atr": 10.0},
    )
    bar = {"symbol": "WIN$", "close": 100.0}

    mock_result = MagicMock()
    mock_result.retcode = 10009
    mock_result.price = 100.0

    with patch("MetaTrader5.order_send", return_value=mock_result) as mocked_send:
        adapter.execute_signal(signal, bar)
        # Inspeciona o request que foi passado
        call_args = mocked_send.call_args
        request = call_args[0][0]
        assert "sl" in request
        assert "tp" in request
        assert request["sl"] < request["price"]  # BUY: SL abaixo
        assert request["tp"] > request["price"]  # BUY: TP acima


# ---------------------------------------------------------------------------
# quantity via signal.metadata
# ---------------------------------------------------------------------------

def test_quantity_taken_from_metadata():
    adapter = MT5Adapter()
    adapter.initialize()

    signal = Signal(
        symbol="WIN$",
        direction=SignalDirection.BUY,
        confidence=0.9,
        metadata={"atr": 10.0, "quantity": 3.0},
    )
    bar = {"symbol": "WIN$", "close": 100.0}

    mock_result = MagicMock()
    mock_result.retcode = 10009
    mock_result.price = 100.0

    with patch("MetaTrader5.order_send", return_value=mock_result) as mocked_send:
        order = adapter.execute_signal(signal, bar)
        assert order.quantity == 3.0
        request = mocked_send.call_args[0][0]
        assert request["volume"] == 3.0


# ---------------------------------------------------------------------------
# Rejeitado quando nao conectado
# ---------------------------------------------------------------------------

def test_execute_signal_rejected_when_not_connected():
    adapter = MT5Adapter()
    adapter.is_connected = False  # nunca inicializado

    signal = Signal(
        symbol="WIN$",
        direction=SignalDirection.BUY,
        confidence=0.9,
        metadata={"atr": 10.0},
    )
    bar = {"symbol": "WIN$", "close": 100.0}

    order = adapter.execute_signal(signal, bar)
    assert order.status == OrderStatus.REJECTED
    # Mesmo rejeitada, deve trazer SL/TP calculados
    assert order.stop_loss is not None
    assert order.take_profit is not None