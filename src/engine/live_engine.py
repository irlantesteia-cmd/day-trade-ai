import time
from typing import Dict, Any, Optional
from src.domain.models import Order
from src.telemetry.collector import MetricsCollector
from src.telemetry.health import SystemHealthMonitor


class LiveTradingEngine:
    def __init__(
        self,
        strategy: Any,
        risk_manager: Any,
        execution_engine: Any,
        metrics_collector: Optional[MetricsCollector] = None,
        health_monitor: Optional[SystemHealthMonitor] = None,
    ):
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.execution_engine = execution_engine
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.health_monitor = health_monitor or SystemHealthMonitor(self.metrics_collector)
        self.is_running = False

    def start(self) -> None:
        self.is_running = True
        self.health_monitor.record_heartbeat()

    def stop(self) -> None:
        self.is_running = False

    def process_bar(self, bar: Dict[str, Any]) -> Optional[Order]:
        if not self.is_running:
            return None

        start_time = time.perf_counter()
        self.health_monitor.record_heartbeat()
        self.metrics_collector.increment_counter("bars_processed", 1.0)

        # 1. Geração do Sinal
        signal = self.strategy.generate_signal(bar)
        if not signal:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            self.metrics_collector.record_latency("execution_time", duration_ms)
            return None

        self.metrics_collector.increment_counter("signals_generated", 1.0)

        # 2. Validação pelo Gerenciador de Risco
        is_approved = True
        if hasattr(self.risk_manager, "validate_signal"):
            is_approved = self.risk_manager.validate_signal(signal)

        if not is_approved:
            self.metrics_collector.increment_counter("signals_rejected_risk", 1.0)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            self.metrics_collector.record_latency("execution_time", duration_ms)
            return None

        # 3. Envio da Ordem para Execução
        order = None
        try:
            order = self.execution_engine.execute_signal(signal, bar)
            self.metrics_collector.increment_counter("orders_executed", 1.0)
        except Exception:
            self.metrics_collector.increment_counter("total_errors", 1.0)
            raise
        finally:
            self.metrics_collector.increment_counter("total_operations", 1.0)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            self.metrics_collector.record_latency("execution_time", duration_ms)

        return order