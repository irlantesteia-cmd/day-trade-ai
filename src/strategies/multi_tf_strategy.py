"""
Estratégia multi-timeframe com detecção de regime.
Treina um modelo por (symbol, timeframe) e usa o regime para filtrar sinais.
"""
import os
from typing import Dict, Any, Optional, List
import logging

import joblib
import numpy as np

logger = logging.getLogger(__name__)

FEATURE_KEYS = [
    "return_1", "return_2", "return_3", "return_5",
    "body_pct", "range_pct",
    "upper_wick_pct", "lower_wick_pct",
    "vol_ratio_20", "atr_14_norm",
    # Features cross-asset (preenchidas pelo orquestrador)
    "corr_win_1", "corr_win_5",
    # Features de regime
    "regime_calm", "regime_normal", "regime_volatile",
]


class RegimeDetector:
    """
    Detecção simplificada de regime por volatilidade (vol clustering).
    3 regimes: 0=CALM, 1=NORMAL, 2=VOLATILE.
    Baseado em quantis de ATR normalizado.
    """
    def __init__(self):
        self.thresholds = None

    def fit(self, atr_series: List[float]):
        arr = np.array(atr_series)
        self.thresholds = (float(np.quantile(arr, 0.33)),
                           float(np.quantile(arr, 0.67)))

    def predict(self, atr_value: float) -> int:
        if self.thresholds is None:
            return 1
        lo, hi = self.thresholds
        if atr_value < lo:
            return 0
        if atr_value > hi:
            return 2
        return 1

    def one_hot(self, regime: int) -> List[float]:
        return [1.0 if regime == i else 0.0 for i in range(3)]


class MultiTFStrategy:
    """
    Estratégia que combina sinais de múltiplos timeframes para um símbolo.
    Usa modelo treinado por timeframe e pondera por regime.
    """

    def __init__(self, models: Dict[str, Any], feature_keys: List[str],
                 buy_threshold: float = 0.58, sell_threshold: float = 0.42,
                 regime_detector: Optional[RegimeDetector] = None):
        self.models = models  # {"M1": model, "M5": model, ...}
        self.feature_keys = feature_keys
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.regime_detector = regime_detector or RegimeDetector()

    def generate_signal(self, features_by_tf: Dict[str, Dict[str, float]]) -> Optional[Any]:
        """
        Recebe features já calculadas por timeframe e combina.
        Retorna Signal se a média das probabilidades cruzar o threshold.
        """
        from src.domain.models import Signal
        from src.domain.enums import SignalDirection

        probs = []
        for tf, feats in features_by_tf.items():
            model = self.models.get(tf)
            if model is None:
                continue
            try:
                vec = [float(feats.get(k, 0.0)) for k in self.feature_keys]
                p = model.predict_proba([vec])[0]
                probs.append(p)
            except Exception as exc:
                logger.debug("Modelo %s falhou: %s", tf, exc)

        if not probs:
            return None

        # Ponderação: timeframes maiores têm mais peso
        weights = {"M1": 0.1, "M5": 0.2, "M15": 0.3, "M30": 0.2, "H1": 0.2}
        avg_p = sum(p * weights.get(tf, 0.2) for p, tf in zip(probs, features_by_tf.keys()))
        total_w = sum(weights.get(tf, 0.2) for tf in features_by_tf.keys())
        avg_p = avg_p / total_w if total_w > 0 else 0.5

        # Filtro de regime: em alta volatilidade, exige mais confiança
        regime = features_by_tf.get("M15", {}).get("regime", 1)
        if regime == 2 and 0.45 < avg_p < 0.55:
            return None  # não opera em zona cinzenta durante volatilidade

        if avg_p >= self.buy_threshold:
            return Signal(
                symbol=features_by_tf.get("symbol", "UNKNOWN"),
                direction=SignalDirection.BUY,
                confidence=float(avg_p),
            )
        if avg_p <= self.sell_threshold:
            return Signal(
                symbol=features_by_tf.get("symbol", "UNKNOWN"),
                direction=SignalDirection.SELL,
                confidence=float(1.0 - avg_p),
            )
        return None