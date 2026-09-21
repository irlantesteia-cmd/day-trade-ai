from typing import Any, Dict, List, Optional
from src.domain.models import Candle, Signal
from src.strategies.base import Strategy


class StrategyEngine:
    def __init__(self) -> None:
        self._strategies: List[Strategy] = []

    def add_strategy(self, strategy: Strategy) -> None:
        self._strategies.append(strategy)

    def evaluate_all(
        self,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
        feature_results: Optional[Dict[str, Any]] = None,
    ) -> List[Signal]:
        signals: List[Signal] = []
        for strategy in self._strategies:
            signal = strategy.evaluate(candles, indicator_results, feature_results)
            signals.append(signal)
        return signals