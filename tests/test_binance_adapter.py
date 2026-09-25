"""Testes do BinanceDataProvider (mocked httpx)."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.binance_adapter import (
    BinanceDataProvider,
    TIMEFRAME_TO_BINANCE,
    _build_timeframe_map,
)
from src.domain.enums import Timeframe


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _fake_kline(ts_ms: int, o: float, h: float, l: float, c: float, v: float):
    """Formato minimo de kline da Binance (array)."""
    return [
        ts_ms,       # open_time
        str(o),      # open
        str(h),      # high
        str(l),      # low
        str(c),      # close
        str(v),      # volume
        ts_ms + 299_999,  # close_time
        "0",          # quote asset volume
        100,          # num trades
        "0",          # taker buy base
        "0",          # taker buy quote
        "0",          # ignore
    ]


# ---------------------------------------------------------------------------
# Mapeamento de timeframes
# ---------------------------------------------------------------------------

def test_timeframe_map_has_all_supported():
    assert Timeframe.M1 in TIMEFRAME_TO_BINANCE
    assert Timeframe.M5 in TIMEFRAME_TO_BINANCE
    assert Timeframe.M15 in TIMEFRAME_TO_BINANCE
    assert Timeframe.H1 in TIMEFRAME_TO_BINANCE


def test_timeframe_map_values():
    assert TIMEFRAME_TO_BINANCE[Timeframe.M1] == "1m"
    assert TIMEFRAME_TO_BINANCE[Timeframe.M5] == "5m"
    assert TIMEFRAME_TO_BINANCE[Timeframe.M15] == "15m"
    assert TIMEFRAME_TO_BINANCE[Timeframe.H1] == "1h"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def test_raw_to_candle_parses_correctly():
    raw = _fake_kline(1_700_000_000_000, 100.0, 105.0, 99.0, 104.0, 1000.0)
    c = BinanceDataProvider._raw_to_candle("BTCUSDT", Timeframe.M5, raw)
    assert c.symbol == "BTCUSDT"
    assert c.timeframe == Timeframe.M5
    assert c.open == 100.0
    assert c.high == 105.0
    assert c.low == 99.0
    assert c.close == 104.0
    assert c.volume == 1000.0
    assert c.timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# fetch_latest_bars (mocked HTTP)
# ---------------------------------------------------------------------------

@patch("src.adapters.binance_adapter.httpx.Client")
def test_fetch_latest_bars(mock_client_cls):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = [
        _fake_kline(1_700_000_000_000, 100.0, 105.0, 99.0, 104.0, 10.0),
        _fake_kline(1_700_000_300_000, 104.0, 106.0, 103.0, 105.0, 20.0),
    ]
    mock_client.get.return_value = mock_response
    mock_client_cls.return_value = mock_client

    p = BinanceDataProvider()
    bars = p.fetch_latest_bars("BTCUSDT", Timeframe.M5, n=2)

    assert len(bars) == 2
    assert bars[0].close == 104.0
    assert bars[1].close == 105.0

    # Verifica parametros do request
    call_args = mock_client.get.call_args
    assert "BTCUSDT" in str(call_args)
    assert "5m" in str(call_args)


@patch("src.adapters.binance_adapter.httpx.Client")
def test_fetch_latest_bars_rejects_invalid_timeframe(mock_client_cls):
    p = BinanceDataProvider()
    # Timeframe.D1 nao existe no enum (pode ser, depende da versao)
    # Testamos com um valor que definitivamente nao esta no map
    class FakeTF:
        pass
    with pytest.raises(ValueError):
        p.fetch_latest_bars("BTCUSDT", FakeTF(), n=10)


@patch("src.adapters.binance_adapter.httpx.Client")
def test_fetch_latest_bar_returns_dict(mock_client_cls):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = [
        _fake_kline(1_700_000_000_000, 100.0, 105.0, 99.0, 104.0, 10.0),
    ]
    mock_client.get.return_value = mock_response
    mock_client_cls.return_value = mock_client

    p = BinanceDataProvider()
    bar = p.fetch_latest_bar("ETHUSDT", Timeframe.M15)

    assert isinstance(bar, dict)
    assert bar["symbol"] == "ETHUSDT"
    assert bar["open"] == 100.0
    assert bar["close"] == 104.0
    assert "timestamp" in bar


# ---------------------------------------------------------------------------
# fetch_candles (com start/end)
# ---------------------------------------------------------------------------

@patch("src.adapters.binance_adapter.httpx.Client")
def test_fetch_candles_with_range(mock_client_cls):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = [
        _fake_kline(1_700_000_000_000, 100.0, 105.0, 99.0, 104.0, 10.0),
    ]
    mock_client.get.return_value = mock_response
    mock_client_cls.return_value = mock_client

    p = BinanceDataProvider()
    start = datetime(2023, 11, 14, tzinfo=timezone.utc)
    end = datetime(2023, 11, 15, tzinfo=timezone.utc)
    candles = p.fetch_candles("BTCUSDT", Timeframe.M5, start, end)

    assert len(candles) == 1
    assert candles[0].symbol == "BTCUSDT"


# ---------------------------------------------------------------------------
# Ciclo de vida
# ---------------------------------------------------------------------------

@patch("src.adapters.binance_adapter.httpx.Client")
def test_context_manager_closes_client(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    with BinanceDataProvider() as p:
        _ = p._get_client()

    mock_client.close.assert_called_once()