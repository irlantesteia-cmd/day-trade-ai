from typing import Dict, List, Optional
from src.domain.models import Candle


class DataEngine:
    def __init__(self):
        self._candles: Dict[str, List[Candle]] = {}

    def add_candle(self, candle: Candle):
        symbol = candle.symbol
        if symbol not in self._candles:
            self._candles[symbol] = []
        self._candles[symbol].append(candle)

    def add_candles(self, candles: List[Candle]):
        for candle in candles:
            self.add_candle(candle)

    def get_candles(self, symbol: str) -> List[Candle]:
        return self._candles.get(symbol, [])