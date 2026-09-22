from typing import Dict, Any, Tuple
from src.domain.enums import OrderStatus
from src.domain.models import Order, Signal
from src.domain.enums import SignalDirection
from src.telemetry.collector import MetricsCollector
from src.telemetry.health import SystemHealthMonitor
from src.telemetry.alerts import AlertManager
from src.engine.live_engine import LiveTradingEngine
from src.engine.kill_switch import KillSwitch


class DummyStrategy:
    def generate_signal(self, bar: Dict[str, Any]) -> Any:
        if bar.get("close", 0) > 100.0:
            return Signal(
                symbol=bar.get("symbol", "WIN"),
                direction=SignalDirection.BUY,
                confidence=0.85,
                metadata={"price": bar.get("close")},
            )
        return None


class DummyExecutionEngine:
    def execute_signal(self, signal: Any, bar: Dict[str, Any]) -> Order:
        return Order(
            symbol=signal.symbol,
            direction=signal.direction,
            quantity=1.0,
            price=bar.get("close", 100.0),
            status=OrderStatus.FILLED,
        )


def build_system() -> Dict[str, Any]:
    metrics = MetricsCollector()
    health = SystemHealthMonitor(metrics)
    alerts = AlertManager()
    strategy = DummyStrategy()
    execution = DummyExecutionEngine()

    engine = LiveTradingEngine(
        strategy=strategy,
        risk_manager=None,
        execution_engine=execution,
        metrics_collector=metrics,
        health_monitor=health,
    )

    kill_switch = KillSwitch(engine)
    alerts.register_handler(kill_switch.handle_alert)

    return {
        "metrics": metrics,
        "health": health,
        "alerts": alerts,
        "engine": engine,
        "kill_switch": kill_switch,
    }


def run_app() -> Tuple[Dict[str, Any], Any]:
    system = build_system()
    engine = system["engine"]
    engine.start()

    sample_bar = {"symbol": "WIN", "close": 105.0}
    order = engine.process_bar(sample_bar)
    return system, order


if __name__ == "__main__":
    run_app()