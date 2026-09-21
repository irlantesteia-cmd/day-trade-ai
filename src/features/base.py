from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from src.domain.models import Candle


class FeatureExtractor(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Nome identificador do extrator de features."""
        pass

    @abstractmethod
    def extract(
        self, candles: List[Candle], indicator_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Optional[float]]:
        """Extrai o conjunto de features a partir da lista de candles e indicadores opcionais."""
        pass