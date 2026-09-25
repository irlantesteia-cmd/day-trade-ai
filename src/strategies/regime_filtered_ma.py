"""
RegimeFilteredMAStrategy - MA Crossover condicionada a regime de volatilidade.

Baseada no achado do M25: MA tem edge negativo em regimes de baixa
volatilidade e edge positivo em regimes de alta volatilidade no WINV26 M5.

Design SEM look-ahead:
  - A cada candle, computa realized_vol_20 dos candles ANTERIORES
  - Compara com threshold ROLANTE (percentil sobre janela de vol)
  - Se vol_atual > threshold_percentil: avalia MA
  - Caso contrario: NEUTRAL (nao opera)

Diferente da analise retrospectiva (M25), aqui o threshold e
calculado apenas com dados passados. Nao ha espiar o futuro.

Uso:
    strategy = RegimeFilteredMAStrategy(
        vol_window=20,
        vol_lookback=500,
        vol_percentile=66.0,
    )
"""
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.domain.enums import SignalDirection, Timeframe
from src.domain.models import Candle, Signal
from src.features.volatility import RealizedVolatilityExtractor


class RegimeFilteredMAStrategy:
    def __init__(
        self,
        vol_window: int = 20,
        vol_lookback: int = 500,
        vol_percentile: float = 66.0,
        fast_key: str = "sma_fast",
        slow_key: str = "sma_slow",
        name: str = "REGIME_FILTERED_MA",
    ):
        if vol_window < 2:
            raise ValueError("vol_window deve ser >= 2")
        if vol_lookback < vol_window:
            raise ValueError("vol_lookback deve ser >= vol_window")
        if not 0 < vol_percentile < 100:
            raise ValueError("vol_percentile deve estar em (0, 100)")

        self.vol_window = vol_window
        self.vol_lookback = vol_lookback
        self.vol_percentile = vol_percentile
        self.fast_key = fast_key
        self.slow_key = slow_key
        self.name = name

        # Extrator de vol e buffer de vol historico
        self._vol_extractor = RealizedVolatilityExtractor(period=vol_window)
        self._vol_history: deque = deque(maxlen=vol_lookback)

    def _neutral(self, candles: List[Candle], reason: str) -> Signal:
        if candles:
            last = candles[-1]
            return Signal(
                symbol=last.symbol,
                timeframe=last.timeframe,
                timestamp=last.timestamp,
                direction=SignalDirection.NEUTRAL,
                confidence=0.0,
                strategy_name=self.name,
                metadata={"reason": reason},
            )
        return Signal(
            symbol="UNKNOWN",
            timeframe=Timeframe.M5,
            timestamp=datetime.now(timezone.utc),
            direction=SignalDirection.NEUTRAL,
            confidence=0.0,
            strategy_name=self.name,
            metadata={"reason": reason},
        )

    def _update_vol_history(self, candles: List[Candle]) -> Optional[float]:
        """
        Retorna a realized_vol do candle atual, e a adiciona ao historico.

        Diferente da analise retrospectiva, aqui NAO usamos tercis do
        total. Apenas acumulamos vol passada e comparamos com percentil.
        """
        if len(candles) < self.vol_window + 1:
            return None

        out = self._vol_extractor.extract(candles, None)
        vol = out.get(f"realized_vol_{self.vol_window}")
        if vol is None:
            return None

        self._vol_history.append(vol)
        return vol

    def _vol_threshold(self) -> Optional[float]:
        """Percentil do historico de vol. None se historico insuficiente."""
        if len(self._vol_history) < self.vol_window * 2:
            return None
        sorted_vols = sorted(self._vol_history)
        idx = int(len(sorted_vols) * self.vol_percentile / 100.0)
        idx = max(0, min(idx, len(sorted_vols) - 1))
        return sorted_vols[idx]

    def evaluate(
        self,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
        feature_results: Optional[Dict[str, Any]] = None,
    ) -> Signal:
        if not candles:
            return self._neutral(candles, "sem candles")

        # 1. Atualiza vol do candle atual
        current_vol = self._update_vol_history(candles)
        if current_vol is None:
            return self._neutral(candles, "vol indisponivel")

        # 2. Threshold de vol
        threshold = self._vol_threshold()
        if threshold is None:
            return self._neutral(candles, "historico vol insuficiente")

        # 3. Filtro: so opera se vol atual > threshold
        if current_vol <= threshold:
            return self._neutral(candles, "vol abaixo do threshold")

        # 4. MA Crossover
        indicators = indicator_results or {}
        sma_fast = indicators.get(self.fast_key, indicators.get("sma_fast", 0.0))
        sma_slow = indicators.get(self.slow_key, indicators.get("sma_slow", 0.0))

        if sma_slow <= 0:
            return self._neutral(candles, "SMA slow invalida")

        last = candles[-1]
        metadata = {
            "vol_at_entry": current_vol,
            "vol_threshold": threshold,
            "sma_fast": sma_fast,
            "sma_slow": sma_slow,
        }

        if sma_fast > sma_slow:
            return Signal(
                symbol=last.symbol,
                timeframe=last.timeframe,
                timestamp=last.timestamp,
                direction=SignalDirection.BUY,
                confidence=0.8,
                strategy_name=self.name,
                metadata=metadata,
            )
        if sma_fast < sma_slow:
            return Signal(
                symbol=last.symbol,
                timeframe=last.timeframe,
                timestamp=last.timestamp,
                direction=SignalDirection.SELL,
                confidence=0.8,
                strategy_name=self.name,
                metadata=metadata,
            )

        return self._neutral(candles, "MA sem cruzamento")