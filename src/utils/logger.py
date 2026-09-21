import json
import logging
import sys
from datetime import datetime, timezone


class StructuredLogger:
    def __init__(self, name: str = "DayTradeAI", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self.logger.handlers.clear()

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)

    def _format_event(
        self,
        level: str,
        event_type: str,
        component: str,
        message: str,
        details: dict | None = None,
        correlation_id: str | None = None,
    ) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event_type": event_type,
            "component": component,
            "message": message,
            "correlation_id": correlation_id,
            "details": details or {},
        }
        return json.dumps(payload)

    def info(
        self,
        event_type: str,
        component: str,
        message: str,
        details: dict | None = None,
        correlation_id: str | None = None,
    ) -> None:
        formatted = self._format_event(
            "INFO", event_type, component, message, details, correlation_id
        )
        self.logger.info(formatted)

    def warning(
        self,
        event_type: str,
        component: str,
        message: str,
        details: dict | None = None,
        correlation_id: str | None = None,
    ) -> None:
        formatted = self._format_event(
            "WARNING", event_type, component, message, details, correlation_id
        )
        self.logger.warning(formatted)

    def error(
        self,
        event_type: str,
        component: str,
        message: str,
        details: dict | None = None,
        correlation_id: str | None = None,
    ) -> None:
        formatted = self._format_event(
            "ERROR", event_type, component, message, details, correlation_id
        )
        self.logger.error(formatted)


logger = StructuredLogger()