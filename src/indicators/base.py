from abc import ABC, abstractmethod
from typing import Any, List, Union
from src.domain.models import Candle

IndicatorValue = Union[float, dict[str, float], None]


class Indicator(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Nome identificador do indicador."""
        pass

    @abstractmethod
    def calculate(self, candles: List[Candle]) -> IndicatorValue:
        """Calcula o valor do indicador para a lista de candles fornecida."""
        pass