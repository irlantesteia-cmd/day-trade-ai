from typing import Dict, Any, List, Optional
from src.models.base import BaseModel
from src.domain.models import Signal
from src.domain.enums import SignalType


class MLSignalStrategy:
    def __init__(
        self,
        model: BaseModel,
        feature_keys: List[str],
        buy_threshold: float = 0.60,
        sell_threshold: float = 0.40,
    ):
        if not hasattr(model, "is_fitted") or not getattr(model, "is_fitted"):
            raise ValueError("Model must be fitted before initializing strategy")
        if not feature_keys:
            raise ValueError("feature_keys list cannot be empty")
        if buy_threshold <= sell_threshold:
            raise ValueError("buy_threshold must be strictly greater than sell_threshold")

        self.model = model
        self.feature_keys = feature_keys
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def generate_signal(self, current_bar: Dict[str, Any]) -> Optional[Signal]:
        symbol = current_bar.get("symbol", "UNKNOWN")
        timestamp = current_bar.get("timestamp")

        feat_vector = []
        for k in self.feature_keys:
            if k not in current_bar or current_bar[k] is None:
                return None
            feat_vector.append(float(current_bar[k]))

        probas = self.model.predict_proba([feat_vector])
        if not probas:
            return None

        prob_up = probas[0]

        if prob_up >= self.buy_threshold:
            return Signal(
                symbol=symbol,
                direction=SignalType.BUY,
                confidence=float(prob_up),
                metadata={
                    "price": float(current_bar.get("close", 0.0)),
                    "timestamp": timestamp,
                },
            )
        elif prob_up <= self.sell_threshold:
            return Signal(
                symbol=symbol,
                direction=SignalType.SELL,
                confidence=float(1.0 - prob_up),
                metadata={
                    "price": float(current_bar.get("close", 0.0)),
                    "timestamp": timestamp,
                },
            )

        return None