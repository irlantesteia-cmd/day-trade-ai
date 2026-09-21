from typing import List
from src.domain.models import Candle
from src.indicators.base import Indicator, IndicatorValue


class OBV(Indicator):
    @property
    def name(self) -> str:
        return "OBV"

    def calculate(self, candles: List[Candle]) -> IndicatorValue:
        if not candles:
            return None
        obv = 0.0
        for i in range(1, len(candles)):
            if candles[i].close > candles[i - 1].close:
                obv += candles[i].volume
            elif candles[i].close < candles[i - 1].close:
                obv -= candles[i].volume
        return round(obv, 6)