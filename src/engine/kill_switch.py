from enum import Enum
from typing import Any, Optional
from src.telemetry.alerts import Alert, AlertLevel


class CircuitBreakerStatus(str, Enum):
    ARMED = "ARMED"
    TRIPPED = "TRIPPED"
    RESET = "RESET"


class KillSwitch:
    def __init__(self, live_engine: Any, max_daily_loss: float = 1000.0):
        self.engine = live_engine
        self.max_daily_loss = abs(float(max_daily_loss))
        self.status = CircuitBreakerStatus.ARMED
        self.trip_reason: Optional[str] = None

    def trip(self, reason: str) -> None:
        self.status = CircuitBreakerStatus.TRIPPED
        self.trip_reason = reason
        if hasattr(self.engine, "stop"):
            self.engine.stop()

    def handle_alert(self, alert: Alert) -> None:
        if alert.level == AlertLevel.CRITICAL:
            self.trip(f"Critical alert triggered: {alert.message}")

    def check_daily_pnl(self, current_daily_pnl: float) -> bool:
        if current_daily_pnl <= -self.max_daily_loss:
            self.trip(
                f"Max daily loss reached ({current_daily_pnl:.2f} <= -{self.max_daily_loss:.2f})"
            )
            return True
        return False

    def reset(self) -> None:
        self.status = CircuitBreakerStatus.ARMED
        self.trip_reason = None