from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field, model_validator
from src.domain.enums import AssetType, OrderDirection, OrderStatus, OrderType, SignalDirection, Timeframe

class Asset(BaseModel):
    symbol: str
    name: str = ""
    asset_type: Any = "EQUITY"
    exchange: str = "GLOBAL"
    pip_size: float = 0.01

class Candle(BaseModel):
    symbol: str
    timeframe: Timeframe = Timeframe.M5
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    @model_validator(mode="after")
    def validate_prices(self) -> "Candle":
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("Invalid candle high/low bounds")
        return self

class Order(BaseModel):
    order_id: str = Field(default_factory=lambda: f"ord_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    symbol: str
    direction: Union[SignalDirection, OrderDirection]
    order_type: OrderType = OrderType.MARKET
    quantity: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def side(self) -> Union[SignalDirection, OrderDirection]:
        return self.direction

    @side.setter
    def side(self, val: Union[SignalDirection, OrderDirection]):
        self.direction = val

    @model_validator(mode="before")
    @classmethod
    def sync_side(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "side" in data and "direction" not in data:
                data["direction"] = data["side"]
            elif "direction" in data and "side" not in data:
                data["side"] = data["direction"]
        return data

class Position(BaseModel):
    position_id: str = Field(default_factory=lambda: f"pos_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    symbol: str
    direction: Union[SignalDirection, OrderDirection] = OrderDirection.BUY
    side: Any = "FLAT"  # compatibilidade com testes que esperam string/enum FLAT
    quantity: float = 0.0
    entry_price: float = 0.0
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="before")
    @classmethod
    def set_position_side(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "direction" in data and "side" not in data:
                data["side"] = "LONG" if data["direction"] == OrderDirection.BUY else "SHORT"
            elif "side" not in data:
                data["side"] = "FLAT"
        return data

class Signal(BaseModel):
    signal_id: str = Field(default_factory=lambda: f"sig_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    strategy_id: Optional[str] = None
    strategy_version: Optional[str] = None
    symbol: str
    timeframe: Timeframe = Timeframe.M5
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    direction: SignalDirection
    strength: float = 1.0
    confidence: Optional[float] = None
    type: Optional[SignalDirection] = None
    strategy_name: str = "UNKNOWN"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def py_compat_sync(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "confidence" in data and data["confidence"] is not None and "strength" not in data:
                data["strength"] = data["confidence"]
            elif "strength" in data and "confidence" not in data:
                data["confidence"] = data["strength"]
            if "type" in data and type(data["type"]) != type(data.get("direction")) and "direction" not in data:
                data["direction"] = data["type"]
            elif "direction" in data and "type" not in data:
                data["type"] = data["direction"]
        return data

    def model_post_init(self, __context: Any) -> None:
        if self.confidence is None:
            self.confidence = self.strength
        if self.strength == 1.0 and self.confidence is not None:
            self.strength = self.confidence
        if self.type is None:
            self.type = self.direction
        elif self.direction is None:
            self.direction = self.type