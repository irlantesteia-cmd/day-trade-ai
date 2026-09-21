from abc import ABC, abstractmethod
from datetime import datetime
from typing import List
from src.domain.enums import Timeframe
from src.domain.models import Candle


class MarketDataProvider(ABC):
    @abstractmethod
    def fetch_candles(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> List[Candle]:
        """Obtém candles históricos para o símbolo e intervalo especificados."""
        pass