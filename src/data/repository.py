from typing import List
from sqlalchemy.orm import Session
from src.data.models import CandleModel
from src.domain.enums import Timeframe
from src.domain.models import Candle


class CandleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save_candles(self, candles: List[Candle]) -> int:
        models = [
            CandleModel(
                symbol=c.symbol,
                timeframe=c.timeframe.value,
                timestamp=c.timestamp,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                volume=c.volume,
            )
            for c in candles
        ]
        self.db.add_all(models)
        self.db.commit()
        return len(models)

    def get_candles(self, symbol: str, timeframe: Timeframe) -> List[Candle]:
        models = (
            self.db.query(CandleModel)
            .filter(
                CandleModel.symbol == symbol,
                CandleModel.timeframe == timeframe.value,
            )
            .order_by(CandleModel.timestamp.asc())
            .all()
        )
        return [
            Candle(
                symbol=m.symbol,
                timeframe=Timeframe(m.timeframe),
                timestamp=m.timestamp,
                open=m.open,
                high=m.high,
                low=m.low,
                close=m.close,
                volume=m.volume,
            )
            for m in models
        ]