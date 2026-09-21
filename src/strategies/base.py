from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from src.domain.models import Candle, Signal


class Strategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Nome identificador da estratégia."""
        pass

    @abstractmethod
    def evaluate(
        self,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
        feature_results: Optional[Dict[str, Any]] = None,
    ) -> Signal:
        """Avalia o estado do mercado e gera um sinal de negociação (BUY, SELL ou NEUTRAL)."""
        pass