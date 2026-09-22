import argparse
from typing import List, Optional, Tuple, Dict, Any
from src.config.settings import AppConfig
from src.main import run_app


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Day Trade AI Platform - System Runner"
    )
    parser.add_argument(
        "--env",
        type=str,
        default="development",
        help="Environment mode (development, staging, production)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="paper",
        choices=["paper", "live", "backtest"],
        help="Trading mode (paper, live, backtest)",
    )
    parser.add_argument(
        "--max-loss",
        type=float,
        default=1000.0,
        help="Maximum daily loss limit",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity level",
    )
    return parser.parse_args(args)


def build_config_from_args(cli_args: argparse.Namespace) -> AppConfig:
    return AppConfig(
        environment=cli_args.env,
        trading_mode=cli_args.mode,
        max_daily_loss=cli_args.max_loss,
        log_level=cli_args.log_level,
    )


def main_cli(args: Optional[List[str]] = None) -> Tuple[Dict[str, Any], Any]:
    parsed = parse_args(args)
    config = build_config_from_args(parsed)
    return run_app(config)


if __name__ == "__main__":
    main_cli()