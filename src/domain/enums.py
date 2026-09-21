from enum import Enum


class AssetType(Enum):
    STOCK = "STOCK"
    FUTURE = "FUTURE"
    CRYPTO = "CRYPTO"
    INDEX = "INDEX"
    FX = "FX"
    WIN = "WIN"
    WDO = "WDO"


AssetClass = AssetType


class OrderDirection(Enum):
    BUY = "BUY"
    SELL = "SELL"
    LONG = "BUY"
    SHORT = "SELL"


OrderSide = OrderDirection


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    BUY = "LONG"
    SELL = "SHORT"


class SignalDirection(Enum):
    BUY = "BUY"
    SELL = "SELL"
    LONG = "BUY"
    SHORT = "SELL"
    NEUTRAL = "NEUTRAL"


SignalType = SignalDirection


class Timeframe(Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    D1 = "1d"