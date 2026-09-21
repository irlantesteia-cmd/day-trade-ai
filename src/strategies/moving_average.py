from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from src.domain.enums import SignalDirection, Timeframe
from src.domain.models import Candle, Signal


class MovingAverageCrossoverStrategy:
    def __init__(
        self,
        fast_key: str = "sma_fast",
        slow_key: str = "sma_slow",
        name: str = "MA_CROSSOVER",
        **kwargs,
    ):
        self.fast_key = fast_key
        self.slow_key = slow_key
        self.name = name

    def evaluate(
        self,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
        feature_results: Optional[Dict[str, Any]] = None,
    ) -> Signal:
        if not candles:
            return Signal(
                symbol="UNKNOWN",
                timeframe=Timeframe.M5,
                timestamp=datetime.now(timezone.utc),
                direction=SignalDirection.NEUTRAL,
                strength=0.0,
                strategy_name=self.name,
            )

        last_candle = candles[-1]
        symbol = last_candle.symbol
        timeframe = last_candle.timeframe
        timestamp = last_candle.timestamp
        indicators = indicator_results or {}

        sma_fast = indicators.get(self.fast_key, indicators.get("sma_fast", 0.0))
        sma_slow = indicators.get(self.slow_key, indicators.get("sma_slow", 0.0))

        if sma_fast > sma_slow and sma_slow > 0:
            return Signal(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=timestamp,
                direction=SignalDirection.BUY,
                strength=0.8,
                strategy_name=self.name,
            )
        elif sma_fast < sma_slow and sma_slow > 0:
            return Signal(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=timestamp,
                direction=SignalDirection.SELL,
                strength=0.8,
                strategy_name=self.name,
            )

        return Signal(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp,
            direction=SignalDirection.NEUTRAL,
            strength=0.0,
            strategy_name=self.name,
        )