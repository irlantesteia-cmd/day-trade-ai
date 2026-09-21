import math
from typing import Any, Dict, List, Optional
from src.domain.models import Candle
from src.features.base import FeatureExtractor


class NormalizedRSIExtractor(FeatureExtractor):
    def __init__(self, rsi_key: str = "rsi_14") -> None:
        self.rsi_key = rsi_key

    @property
    def name(self) -> str:
        return "norm_rsi"

    def extract(
        self, candles: List[Candle], indicator_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Optional[float]]:
        if not indicator_results or self.rsi_key not in indicator_results:
            return {f"{self.rsi_key}_norm": None}

        raw_rsi = indicator_results.get(self.rsi_key)
        if raw_rsi is None:
            return {f"{self.rsi_key}_norm": None}

        # Normalização para intervalo [-1.0, 1.0] centralizado em 50
        norm_rsi = round((raw_rsi - 50.0) / 50.0, 6)
        return {f"{self.rsi_key}_norm": norm_rsi}


class BollingerPercentBExtractor(FeatureExtractor):
    def __init__(self, bb_key: str = "bb_20") -> None:
        self.bb_key = bb_key

    @property
    def name(self) -> str:
        return "bb_percent_b"

    def extract(
        self, candles: List[Candle], indicator_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Optional[float]]:
        feature_name = f"{self.bb_key}_percent_b"
        if not candles or not indicator_results or self.bb_key not in indicator_results:
            return {feature_name: None}

        bb_data = indicator_results.get(self.bb_key)
        if not isinstance(bb_data, dict):
            return {feature_name: None}

        upper = bb_data.get("upper")
        lower = bb_data.get("lower")
        close = candles[-1].close

        if upper is None or lower is None or upper == lower:
            return {feature_name: None}

        percent_b = (close - lower) / (upper - lower)
        return {feature_name: round(percent_b, 6)}


class SMADistanceExtractor(FeatureExtractor):
    def __init__(self, sma_key: str = "sma_20") -> None:
        self.sma_key = sma_key

    @property
    def name(self) -> str:
        return "sma_distance"

    def extract(
        self, candles: List[Candle], indicator_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Optional[float]]:
        feature_name = f"{self.sma_key}_dist_pct"
        if not candles or not indicator_results or self.sma_key not in indicator_results:
            return {feature_name: None}

        sma_val = indicator_results.get(self.sma_key)
        if sma_val is None or sma_val == 0:
            return {feature_name: None}

        close = candles[-1].close
        dist_pct = ((close - sma_val) / sma_val) * 100.0
        return {feature_name: round(dist_pct, 6)}