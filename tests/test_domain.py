from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from src.domain.enums import AssetClass, OrderSide, OrderType, SignalDirection, Timeframe
from src.domain.models import Asset, Candle, Order, Position, Signal


def test_candle_creation_valid():
    candle = Candle(
        symbol="WIN",
        timeframe=Timeframe.M1,
        timestamp=datetime.now(timezone.utc),
        open=100.0,
        high=105.0,
        low=98.0,
        close=102.0,
        volume=1500.0,
    )
    assert candle.high >= candle.low
    assert candle.close == 102.0


def test_candle_invalid_high():
    with pytest.raises(ValidationError):
        Candle(
            symbol="WIN",
            timeframe=Timeframe.M1,
            timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=95.0,  # Inválido: High < Open
            low=90.0,
            close=98.0,
            volume=100.0,
        )


def test_signal_creation_and_defaults():
    signal = Signal(
        strategy_id="trend_v1",
        strategy_version="1.0.0",
        symbol="WIN",
        timeframe=Timeframe.M5,
        timestamp=datetime.now(timezone.utc),
        direction=SignalDirection.BUY,
        confidence=0.85,
    )
    assert signal.signal_id is not None
    assert signal.confidence == 0.85


def test_order_and_position():
    order = Order(
        symbol="WIN",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=2.0,
    )
    assert order.quantity == 2.0

    position = Position(symbol="WIN")
    assert position.side == "FLAT"
    assert position.quantity == 0.0