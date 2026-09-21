from typing import Any, Dict, List, Optional
from src.domain.enums import SignalType
from src.domain.models import Candle, Signal


class MovingAverageCrossoverStrategy:
    def __init__(
        self,
        fast_key: str = "sma_fast",
        slow_key: str = "sma_slow",
        name: str = "MA_CROSSOVER",
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
            raise ValueError("A lista de candles não pode estar vazia.")

        last_candle = candles[-1]

        if (
            not indicator_results
            or self.fast_key not in indicator_results
            or self.slow_key not in indicator_results
        ):
            return Signal(
                symbol=last_candle.symbol,
                timeframe=last_candle.timeframe,
                timestamp=last_candle.timestamp,
                direction=SignalType.NEUTRAL,
                strategy_id=self.name,
                strategy_version="1.0.0",
                confidence=0.0,
                metadata={"reason": "Indicadores ausentes"},
            )

        fast_val = indicator_results.get(self.fast_key)
        slow_val = indicator_results.get(self.slow_key)

        if fast_val is None or slow_val is None:
            return Signal(
                symbol=last_candle.symbol,
                timeframe=last_candle.timeframe,
                timestamp=last_candle.timestamp,
                direction=SignalType.NEUTRAL,
                strategy_id=self.name,
                strategy_version="1.0.0",
                confidence=0.0,
                metadata={"reason": "Valores de indicadores nulos"},
            )

        if fast_val > slow_val:
            sig_type = SignalType.BUY
            diff_pct = abs(fast_val - slow_val) / slow_val
            confidence = min(1.0, max(0.5, 0.5 + diff_pct * 10))
        elif fast_val < slow_val:
            sig_type = SignalType.SELL
            diff_pct = abs(fast_val - slow_val) / slow_val
            confidence = min(1.0, max(0.5, 0.5 + diff_pct * 10))
        else:
            sig_type = SignalType.NEUTRAL
            confidence = 0.0

        return Signal(
            symbol=last_candle.symbol,
            timeframe=last_candle.timeframe,
            timestamp=last_candle.timestamp,
            direction=sig_type,
            strategy_id=self.name,
            strategy_version="1.0.0",
            confidence=round(confidence, 4),
            metadata={"fast_val": fast_val, "slow_val": slow_val},
        )