from datetime import datetime, timedelta, timezone
import pytest
from src.domain.enums import Timeframe
from src.domain.models import Candle
from src.timeseries.resampler import TimeSeriesResampler
from src.timeseries.window import RollingWindowEngine


def test_resample_1m_to_5m():
    start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    candles_1m = []

    # Criar 5 candles de 1 minuto
    # Candle 0: 10:00 (O:100, H:102, L:99, C:101, V:100)
    # Candle 1: 10:01 (O:101, H:105, L:100, C:104, V:150)
    # Candle 2: 10:02 (O:104, H:104, L:98, C:99, V:200)
    # Candle 3: 10:03 (O:99, H:103, L:99, C:102, V:100)
    # Candle 4: 10:04 (O:102, H:106, L:101, C:105, V:250)
    prices = [
        (100.0, 102.0, 99.0, 101.0, 100.0),
        (101.0, 105.0, 100.0, 104.0, 150.0),
        (104.0, 104.0, 98.0, 99.0, 200.0),
        (99.0, 103.0, 99.0, 102.0, 100.0),
        (102.0, 106.0, 101.0, 105.0, 250.0),
    ]

    for i, (o, h, l, c, v) in enumerate(prices):
        candles_1m.append(
            Candle(
                symbol="WIN",
                timeframe=Timeframe.M1,
                timestamp=start + timedelta(minutes=i),
                open=o,
                high=h,
                low=l,
                close=c,
                volume=v,
            )
        )

    resampled = TimeSeriesResampler.resample(candles_1m, Timeframe.M5)

    assert len(resampled) == 1
    candle_5m = resampled[0]
    assert candle_5m.timeframe == Timeframe.M5
    assert candle_5m.open == 100.0
    assert candle_5m.high == 106.0
    assert candle_5m.low == 98.0
    assert candle_5m.close == 105.0
    assert candle_5m.volume == 800.0


def test_resample_invalid_downsampling():
    start = datetime.now(timezone.utc)
    c_5m = Candle(
        symbol="WIN",
        timeframe=Timeframe.M5,
        timestamp=start,
        open=100.0,
        high=105.0,
        low=95.0,
        close=102.0,
        volume=500.0,
    )

    with pytest.raises(ValueError):
        TimeSeriesResampler.resample([c_5m], Timeframe.M1)


def test_rolling_window_engine_no_look_ahead():
    start = datetime.now(timezone.utc)
    candles = [
        Candle(
            symbol="WIN",
            timeframe=Timeframe.M1,
            timestamp=start + timedelta(minutes=i),
            open=100.0 + i,
            high=105.0 + i,
            low=95.0 + i,
            close=102.0 + i,
            volume=100.0,
        )
        for i in range(5)
    ]

    windows = list(RollingWindowEngine.get_windows(candles, window_size=3))

    assert len(windows) == 3
    # Janela 1: candles[0..2]
    assert windows[0][-1].close == 104.0
    # Janela 2: candles[1..3]
    assert windows[1][-1].close == 105.0
    # Janela 3: candles[2..4]
    assert windows[2][-1].close == 106.0