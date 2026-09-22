from typing import Dict, Any, Tuple, Optional
from src.adapters.mt5_adapter import MT5Adapter
from src.config.settings import AppConfig
from src.domain.enums import OrderStatus, SignalDirection
from src.domain.models import Order, Signal
from src.engine.kill_switch import KillSwitch
from src.engine.live_engine import LiveTradingEngine
from src.engine.mt5_bridge import MT5ExecutionEngine
from src.telemetry.alerts import AlertManager
from src.telemetry.collector import MetricsCollector
from src.telemetry.health import SystemHealthMonitor


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


def build_system(config: Optional[AppConfig] = None, use_mt5: bool = False) -> Dict[str, Any]:
    cfg = config or AppConfig.from_env()

    metrics = MetricsCollector()
    health = SystemHealthMonitor(metrics)
    alerts = AlertManager()
    strategy = DummyStrategy()

    if use_mt5 or cfg.trading_mode in ["live", "paper_mt5"]:
        mt5_adapter = MT5Adapter()
        mt5_adapter.initialize()
        execution = MT5ExecutionEngine(adapter=mt5_adapter)
    else:
        execution = DummyExecutionEngine()

    engine = LiveTradingEngine(
        strategy=strategy,
        risk_manager=None,
        execution_engine=execution,
        metrics_collector=metrics,
        health_monitor=health,
    )

    kill_switch = KillSwitch(engine, max_daily_loss=cfg.max_daily_loss)
    alerts.register_handler(kill_switch.handle_alert)

    return {
        "config": cfg,
        "metrics": metrics,
        "health": health,
        "alerts": alerts,
        "engine": engine,
        "kill_switch": kill_switch,
    }


def run_app(config: Optional[AppConfig] = None, use_mt5: bool = False) -> Tuple[Dict[str, Any], Any]:
    system = build_system(config, use_mt5=use_mt5)
    engine = system["engine"]
    engine.start()

    sample_bar = {"symbol": "WIN", "close": 105.0}
    order = engine.process_bar(sample_bar)
    return system, order


if __name__ == "__main__":
    run_app()