"""
Binance data provider (API publica, sem autenticacao).

Usa o endpoint publico de klines. Nao requer API key para dados.

Endpoints:
    GET /api/v3/klines?symbol=BTCUSDT&interval=5m&limit=N

Mapeamento Timeframe -> intervalo Binance:
    M1  -> 1m
    M5  -> 5m
    M15 -> 15m
    M30 -> 30m
    H1  -> 1h

Notas:
  - Binance retorna timestamps em milissegundos
  - Precos vem como strings; convertemos para float
  - Limite maximo por request: 1000
  - Nao trata rate limit (1200 req/min na pratica)

Uso:
    with BinanceDataProvider() as p:
        candles = p.fetch_latest_bars("BTCUSDT", Timeframe.M5, n=500)
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from src.data.interfaces import MarketDataProvider
from src.domain.enums import Timeframe
from src.domain.models import Candle

logger = logging.getLogger(__name__)


BINANCE_BASE_URL = "https://api.binance.com"


def _build_timeframe_map() -> Dict[Timeframe, str]:
    """Mapeia apenas timeframes suportados pela Binance e disponiveis no enum."""
    out: Dict[Timeframe, str] = {}
    pairs = [
        ("M1", "1m"),
        ("M5", "5m"),
        ("M15", "15m"),
        ("M30", "30m"),
        ("H1", "1h"),
        ("H4", "4h"),
        ("D1", "1d"),
    ]
    for tf_name, binance_name in pairs:
        tf = getattr(Timeframe, tf_name, None)
        if tf is not None:
            out[tf] = binance_name
    return out


TIMEFRAME_TO_BINANCE = _build_timeframe_map()


class BinanceDataProvider(MarketDataProvider):
    """Provider de dados historicos da Binance (klines)."""

    def __init__(self, base_url: str = BINANCE_BASE_URL, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    # ------------------------------------------------------------------
    # Ciclo de vida do client HTTP
    # ------------------------------------------------------------------

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    # ------------------------------------------------------------------
    # Interface MarketDataProvider
    # ------------------------------------------------------------------

    def fetch_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        limit: int = 1000,
    ) -> List[Candle]:
        """Candles em [start, end], limitado a 1000 por request."""
        if timeframe not in TIMEFRAME_TO_BINANCE:
            raise ValueError(f"Timeframe nao suportado pela Binance: {timeframe}")

        interval = TIMEFRAME_TO_BINANCE[timeframe]

        # Converte para ms epoch (Binance usa ms)
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)

        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": min(max(limit, 1), 1000),
        }

        client = self._get_client()
        r = client.get(f"{self.base_url}/api/v3/klines", params=params)
        r.raise_for_status()
        raw = r.json()

        return [self._raw_to_candle(symbol, timeframe, k) for k in raw]

    # ------------------------------------------------------------------
    # Helpers de conveniencia
    # ------------------------------------------------------------------

    def fetch_latest_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        n: int = 500,
    ) -> List[Candle]:
        """Retorna as ultimas N barras (mais recentes)."""
        if timeframe not in TIMEFRAME_TO_BINANCE:
            raise ValueError(f"Timeframe nao suportado pela Binance: {timeframe}")

        interval = TIMEFRAME_TO_BINANCE[timeframe]
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(max(n, 1), 1000),
        }

        client = self._get_client()
        r = client.get(f"{self.base_url}/api/v3/klines", params=params)
        r.raise_for_status()
        raw = r.json()

        return [self._raw_to_candle(symbol, timeframe, k) for k in raw]

    def fetch_latest_bar(self, symbol: str, timeframe: Timeframe = Timeframe.M5) -> Dict[str, Any]:
        """
        Compatibilidade com MT5Adapter.fetch_latest_bar: retorna dict
        da ultima barra.
        """
        candles = self.fetch_latest_bars(symbol, timeframe, n=1)
        if not candles:
            return {}
        c = candles[-1]
        return {
            "symbol": c.symbol,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
            "timestamp": int(c.timestamp.timestamp()),
        }

    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Info do simbolo (price precision, tick size, etc)."""
        client = self._get_client()
        r = client.get(
            f"{self.base_url}/api/v3/exchangeInfo",
            params={"symbol": symbol.upper()},
        )
        r.raise_for_status()
        data = r.json()
        symbols = data.get("symbols", [])
        return symbols[0] if symbols else {}

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------

    @staticmethod
    def _raw_to_candle(symbol: str, timeframe: Timeframe, raw: List[Any]) -> Candle:
        """
        Binance kline (formato array):
            [0] open_time (ms)
            [1] open
            [2] high
            [3] low
            [4] close
            [5] volume
            [6] close_time
            ...
        """
        ts = datetime.fromtimestamp(raw[0] / 1000, tz=timezone.utc)
        return Candle(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=ts,
            open=float(raw[1]),
            high=float(raw[2]),
            low=float(raw[3]),
            close=float(raw[4]),
            volume=float(raw[5]),
        )