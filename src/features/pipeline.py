from typing import Any, Dict, List, Optional
from src.domain.models import Candle
from src.features.base import FeatureExtractor


class FeaturePipeline:
    def __init__(self) -> None:
        self._extractors: List[FeatureExtractor] = []

    def add_extractor(self, extractor: FeatureExtractor) -> None:
        self._extractors.append(extractor)

    def extract_all(
        self, candles: List[Candle], indicator_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Optional[float]]:
        combined_features: Dict[str, Optional[float]] = {}
        for extractor in self._extractors:
            features = extractor.extract(candles, indicator_results)
            combined_features.update(features)
        return combined_features