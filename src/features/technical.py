"""
Extratores de features baseados em indicadores tecnicos.

As chaves de indicadores esperadas batem com a saida de
src.indicators.engine.IndicatorEngine.compute_all():
  - rsi         (nao "rsi_14")
  - sma_fast    (nao "sma_20")
  - atr         (nao "atr_14")
  - bb (via IndicatorRegistry / indicator custom, nao via compute_all padrao)

Extratores:
  - NormalizedRSIExtractor    -> rsi_norm
  - SMADistanceExtractor      -> sma_fast_dist_pct
  - ATRNormalizedExtractor    -> atr_norm
  - BollingerPercentBExtractor -> {bb_key}_percent_b (requer bb custom)
"""
from typing import Any, Dict, List, Optional

from src.domain.models import Candle
from src.features.base import FeatureExtractor


class NormalizedRSIExtractor(FeatureExtractor):
    """RSI normalizado para [-1.0, 1.0], centralizado em 50."""

    def __init__(self, rsi_key: str = "rsi") -> None:
        self.rsi_key = rsi_key

    @property
    def name(self) -> str:
        return "norm_rsi"

    def extract(
        self,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Optional[float]]:
        feature_name = f"{self.rsi_key}_norm"
        if not indicator_results or self.rsi_key not in indicator_results:
            return {feature_name: None}

        raw_rsi = indicator_results.get(self.rsi_key)
        if raw_rsi is None:
            return {feature_name: None}

        norm_rsi = round((float(raw_rsi) - 50.0) / 50.0, 6)
        return {feature_name: norm_rsi}


class SMADistanceExtractor(FeatureExtractor):
    """Distancia percentual do close ate a SMA."""

    def __init__(self, sma_key: str = "sma_fast") -> None:
        self.sma_key = sma_key

    @property
    def name(self) -> str:
        return "sma_distance"

    def extract(
        self,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
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


class ATRNormalizedExtractor(FeatureExtractor):
    """ATR dividido pelo close atual (adimensional, escala com o ativo)."""

    def __init__(self, atr_key: str = "atr") -> None:
        self.atr_key = atr_key

    @property
    def name(self) -> str:
        return "norm_atr"

    def extract(
        self,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Optional[float]]:
        feature_name = f"{self.atr_key}_norm"
        if not candles or not indicator_results or self.atr_key not in indicator_results:
            return {feature_name: None}

        atr_val = indicator_results.get(self.atr_key)
        if atr_val is None or atr_val == 0:
            return {feature_name: None}

        close = candles[-1].close
        if close == 0:
            return {feature_name: None}

        return {feature_name: round(float(atr_val) / close, 6)}


class BollingerPercentBExtractor(FeatureExtractor):
    """
    Percent B de Bollinger. Requer que indicator_results contenha
    a chave bb_key com um dict {"upper": ..., "lower": ...}.

    Nao e populado por IndicatorEngine.compute_all() padrao — precisa
    de um indicador custom registrado.
    """

    def __init__(self, bb_key: str = "bb_20") -> None:
        self.bb_key = bb_key

    @property
    def name(self) -> str:
        return "bb_percent_b"

    def extract(
        self,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
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