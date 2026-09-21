from typing import Dict, List
from src.domain.models import Candle
from src.indicators.base import Indicator, IndicatorValue
from src.indicators.registry import IndicatorRegistry


class IndicatorEngine:
    def __init__(self, registry: IndicatorRegistry | None = None) -> None:
        self.registry = registry or IndicatorRegistry()
        self._indicators: Dict[str, Indicator] = {}

    def add_indicator(self, alias: str, indicator: Indicator) -> None:
        self._indicators[alias] = indicator

    def calculate_all(self, candles: List[Candle]) -> Dict[str, IndicatorValue]:
        results: Dict[str, IndicatorValue] = {}
        for alias, indicator in self._indicators.items():
            results[alias] = indicator.calculate(candles)
        return results