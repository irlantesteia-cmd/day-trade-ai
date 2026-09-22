import pytest
from src.telemetry.collector import MetricsCollector


def test_metrics_collector_counters():
    collector = MetricsCollector()
    collector.increment_counter("signals_generated", 1.0)
    collector.increment_counter("signals_generated", 2.0)

    assert collector.get_counter("signals_generated") == 3.0
    assert collector.get_counter("non_existent") == 0.0


def test_metrics_collector_gauges():
    collector = MetricsCollector()
    collector.set_gauge("portfolio_equity", 10500.50)
    collector.set_gauge("portfolio_equity", 10800.00)

    assert collector.get_gauge("portfolio_equity") == 10800.00
    assert collector.get_gauge("unregistered") is None


def test_metrics_collector_latencies_and_summary():
    collector = MetricsCollector()
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0]
    for lat in latencies:
        collector.record_latency("execution_time", lat)

    stats = collector.get_latency_stats("execution_time")
    assert stats["count"] == 5
    assert stats["avg"] == 30.0
    assert stats["min"] == 10.0
    assert stats["max"] == 50.0

    summary = collector.summary()
    assert "execution_time" in summary["latencies"]

    collector.reset()
    assert collector.get_counter("signals_generated") == 0.0
    assert collector.get_gauge("portfolio_equity") is None
    assert collector.get_latency_stats("execution_time")["count"] == 0