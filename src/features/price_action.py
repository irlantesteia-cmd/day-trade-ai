import math
from typing import Any, Dict, List, Optional
from src.domain.models import Candle
from src.features.base import FeatureExtractor


class LogReturnExtractor(FeatureExtractor):
    def __init__(self, period: int = 1) -> None:
        self.period = period

    @property
    def name(self) -> str:
        return f"log_return_{self.period}"

    def extract(
        self, candles: List[Candle], indicator_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Optional[float]]:
        feature_name = f"log_return_{self.period}"
        if len(candles) <= self.period:
            return {feature_name: None}

        curr_close = candles[-1].close
        prev_close = candles[-(self.period + 1)].close

        if curr_close <= 0 or prev_close <= 0:
            return {feature_name: None}

        log_ret = math.log(curr_close / prev_close)
        return {feature_name: round(log_ret, 6)}


class CandleMorphologyExtractor(FeatureExtractor):
    @property
    def name(self) -> str:
        return "candle_morphology"

    def extract(
        self, candles: List[Candle], indicator_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Optional[float]]:
        if not candles:
            return {
                "body_ratio": None,
                "upper_shadow_ratio": None,
                "lower_shadow_ratio": None,
            }

        last = candles[-1]
        candle_range = last.high - last.low

        if candle_range == 0:
            return {
                "body_ratio": 0.0,
                "upper_shadow_ratio": 0.0,
                "lower_shadow_ratio": 0.0,
            }

        body_size = abs(last.close - last.open)
        upper_shadow = last.high - max(last.open, last.close)
        lower_shadow = min(last.open, last.close) - last.low

        return {
            "body_ratio": round(body_size / candle_range, 6),
            "upper_shadow_ratio": round(upper_shadow / candle_range, 6),
            "lower_shadow_ratio": round(lower_shadow / candle_range, 6),
        }