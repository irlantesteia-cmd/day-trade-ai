from sqlalchemy import Column, DateTime, Float, Integer, String
from src.data.database import Base


class CandleModel(Base):
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol = Column(String, index=True, nullable=False)
    timeframe = Column(String, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)