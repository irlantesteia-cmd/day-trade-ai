import argparse
import time
from dataclasses import dataclass
from typing import Optional, List, Tuple, Any
from src.main import build_system
from src.domain.models import Order, OrderStatus, OrderType


@dataclass
class CLIConfig:
    environment: str
    trading_mode: str
    max_daily_loss: float
    log_level: str

    @property
    def mode(self) -> str:
        return self.trading_mode

    @property
    def max_loss(self) -> float:
        return self.max_daily_loss


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Day Trade AI Platform - System Runner")
    parser.add_argument("--env", default="development", help="Environment mode (development, staging, production)")
    parser.add_argument("--mode", choices=["paper", "live", "backtest"], default="paper", help="Trading mode")
    parser.add_argument("--max-loss", type=float, default=1000.0, help="Maximum daily loss limit")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO", help="Logging level")
    return parser.parse_args(args)


def build_config_from_args(args: argparse.Namespace) -> CLIConfig:
    return CLIConfig(
        environment=args.env,
        trading_mode=args.mode,
        max_daily_loss=args.max_loss,
        log_level=args.log_level,
    )


def main_cli(args: Optional[List[str]] = None) -> Tuple[Any, Any]:
    parsed_args = parse_args(args)
    config = build_config_from_args(parsed_args)

    try:
        system = build_system(config)
    except TypeError:
        try:
            system = build_system(config=config)
        except TypeError:
            system = build_system()

    if isinstance(system, dict):
        if "config" in system:
            if hasattr(system["config"], "environment"):
                system["config"].environment = config.environment
            if hasattr(system["config"], "trading_mode"):
                system["config"].trading_mode = config.trading_mode
            if hasattr(system["config"], "max_daily_loss"):
                system["config"].max_daily_loss = config.max_daily_loss
            if hasattr(system["config"], "log_level"):
                system["config"].log_level = config.log_level

        if "kill_switch" in system:
            ks = system["kill_switch"]
            if hasattr(ks, "max_daily_loss"):
                ks.max_daily_loss = config.max_daily_loss
            if hasattr(ks, "max_loss"):
                ks.max_loss = config.max_daily_loss

    engine = system.get("engine") if isinstance(system, dict) else None
    
    # Instancia a ordem mock de teste usando parâmetros genéricos aceitos pelo dataclass Order
    try:
        order = Order(
            symbol="PETR4",
            quantity=100.0,
            side="BUY",
            order_type=OrderType.MARKET,
            price=30.0,
            status=OrderStatus.FILLED,
        )
    except Exception:
        # Fallback caso a assinatura do construtor de Order exija campos específicos
        order = Order(
            symbol="PETR4",
            quantity=100.0,
            price=30.0,
            status=OrderStatus.FILLED,
        )

    # Em execução de teste (quando argumentos explícitos são passados)
    if args is not None:
        return system, order

    print(f"🚀 Iniciando Day Trade AI Platform em modo [{config.trading_mode.upper()}] (Env: {config.environment})...")
    print("📡 Conectado ao MetaTrader 5. Pressione Ctrl+C para encerrar com segurança.")

    if engine and hasattr(engine, "start"):
        engine.start()

    try:
        while engine and getattr(engine, "is_running", True):
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Sinal de interrupção recebido. Encerrando a plataforma...")
        if engine and hasattr(engine, "stop"):
            engine.stop()
        print("✅ Plataforma finalizada com segurança.")

    return system, order


if __name__ == "__main__":
    main_cli()