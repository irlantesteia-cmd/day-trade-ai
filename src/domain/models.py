import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.domain.enums import (
    AssetClass,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
    SignalType,
    Timeframe,
)


class Asset(BaseModel):
    symbol: str
    asset_class: AssetClass


class Candle(BaseModel):
    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    @model_validator(mode="after")
    def validate_prices(self) -> "Candle":
        if self.high < self.low or self.high < self.open or self.high < self.close:
            raise ValueError("High price must be >= open, close, and low.")
        if self.low > self.open or self.low > self.close:
            raise ValueError("Low price must be <= open and close.")
        return self


class Signal(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    direction: SignalType = Field(default=SignalType.NEUTRAL, alias="type")
    confidence: float = 1.0
    strategy_id: str = Field(default="UNKNOWN", alias="strategy_name")
    strategy_version: str = "1.0.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def type(self) -> SignalType:
        return self.direction

    @property
    def strategy_name(self) -> str:
        return self.strategy_id


class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Position(BaseModel):
    symbol: str
    side: PositionSide = PositionSide.FLAT
    quantity: float = 0.0
    entry_price: float = 0.0
    current_price: float = 0.0
    unrealized_pnl: float = 0.0