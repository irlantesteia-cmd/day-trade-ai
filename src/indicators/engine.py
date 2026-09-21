from typing import Any, Dict, List, Optional
from src.domain.models import Candle

class IndicatorEngine:
    def __init__(self, registry: Optional[Any] = None, **kwargs):
        self.registry = registry
        self.kwargs = kwargs
        self._indicators: Dict[str, Any] = {}

    def add_indicator(self, name: str, indicator: Any):
        self._indicators[name] = indicator

    def calculate_sma(self, candles: List[Candle], period: int = 14) -> float:
        if not candles:
            return 0.0
        closes = [c.close for c in candles[-period:]]
        return sum(closes) / len(closes) if closes else 0.0

    def calculate_rsi(self, candles: List[Candle], period: int = 14) -> float:
        if len(candles) < period + 1:
            return 50.0
        closes = [c.close for c in candles[-(period + 1):]]
        gains, losses = [], []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i - 1]
            gains.append(max(0.0, change))
            losses.append(max(0.0, -change))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def calculate_atr(self, candles: List[Candle], period: int = 14) -> float:
        if len(candles) < 2:
            return 1.0
        tr_list = []
        for i in range(1, len(candles)):
            high = candles[i].high
            low = candles[i].low
            prev_close = candles[i - 1].close
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_list.append(tr)
        selected_tr = tr_list[-period:]
        return sum(selected_tr) / len(selected_tr) if selected_tr else 1.0

    def compute_all(self, candles: List[Candle]) -> Dict[str, Any]:
        if not candles:
            return {}
        return {
            "sma_fast": self.calculate_sma(candles, period=9),
            "sma_slow": self.calculate_sma(candles, period=21),
            "rsi": self.calculate_rsi(candles, period=14),
            "atr": self.calculate_atr(candles, period=14),
            "sma_10": self.calculate_sma(candles, period=10),
            "sma_30": self.calculate_sma(candles, period=30),
        }

    def calculate_all(self, candles: List[Candle], **kwargs) -> Dict[str, Any]:
        res = self.compute_all(candles)
        for name, ind in self._indicators.items():
            if hasattr(ind, "calculate"):
                res[name] = ind.calculate(candles, **kwargs)
            elif callable(ind):
                res[name] = ind(candles, **kwargs)
            else:
                res[name] = ind
        return res