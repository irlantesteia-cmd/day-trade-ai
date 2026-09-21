from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from src.domain.enums import SignalDirection, Timeframe
from src.domain.models import Candle, Signal
from src.strategies.moving_average import MovingAverageCrossoverStrategy

class StrategyEngine:
    def __init__(self):
        self._strategies: List[Any] = []

    def register_strategy(self, name: str, strategy: Any):
        self.add_strategy(strategy)

    def add_strategy(self, strategy: Any):
        if isinstance(strategy, type):
            inst = strategy()
            self._strategies.append(inst)
        elif strategy is not None:
            self._strategies.append(strategy)

    def evaluate_strategy(
        self,
        strategy_name: str,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
        feature_results: Optional[Dict[str, Any]] = None,
    ) -> Signal:
        default_symbol = candles[-1].symbol if candles else "UNKNOWN"
        default_tf = candles[-1].timeframe if candles else Timeframe.M5
        default_ts = candles[-1].timestamp if candles else datetime.now(timezone.utc)

        for s in self._strategies:
            name = getattr(s, "name", s.__class__.__name__)
            if name == strategy_name or s.__class__.__name__ == strategy_name:
                if hasattr(s, "evaluate"):
                    return s.evaluate(
                        candles=candles,
                        indicator_results=indicator_results,
                        feature_results=feature_results,
                    )

        return Signal(
            symbol=default_symbol,
            timeframe=default_tf,
            timestamp=default_ts,
            direction=SignalDirection.NEUTRAL,
            strength=0.0,
        )

    def evaluate_all(
        self,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
        feature_results: Optional[Dict[str, Any]] = None,
    ) -> List[Signal]:
        signals = []
        seen = set()
        for strategy in self._strategies:
            if id(strategy) in seen:
                continue
            seen.add(id(strategy))
            if hasattr(strategy, "evaluate"):
                sig = strategy.evaluate(
                    candles=candles,
                    indicator_results=indicator_results,
                    feature_results=feature_results,
                )
                signals.append(sig)
        return signals