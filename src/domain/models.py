from datetime import datetime, timezone
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator
from src.domain.enums import (
    AssetClass,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
    SignalDirection,
    Timeframe,
)


class Asset(BaseModel):
    symbol: str
    asset_class: AssetClass
    exchange: str
    min_tick: float = Field(default=0.01, gt=0)
    point_value: float = Field(default=1.0, gt=0)


class Candle(BaseModel):
    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)

    @field_validator("high")
    @classmethod
    def validate_high(cls, v: float, info) -> float:
        values = info.data
        if "open" in values and v < values["open"]:
            raise ValueError("High não pode ser menor que Open")
        if "close" in values and v < values["close"]:
            raise ValueError("High não pode ser menor que Close")
        if "low" in values and v < values["low"]:
            raise ValueError("High não pode ser menor que Low")
        return v

    @field_validator("low")
    @classmethod
    def validate_low(cls, v: float, info) -> float:
        values = info.data
        if "open" in values and v > values["open"]:
            raise ValueError("Low não pode ser maior que Open")
        if "close" in values and v > values["close"]:
            raise ValueError("Low não pode ser maior que Close")
        return v


class Signal(BaseModel):
    signal_id: str = Field(default_factory=lambda: str(uuid4()))
    strategy_id: str
    strategy_version: str
    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    entry_price: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    take_profit: float | None = Field(default=None, gt=0)
    reason: str = ""
    metadata: dict = Field(default_factory=dict)


class Order(BaseModel):
    order_id: str = Field(default_factory=lambda: str(uuid4()))
    signal_id: str | None = None
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float = Field(gt=0)
    price: float | None = Field(default=None, gt=0)
    stop_price: float | None = Field(default=None, gt=0)
    status: OrderStatus = OrderStatus.CREATED
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class Position(BaseModel):
    symbol: str
    side: PositionSide = PositionSide.FLAT
    quantity: float = Field(default=0.0, ge=0)
    avg_price: float = Field(default=0.0, ge=0)
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )