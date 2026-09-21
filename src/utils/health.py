from enum import Enum
from typing import Any, Dict


class SystemState(str, Enum):
    STARTING = "STARTING"
    READY = "READY"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class HealthChecker:
    def __init__(self) -> None:
        self._state = SystemState.STARTING

    @property
    def state(self) -> SystemState:
        return self._state

    def set_state(self, new_state: SystemState) -> None:
        self._state = new_state

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": self._state.value,
            "healthy": self._state in [SystemState.READY, SystemState.RUNNING],
        }