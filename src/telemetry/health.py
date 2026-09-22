from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from src.telemetry.collector import MetricsCollector


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


class SystemHealthMonitor:
    def __init__(
        self,
        metrics_collector: MetricsCollector,
        max_latency_ms: float = 500.0,
        max_error_rate: float = 0.05,
        stale_heartbeat_sec: float = 30.0,
    ):
        self.collector = metrics_collector
        self.max_latency_ms = max_latency_ms
        self.max_error_rate = max_error_rate
        self.stale_heartbeat_sec = stale_heartbeat_sec
        self._last_heartbeat: Optional[datetime] = None

    def record_heartbeat(self, timestamp: Optional[datetime] = None) -> None:
        self._last_heartbeat = timestamp or datetime.now(timezone.utc)

    def check_health(self) -> Dict[str, Any]:
        status = HealthStatus.HEALTHY
        reasons: List[str] = []

        # 1. Checagem de Staleness do Heartbeat
        if self._last_heartbeat is None:
            status = HealthStatus.DEGRADED
            reasons.append("No heartbeat recorded")
        else:
            now = datetime.now(timezone.utc)
            hb_ts = self._last_heartbeat
            if hb_ts.tzinfo is None:
                hb_ts = hb_ts.replace(tzinfo=timezone.utc)
            elapsed = (now - hb_ts).total_seconds()
            if elapsed > self.stale_heartbeat_sec:
                status = HealthStatus.UNHEALTHY
                reasons.append(f"Heartbeat stale ({elapsed:.1f}s > {self.stale_heartbeat_sec}s)")

        # 2. Checagem de Latência de Execução
        latency_stats = self.collector.get_latency_stats("execution_time")
        if latency_stats["count"] > 0 and latency_stats["avg"] > self.max_latency_ms:
            if status != HealthStatus.UNHEALTHY:
                status = HealthStatus.DEGRADED
            reasons.append(f"High execution latency avg ({latency_stats['avg']}ms > {self.max_latency_ms}ms)")

        # 3. Checagem da Taxa de Erros
        total_ops = self.collector.get_counter("total_operations")
        total_errors = self.collector.get_counter("total_errors")
        if total_ops > 0:
            error_rate = total_errors / total_ops
            if error_rate > self.max_error_rate:
                status = HealthStatus.UNHEALTHY
                reasons.append(f"High error rate ({error_rate:.1%} > {self.max_error_rate:.1%})")

        return {
            "status": status.value,
            "reasons": reasons,
            "last_heartbeat": self._last_heartbeat.isoformat() if self._last_heartbeat else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }