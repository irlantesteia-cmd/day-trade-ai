"""Testes da VolatilityBreakoutStrategy."""
from datetime import datetime, timedelta, timezone

import pytest

from src.domain.enums import SignalDirection, Timeframe
from src.domain.models import Candle
from src.strategies.volatility_breakout import VolatilityBreakoutStrategy


def _make_candle(ts, o, h, l, c, v=1000.0, symbol="TEST", tf=Timeframe.M5):
    return Candle(
        symbol=symbol, timeframe=tf, timestamp=ts,
        open=o, high=h, low=l, close=c, volume=v,
    )


def _low_vol_series(n: int, base_ts=None, price: float = 100.0):
    """Serie com volatilidade baixa (range 0.2)."""
    if base_ts is None:
        base_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        _make_candle(
            base_ts + timedelta(minutes=5 * i),
            o=price, h=price + 0.1, l=price - 0.1, c=price,
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Validacao de parametros
# ---------------------------------------------------------------------------

def test_invalid_lookback_raises():
    with pytest.raises(ValueError):
        VolatilityBreakoutStrategy(lookback=1)


def test_invalid_vol_threshold_raises():
    with pytest.raises(ValueError):
        VolatilityBreakoutStrategy(vol_threshold=0)


# ---------------------------------------------------------------------------
# Casos sem sinal (NEUTRAL)
# ---------------------------------------------------------------------------

def test_empty_candles_returns_neutral():
    s = VolatilityBreakoutStrategy()
    sig = s.evaluate([])
    assert sig.direction == SignalDirection.NEUTRAL


def test_insufficient_history_returns_neutral():
    s = VolatilityBreakoutStrategy(lookback=20)
    candles = _low_vol_series(10)
    sig = s.evaluate(candles)
    assert sig.direction == SignalDirection.NEUTRAL
    assert "insuficiente" in sig.metadata.get("reason", "")


def test_no_volatility_expansion_returns_neutral():
    """Serie toda com mesma volatilidade -> sem expansao -> NEUTRAL."""
    s = VolatilityBreakoutStrategy(lookback=20, vol_threshold=1.5)
    candles = _low_vol_series(25)
    sig = s.evaluate(candles)
    assert sig.direction == SignalDirection.NEUTRAL
    assert "nao expandiu" in sig.metadata.get("reason", "")


def test_volatility_expands_but_no_breakout_returns_neutral():
    """Candle explosivo sem romper maxima anterior."""
    s = VolatilityBreakoutStrategy(lookback=20, vol_threshold=1.5)
    candles = _low_vol_series(24)
    # Candle com range grande mas close dentro da faixa
    candles.append(_make_candle(
        candles[-1].timestamp + timedelta(minutes=5),
        o=100.0, h=100.5, l=99.5, c=100.0,
    ))
    sig = s.evaluate(candles)
    assert sig.direction == SignalDirection.NEUTRAL
    assert "sem breakout" in sig.metadata.get("reason", "")


# ---------------------------------------------------------------------------
# Breakout de alta
# ---------------------------------------------------------------------------

def test_breakout_up_returns_buy():
    s = VolatilityBreakoutStrategy(lookback=20, vol_threshold=1.5)
    candles = _low_vol_series(24)
    # Candle explosivo: range 5x, close > max high anterior (100.1)
    candles.append(_make_candle(
        candles[-1].timestamp + timedelta(minutes=5),
        o=100.0, h=101.0, l=99.5, c=100.9,
    ))
    sig = s.evaluate(candles)
    assert sig.direction == SignalDirection.BUY
    assert sig.strategy_name == "VOLATILITY_BREAKOUT"
    assert sig.metadata["breakout"] == "up"


# ---------------------------------------------------------------------------
# Breakout de baixa
# ---------------------------------------------------------------------------

def test_breakout_down_returns_sell():
    s = VolatilityBreakoutStrategy(lookback=20, vol_threshold=1.5)
    candles = _low_vol_series(24)
    # Candle explosivo para baixo: close < min low anterior (99.9)
    candles.append(_make_candle(
        candles[-1].timestamp + timedelta(minutes=5),
        o=100.0, h=100.5, l=99.0, c=99.1,
    ))
    sig = s.evaluate(candles)
    assert sig.direction == SignalDirection.SELL
    assert sig.metadata["breakout"] == "down"


# ---------------------------------------------------------------------------
# ATR do metadata
# ---------------------------------------------------------------------------

def test_atr_propagated_to_metadata():
    s = VolatilityBreakoutStrategy(lookback=20, vol_threshold=1.5)
    candles = _low_vol_series(24)
    candles.append(_make_candle(
        candles[-1].timestamp + timedelta(minutes=5),
        o=100.0, h=101.0, l=99.5, c=100.9,
    ))
    sig = s.evaluate(candles, indicator_results={"atr": 1.5})
    assert sig.metadata["atr"] == 1.5


def test_no_atr_does_not_break():
    s = VolatilityBreakoutStrategy(lookback=20, vol_threshold=1.5)
    candles = _low_vol_series(24)
    candles.append(_make_candle(
        candles[-1].timestamp + timedelta(minutes=5),
        o=100.0, h=101.0, l=99.5, c=100.9,
    ))
    sig = s.evaluate(candles, indicator_results=None)
    assert "atr" not in sig.metadata


# ---------------------------------------------------------------------------
# Parametrizacao
# ---------------------------------------------------------------------------

def test_vol_threshold_controls_sensitivity():
    """Threshold alto -> menos sinais."""
    candles = _low_vol_series(24)
    # Range 0.5 vs media 0.2 -> ratio 2.5
    candles.append(_make_candle(
        candles[-1].timestamp + timedelta(minutes=5),
        o=100.0, h=100.5, l=100.0, c=100.4,
    ))

    # Threshold 1.5: dispara
    s_low = VolatilityBreakoutStrategy(lookback=20, vol_threshold=1.5)
    assert s_low.evaluate(candles).direction == SignalDirection.BUY

    # Threshold 3.0: nao dispara
    s_high = VolatilityBreakoutStrategy(lookback=20, vol_threshold=3.0)
    assert s_high.evaluate(candles).direction == SignalDirection.NEUTRAL


def test_strategy_name_customizable():
    s = VolatilityBreakoutStrategy(name="CUSTOM_VB")
    assert s.name == "CUSTOM_VB"