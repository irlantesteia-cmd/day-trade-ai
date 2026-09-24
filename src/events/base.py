"""
Tipos base para o Event Bus.

Define EventType (enum) e Event (dataclass) que circulam pelo sistema.

Referencia: secao 39 do framework (lista oficial de eventos).
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    """Tipos de evento publicaveis no sistema."""

    # Dados de mercado
    MARKET_DATA_RECEIVED = "MarketDataReceived"
    CANDLE_CLOSED = "CandleClosed"

    # Sinais
    SIGNAL_GENERATED = "SignalGenerated"
    SIGNAL_REJECTED = "SignalRejected"

    # Risco
    RISK_APPROVED = "RiskApproved"
    RISK_REJECTED = "RiskRejected"
    RISK_LIMIT_REACHED = "RiskLimitReached"

    # Ordens
    ORDER_CREATED = "OrderCreated"
    ORDER_FILLED = "OrderFilled"
    ORDER_REJECTED = "OrderRejected"

    # Posicoes
    POSITION_OPENED = "PositionOpened"
    POSITION_CLOSED = "PositionClosed"

    # Stop/TP
    STOP_LOSS_TRIGGERED = "StopLossTriggered"
    TAKE_PROFIT_TRIGGERED = "TakeProfitTriggered"

    # Sistema
    SYSTEM_ERROR = "SystemError"


@dataclass
class Event:
    """
    Evento publicado no barramento.

    Campos:
        event_type: tipo do evento (ver EventType)
        payload: dados especificos do evento (schema depende do tipo)
        correlation_id: identificador para rastrear uma operacao ponta-a-ponta
        timestamp: momento do evento (UTC)
    """

    event_type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "payload": dict(self.payload),
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
        }