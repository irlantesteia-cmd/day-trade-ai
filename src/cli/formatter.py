from typing import Dict, Any


class StatusFormatter:
    @staticmethod
    def format_summary(system_dict: Dict[str, Any]) -> str:
        config = system_dict.get("config")
        engine = system_dict.get("engine")
        kill_switch = system_dict.get("kill_switch")
        metrics = system_dict.get("metrics")

        env = str(getattr(config, "environment", "N/A"))
        mode = str(getattr(config, "trading_mode", "N/A"))
        engine_running = getattr(engine, "is_running", False)
        ks_status = getattr(kill_switch, "status", "N/A")
        
        bars = metrics.get_counter("bars_processed") if metrics else 0.0
        orders = metrics.get_counter("orders_executed") if metrics else 0.0

        lines = [
            "==================================================",
            "          DAY TRADE AI PLATFORM STATUS            ",
            "==================================================",
            f" Environment    : {env.upper()}",
            f" Trading Mode   : {mode.upper()}",
            f" Engine Running : {engine_running}",
            f" Kill Switch    : {ks_status}",
            "--------------------------------------------------",
            " Metrics:",
            f"   - Bars Processed : {int(bars)}",
            f"   - Orders Executed: {int(orders)}",
            "==================================================",
        ]
        return "\n".join(lines)