import argparse
import time
from dataclasses import dataclass
from typing import Optional, List, Tuple, Any

from src.main import build_system
from src.adapters.mt5_adapter import MT5Adapter
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
    parser.add_argument("--env", default="development",
                        help="Environment (development, staging, production)")
    parser.add_argument(
        "--mode",
        choices=["paper", "paper_mt5", "live", "backtest"],
        default="paper",
        help="paper = simula ordens localmente | paper_mt5 = envia p/ demo MT5 | live = real",
    )
    parser.add_argument("--max-loss", type=float, default=1000.0,
                        help="Limite de perda diaria")
    parser.add_argument("--log-level",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        default="INFO")
    parser.add_argument("--symbol", default="WIN$",
                        help="Ativo a operar (default: WIN$)")
    parser.add_argument("--poll-interval", type=float, default=2.0,
                        help="Segundos entre polls de barra")
    return parser.parse_args(args)


def build_config_from_args(args: argparse.Namespace) -> CLIConfig:
    return CLIConfig(
        environment=args.env,
        trading_mode=args.mode,
        max_daily_loss=args.max_loss,
        log_level=args.log_level,
    )


def main_cli(args: Optional[List[str]] = None) -> Tuple[Any, Any]:
    parsed = parse_args(args)
    config = build_config_from_args(parsed)

    use_mt5 = parsed.mode in ("paper_mt5", "live")
    system = build_system(config, use_mt5=use_mt5)

    if isinstance(system, dict):
        if "config" in system:
            cfg = system["config"]
            for attr in ("environment", "trading_mode", "max_daily_loss", "log_level"):
                if hasattr(cfg, attr):
                    setattr(cfg, attr, getattr(config, attr))
        if "kill_switch" in system:
            ks = system["kill_switch"]
            if hasattr(ks, "max_daily_loss"):
                ks.max_daily_loss = config.max_daily_loss

    engine = system.get("engine") if isinstance(system, dict) else None

    order = None
    try:
        order = Order(symbol="PETR4", quantity=100.0, side="BUY",
                      order_type=OrderType.MARKET, price=30.0,
                      status=OrderStatus.FILLED)
    except Exception:
        try:
            order = Order(symbol="PETR4", quantity=100.0, price=30.0,
                          status=OrderStatus.FILLED)
        except Exception:
            order = None

    # Chamada programatica (testes): retorna sem iniciar loop
    if args is not None:
        return system, order

    # === Execucao interativa ===
    symbol = parsed.symbol
    poll_interval = max(0.5, parsed.poll_interval)

    print("=" * 60)
    print(f"Day Trade AI Platform | modo [{config.trading_mode.upper()}]")
    print(f"   Env     : {config.environment}")
    print(f"   Simbolo : {symbol}")
    print(f"   Poll    : {poll_interval}s")
    print(f"   Exec MT5: {'ATIVA (demo/live)' if use_mt5 else 'SIMULADA (Dummy)'}")
    print(f"   Log     : {config.log_level}")
    print("=" * 60)

    bar_adapter = MT5Adapter()
    if not bar_adapter.initialize():
        print("Falha ao inicializar MT5 para leitura de barras. Abortando.")
        return system, order

    print("Conectado ao MetaTrader 5. Pressione Ctrl+C para encerrar.\n")

    if engine and hasattr(engine, "start"):
        engine.start()

    last_timestamp = None
    bars_processed = 0
    orders_executed = 0

    try:
        while engine and getattr(engine, "is_running", True):
            try:
                bar = bar_adapter.fetch_latest_bar(symbol)
            except Exception as exc:
                print(f"Erro ao buscar barra: {exc}")
                time.sleep(poll_interval)
                continue

            if not bar:
                time.sleep(poll_interval)
                continue

            ts = bar.get("timestamp")
            if ts == last_timestamp:
                time.sleep(poll_interval)
                continue

            last_timestamp = ts
            bars_processed += 1

            print(
                f"[{bars_processed}] {symbol} @ {ts} | "
                f"O={bar['open']:.2f} H={bar['high']:.2f} "
                f"L={bar['low']:.2f} C={bar['close']:.2f} "
                f"V={bar['volume']:.0f}"
            )

            try:
                result = engine.process_bar(bar)
            except Exception as exc:
                print(f"Erro ao processar barra: {exc}")
                result = None

            if result is not None:
                orders_executed += 1
                print(f"   Ordem executada: {result}")

            time.sleep(poll_interval)

    except KeyboardInterrupt:
        print("\nInterrupcao recebida. Encerrando...")
    finally:
        if engine and hasattr(engine, "stop"):
            engine.stop()
        bar_adapter.shutdown()
        print(f"\nTotal: {bars_processed} barras | {orders_executed} ordens")
        print("Plataforma finalizada com seguranca.")

    return system, order


if __name__ == "__main__":
    main_cli()