import time
from typing import Dict, Any, List, Optional
from collections import defaultdict


class MetricsCollector:
    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._latencies: Dict[str, List[float]] = defaultdict(list)

    def increment_counter(self, name: str, value: float = 1.0) -> None:
        self._counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        self._gauges[name] = float(value)

    def record_latency(self, name: str, duration_ms: float) -> None:
        self._latencies[name].append(float(duration_ms))

    def get_counter(self, name: str) -> float:
        return self._counters.get(name, 0.0)

    def get_gauge(self, name: str) -> Optional[float]:
        return self._gauges.get(name)

    def get_latency_stats(self, name: str) -> Dict[str, float]:
        records = self._latencies.get(name, [])
        if not records:
            return {"count": 0, "avg": 0.0, "min": 0.0, "max": 0.0, "p95": 0.0}

        sorted_records = sorted(records)
        count = len(sorted_records)
        avg = sum(sorted_records) / count
        p95_idx = int(count * 0.95) - 1 if count >= 20 else count - 1
        p95 = sorted_records[max(0, p95_idx)]

        return {
            "count": count,
            "avg": round(avg, 3),
            "min": round(sorted_records[0], 3),
            "max": round(sorted_records[-1], 3),
            "p95": round(p95, 3),
        }

    def summary(self) -> Dict[str, Any]:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "latencies": {k: self.get_latency_stats(k) for k in self._latencies},
        }

    def reset(self) -> None:
        self._counters.clear()
        self._gauges.clear()
        self._latencies.clear()