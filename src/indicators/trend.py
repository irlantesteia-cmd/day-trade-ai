from typing import List
from src.domain.models import Candle
from src.indicators.base import Indicator, IndicatorValue


class SMA(Indicator):
    def __init__(self, period: int = 14) -> None:
        self.period = period

    @property
    def name(self) -> str:
        return f"SMA_{self.period}"

    def calculate(self, candles: List[Candle]) -> IndicatorValue:
        if len(candles) < self.period:
            return None
        closes = [c.close for c in candles[-self.period:]]
        return round(sum(closes) / self.period, 6)


class EMA(Indicator):
    def __init__(self, period: int = 14) -> None:
        self.period = period

    @property
    def name(self) -> str:
        return f"EMA_{self.period}"

    def calculate(self, candles: List[Candle]) -> IndicatorValue:
        if len(candles) < self.period:
            return None
        k = 2.0 / (self.period + 1)
        closes = [c.close for c in candles]
        ema = sum(closes[: self.period]) / self.period
        for price in closes[self.period:]:
            ema = (price * k) + (ema * (1.0 - k))
        return round(ema, 6)


class VWAP(Indicator):
    @property
    def name(self) -> str:
        return "VWAP"

    def calculate(self, candles: List[Candle]) -> IndicatorValue:
        if not candles:
            return None
        cum_pv = sum(((c.high + c.low + c.close) / 3.0) * c.volume for c in candles)
        cum_vol = sum(c.volume for c in candles)
        if cum_vol == 0:
            return None
        return round(cum_pv / cum_vol, 6)