from typing import Any, Dict, List
from src.domain.models import Candle


class FeatureEngine:
    """Motor de geração e extração de features para análise e modelos de IA."""

    def compute_features(
        self,
        candles: List[Candle],
        indicator_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not candles:
            return {}

        last_candle = candles[-1]
        candle_range = last_candle.high - last_candle.low
        body_size = abs(last_candle.close - last_candle.open)

        return {
            "candle_range": candle_range,
            "body_size": body_size,
            "is_bullish": last_candle.close > last_candle.open,
            "close_price": last_candle.close,
            "volume": last_candle.volume,
        }