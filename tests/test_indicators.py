from datetime import datetime, timedelta, timezone
from src.domain.enums import Timeframe
from src.domain.models import Candle
from src.indicators.engine import IndicatorEngine
from src.indicators.momentum import MACD, RSI
from src.indicators.registry import IndicatorRegistry
from src.indicators.trend import EMA, SMA, VWAP
from src.indicators.volatility import ATR, BollingerBands
from src.indicators.volume import OBV


def generate_synthetic_candles(count: int) -> list[Candle]:
    start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    candles = []
    base_price = 100.0

    for i in range(count):
        # Gera padrão alternado para testes matemáticos
        price_delta = 1.0 if i % 2 == 0 else -0.5
        close_price = base_price + price_delta
        candles.append(
            Candle(
                symbol="WIN",
                timeframe=Timeframe.M1,
                timestamp=start + timedelta(minutes=i),
                open=base_price,
                high=max(base_price, close_price) + 0.5,
                low=min(base_price, close_price) - 0.5,
                close=close_price,
                volume=1000.0 + (i * 10),
            )
        )
        base_price = close_price
    return candles


def test_sma_calculation():
    candles = generate_synthetic_candles(5)
    sma_3 = SMA(period=3)
    val = sma_3.calculate(candles)
    assert val is not None
    # Média dos últimos 3 closes
    last_3_closes = [c.close for c in candles[-3:]]
    expected = round(sum(last_3_closes) / 3, 6)
    assert val == expected


def test_insufficient_data_returns_none():
    candles = generate_synthetic_candles(3)
    sma_14 = SMA(period=14)
    assert sma_14.calculate(candles) is None


def test_vwap_calculation():
    candles = generate_synthetic_candles(3)
    vwap = VWAP()
    val = vwap.calculate(candles)
    assert val is not None
    assert isinstance(val, float)


def test_bollinger_bands_structure():
    candles = generate_synthetic_candles(25)
    bb = BollingerBands(period=20, std_dev=2.0)
    val = bb.calculate(candles)
    assert isinstance(val, dict)
    assert "middle" in val
    assert "upper" in val
    assert "lower" in val
    assert val["upper"] >= val["middle"] >= val["lower"]


def test_macd_structure():
    candles = generate_synthetic_candles(40)
    macd = MACD(fast=12, slow=26, signal=9)
    val = macd.calculate(candles)
    assert isinstance(val, dict)
    assert "macd" in val
    assert "signal" in val
    assert "histogram" in val


def test_rsi_and_atr_calculation():
    candles = generate_synthetic_candles(20)
    rsi = RSI(period=14)
    atr = ATR(period=14)

    rsi_val = rsi.calculate(candles)
    atr_val = atr.calculate(candles)

    assert rsi_val is not None and 0.0 <= rsi_val <= 100.0
    assert atr_val is not None and atr_val > 0.0


def test_indicator_registry_and_engine():
    registry = IndicatorRegistry()
    registry.register("SMA", SMA)
    registry.register("EMA", EMA)

    engine = IndicatorEngine(registry=registry)
    engine.add_indicator("sma_10", registry.get("SMA", period=10))
    engine.add_indicator("ema_10", registry.get("EMA", period=10))

    candles = generate_synthetic_candles(15)
    results = engine.calculate_all(candles)

    assert "sma_10" in results
    assert "ema_10" in results
    assert results["sma_10"] is not None
    assert results["ema_10"] is not None