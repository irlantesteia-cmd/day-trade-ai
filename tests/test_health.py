from datetime import datetime, timezone, timedelta
import pytest
from src.telemetry.collector import MetricsCollector
from src.telemetry.health import SystemHealthMonitor, HealthStatus


def test_health_monitor_healthy():
    collector = MetricsCollector()
    monitor = SystemHealthMonitor(collector, max_latency_ms=100.0, max_error_rate=0.1)
    monitor.record_heartbeat()

    collector.increment_counter("total_operations", 100)
    collector.increment_counter("total_errors", 1)
    collector.record_latency("execution_time", 20.0)

    res = monitor.check_health()
    assert res["status"] == HealthStatus.HEALTHY.value
    assert len(res["reasons"]) == 0


def test_health_monitor_stale_heartbeat():
    collector = MetricsCollector()
    monitor = SystemHealthMonitor(collector, stale_heartbeat_sec=5.0)

    past_time = datetime.now(timezone.utc) - timedelta(seconds=10)
    monitor.record_heartbeat(past_time)

    res = monitor.check_health()
    assert res["status"] == HealthStatus.UNHEALTHY.value
    assert any("Heartbeat stale" in r for r in res["reasons"])


def test_health_monitor_high_latency_and_error_rate():
    collector = MetricsCollector()
    monitor = SystemHealthMonitor(collector, max_latency_ms=50.0, max_error_rate=0.05)
    monitor.record_heartbeat()

    collector.record_latency("execution_time", 150.0)
    collector.increment_counter("total_operations", 10)
    collector.increment_counter("total_errors", 2)

    res = monitor.check_health()
    assert res["status"] == HealthStatus.UNHEALTHY.value
    assert len(res["reasons"]) == 2