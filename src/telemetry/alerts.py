from enum import Enum
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime, timezone


class AlertLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class Alert:
    def __init__(
        self,
        level: AlertLevel,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.level = level
        self.message = message
        self.details = details or {}
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class AlertManager:
    def __init__(self):
        self._handlers: List[Callable[[Alert], None]] = []
        self._history: List[Alert] = []

    def register_handler(self, handler: Callable[[Alert], None]) -> None:
        self._handlers.append(handler)

    def trigger_alert(
        self,
        level: AlertLevel,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Alert:
        alert = Alert(level=level, message=message, details=details)
        self._history.append(alert)
        for handler in self._handlers:
            try:
                handler(alert)
            except Exception:
                pass
        return alert

    def evaluate_health(self, health_data: Dict[str, Any]) -> List[Alert]:
        alerts = []
        status = health_data.get("status")
        reasons = health_data.get("reasons", [])

        if status == "UNHEALTHY":
            for reason in reasons:
                alert = self.trigger_alert(
                    level=AlertLevel.CRITICAL,
                    message=f"System Unhealthy: {reason}",
                    details=health_data,
                )
                alerts.append(alert)
        elif status == "DEGRADED":
            for reason in reasons:
                alert = self.trigger_alert(
                    level=AlertLevel.WARNING,
                    message=f"System Degraded: {reason}",
                    details=health_data,
                )
                alerts.append(alert)

        return alerts

    def get_history(self) -> List[Alert]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()