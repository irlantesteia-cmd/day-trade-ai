"""
Binance Futures adapter (endpoints publicos de funding).

Nao requer autenticacao para:
  - /fapi/v1/premiumIndex (funding atual)
  - /fapi/v1/fundingRate  (historico de funding)

Uso:
    with BinanceFuturesAdapter() as fa:
        rate = fa.get_current_funding("BTCUSDT")
        history = fa.get_funding_history("BTCUSDT", limit=100)
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


BINANCE_FUTURES_BASE_URL = "https://fapi.binance.com"

# Intervalo de funding na Binance: 8 horas (3x por dia)
FUNDING_INTERVALS_PER_DAY = 3


class BinanceFuturesAdapter:
    """Cliente de endpoints publicos de futuros da Binance."""

    def __init__(self, base_url: str = BINANCE_FUTURES_BASE_URL, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    # ------------------------------------------------------------------
    # Ciclo de vida
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
    # Ping
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        try:
            r = self._get_client().get(f"{self.base_url}/fapi/v1/ping")
            return r.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Funding atual
    # ------------------------------------------------------------------

    def get_current_funding(self, symbol: str) -> Dict[str, Any]:
        """
        Retorna snapshot atual: mark price, index price, lastFundingRate,
        nextFundingTime.
        """
        r = self._get_client().get(
            f"{self.base_url}/fapi/v1/premiumIndex",
            params={"symbol": symbol.upper()},
        )
        r.raise_for_status()
        data = r.json()

        return {
            "symbol": data["symbol"],
            "mark_price": float(data["markPrice"]),
            "index_price": float(data["indexPrice"]),
            "last_funding_rate": float(data["lastFundingRate"]),
            "next_funding_time": datetime.fromtimestamp(
                data["nextFundingTime"] / 1000, tz=timezone.utc
            ),
            "premium_pct": (float(data["markPrice"]) - float(data["indexPrice"]))
                           / float(data["indexPrice"]) * 100,
        }

    # ------------------------------------------------------------------
    # Historico de funding
    # ------------------------------------------------------------------

    def get_funding_history(
        self,
        symbol: str,
        limit: int = 1000,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retorna historico de funding rates (max 1000 por chamada).

        Retorno: lista de dicts ordenada por fundingTime ascendente.
        """
        if limit > 1000:
            limit = 1000

        params: Dict[str, Any] = {
            "symbol": symbol.upper(),
            "limit": limit,
        }
        if start_time is not None:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time is not None:
            params["endTime"] = int(end_time.timestamp() * 1000)

        r = self._get_client().get(
            f"{self.base_url}/fapi/v1/fundingRate",
            params=params,
        )
        r.raise_for_status()
        raw = r.json()

        return [
            {
                "symbol": entry["symbol"],
                "funding_time": datetime.fromtimestamp(
                    entry["fundingTime"] / 1000, tz=timezone.utc
                ),
                "funding_rate": float(entry["fundingRate"]),
                "mark_price": float(entry.get("markPrice", 0.0)),
            }
            for entry in raw
        ]

    # ------------------------------------------------------------------
    # Metricas agregadas
    # ------------------------------------------------------------------

    def funding_stats(
        self,
        symbol: str,
        lookback_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Estatisticas de funding para os ultimos `lookback_days`.

        Retorna:
            n_obs, mean, median, p05, p95, std, pct_positive,
            annualized_mean_pct (assumindo 3 funding/dia),
            strategy_hint (cash_and_carry | reverse | neutral)
        """
        from datetime import timedelta
        import statistics

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=lookback_days)

        history = self.get_funding_history(symbol, limit=1000, start_time=start, end_time=end)
        if not history:
            return {
                "symbol": symbol,
                "n_obs": 0,
                "lookback_days": lookback_days,
                "error": "sem dados",
            }

        rates = [h["funding_rate"] for h in history]
        n = len(rates)
        mean_rate = statistics.mean(rates)
        median_rate = statistics.median(rates)
        std_rate = statistics.pstdev(rates) if n > 1 else 0.0
        pct_positive = sum(1 for r in rates if r > 0) / n
        sorted_rates = sorted(rates)
        p05 = sorted_rates[max(0, int(n * 0.05))]
        p95 = sorted_rates[min(n - 1, int(n * 0.95))]

        # Anualizado: mean * 3 por dia * 365 dias
        annualized_mean_pct = mean_rate * FUNDING_INTERVALS_PER_DAY * 365 * 100

        # Sugestao de estrategia
        if mean_rate > 0.00005:  # > 0.005% por 8h = ~5.5% ao ano
            strategy_hint = "cash_and_carry"  # short perp + long spot
        elif mean_rate < -0.00005:
            strategy_hint = "reverse"  # long perp + short spot
        else:
            strategy_hint = "neutral"

        return {
            "symbol": symbol,
            "lookback_days": lookback_days,
            "n_obs": n,
            "mean_rate": mean_rate,
            "median_rate": median_rate,
            "std_rate": std_rate,
            "p05": p05,
            "p95": p95,
            "pct_positive": pct_positive,
            "annualized_mean_pct": annualized_mean_pct,
            "strategy_hint": strategy_hint,
        }

    # ------------------------------------------------------------------
    # Lista de simbolos com contrato perpetuo
    # ------------------------------------------------------------------

    def list_perpetual_symbols(self) -> List[str]:
        """
        Retorna simbolos com contrato PERPETUAL e status TRADING.
        """
        r = self._get_client().get(f"{self.base_url}/fapi/v1/exchangeInfo")
        r.raise_for_status()
        data = r.json()

        out: List[str] = []
        for s in data.get("symbols", []):
            if s.get("contractType") == "PERPETUAL" and s.get("status") == "TRADING":
                if s.get("quoteAsset") == "USDT":
                    out.append(s["symbol"])
        return sorted(out)