from typing import Dict, Any, Optional
from src.analytics.exporter import ExecutiveReportExporter
from src.analytics.reporter import PerformanceReporter
from src.main import build_system


class APIGateway:
    """
    Gateway REST de servicos para telemetria, saude do sistema e relatorios executivos.
    """

    def __init__(self, system_components: Optional[Dict[str, Any]] = None):
        self.system = system_components or build_system()
        self.reporter = PerformanceReporter()
        self.exporter = ExecutiveReportExporter()

    def get_health(self) -> Dict[str, Any]:
        """
        Retorna o estado de saude dos componentes do sistema.
        """
        health_monitor = self.system.get("health")
        if health_monitor and hasattr(health_monitor, "check_health"):
            return health_monitor.check_health()
        return {"status": "OK", "components": {}}

    def get_metrics(self) -> Dict[str, Any]:
        """
        Retorna o resumo de metricas coletadas pela telemetria.
        """
        metrics_collector = self.system.get("metrics")
        if metrics_collector and hasattr(metrics_collector, "get_summary"):
            return metrics_collector.get_summary()
        return {}

    def get_performance_report(self, format_type: str = "json") -> Dict[str, Any]:
        """
        Gera e retorna o relatorio de performance no formato solicitado (json ou markdown).
        """
        auditor = self.system.get("auditor")
        trade_history = auditor.trade_history if auditor else []
        report_data = self.reporter.generate_report(trade_history)

        if format_type == "markdown":
            return {
                "content": self.exporter.export_to_markdown(report_data),
                "format": "markdown",
            }
        return {
            "content": report_data,
            "format": "json",
        }