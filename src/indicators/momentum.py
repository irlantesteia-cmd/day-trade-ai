from typing import List
from src.domain.models import Candle
from src.indicators.base import Indicator, IndicatorValue


class RSI(Indicator):
    def __init__(self, period: int = 14) -> None:
        self.period = period

    @property
    def name(self) -> str:
        return f"RSI_{self.period}"

    def calculate(self, candles: List[Candle]) -> IndicatorValue:
        if len(candles) <= self.period:
            return None

        closes = [c.close for c in candles]
        gains, losses = [], []

        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            if diff >= 0:
                gains.append(diff)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(diff))

        avg_gain = sum(gains[: self.period]) / self.period
        avg_loss = sum(losses[: self.period]) / self.period

        for i in range(self.period, len(gains)):
            avg_gain = (avg_gain * (self.period - 1) + gains[i]) / self.period
            avg_loss = (avg_loss * (self.period - 1) + losses[i]) / self.period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return round(rsi, 6)


class MACD(Indicator):
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9) -> None:
        self.fast = fast
        self.slow = slow
        self.signal = signal

    @property
    def name(self) -> str:
        return f"MACD_{self.fast}_{self.slow}_{self.signal}"

    def calculate(self, candles: List[Candle]) -> IndicatorValue:
        min_required = self.slow + self.signal
        if len(candles) < min_required:
            return None

        closes = [c.close for c in candles]

        def _calc_ema_series(data: List[float], period: int) -> List[float]:
            k = 2.0 / (period + 1)
            ema_series = [sum(data[:period]) / period]
            for val in data[period:]:
                ema_series.append((val * k) + (ema_series[-1] * (1.0 - k)))
            return ema_series

        fast_ema = _calc_ema_series(closes, self.fast)
        slow_ema = _calc_ema_series(closes, self.slow)

        offset = self.slow - self.fast
        fast_aligned = fast_ema[offset:]

        macd_line = [f - s for f, s in zip(fast_aligned, slow_ema)]
        if len(macd_line) < self.signal:
            return None

        signal_series = _calc_ema_series(macd_line, self.signal)
        macd_val = macd_line[-1]
        signal_val = signal_series[-1]
        hist_val = macd_val - signal_val

        return {
            "macd": round(macd_val, 6),
            "signal": round(signal_val, 6),
            "histogram": round(hist_val, 6),
        }