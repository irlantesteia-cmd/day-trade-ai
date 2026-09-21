import math
from typing import List
from src.domain.models import Candle
from src.indicators.base import Indicator, IndicatorValue


class ATR(Indicator):
    def __init__(self, period: int = 14) -> None:
        self.period = period

    @property
    def name(self) -> str:
        return f"ATR_{self.period}"

    def calculate(self, candles: List[Candle]) -> IndicatorValue:
        if len(candles) <= self.period:
            return None

        tr_list = []
        for i in range(1, len(candles)):
            curr = candles[i]
            prev = candles[i - 1]
            tr = max(
                curr.high - curr.low,
                abs(curr.high - prev.close),
                abs(curr.low - prev.close),
            )
            tr_list.append(tr)

        if len(tr_list) < self.period:
            return None

        atr = sum(tr_list[: self.period]) / self.period
        for tr in tr_list[self.period:]:
            atr = (atr * (self.period - 1) + tr) / self.period

        return round(atr, 6)


class BollingerBands(Indicator):
    def __init__(self, period: int = 20, std_dev: float = 2.0) -> None:
        self.period = period
        self.std_dev = std_dev

    @property
    def name(self) -> str:
        return f"BB_{self.period}_{self.std_dev}"

    def calculate(self, candles: List[Candle]) -> IndicatorValue:
        if len(candles) < self.period:
            return None
        closes = [c.close for c in candles[-self.period:]]
        middle = sum(closes) / self.period
        variance = sum((x - middle) ** 2 for x in closes) / self.period
        std = math.sqrt(variance)

        return {
            "middle": round(middle, 6),
            "upper": round(middle + (self.std_dev * std), 6),
            "lower": round(middle - (self.std_dev * std), 6),
        }