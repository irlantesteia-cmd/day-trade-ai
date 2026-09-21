from datetime import datetime, timedelta
from typing import List
from src.data.interfaces import MarketDataProvider
from src.domain.enums import Timeframe
from src.domain.models import Candle


class MockMarketDataProvider(MarketDataProvider):
    def fetch_candles(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> List[Candle]:
        candles: List[Candle] = []
        current = start
        base_price = 100.0
        step = (
            timedelta(minutes=1)
            if timeframe == Timeframe.M1
            else timedelta(minutes=5)
        )

        while current <= end:
            candle = Candle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=current,
                open=base_price,
                high=base_price + 1.0,
                low=base_price - 0.5,
                close=base_price + 0.5,
                volume=1000.0,
            )
            candles.append(candle)
            base_price += 0.5
            current += step

        return candles