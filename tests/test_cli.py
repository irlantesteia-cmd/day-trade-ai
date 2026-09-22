import pytest
from src.cli.runner import parse_args, build_config_from_args, main_cli
from src.domain.enums import OrderStatus


def test_parse_args_defaults():
    args = parse_args([])
    assert args.env == "development"
    assert args.mode == "paper"
    assert args.max_loss == 1000.0
    assert args.log_level == "INFO"


def test_build_config_from_custom_args():
    raw_args = ["--env", "production", "--mode", "live", "--max-loss", "3000.0", "--log-level", "DEBUG"]
    parsed = parse_args(raw_args)
    config = build_config_from_args(parsed)

    assert config.environment == "production"
    assert config.trading_mode == "live"
    assert config.max_daily_loss == 3000.0
    assert config.log_level == "DEBUG"


def test_main_cli_execution():
    raw_args = ["--mode", "paper", "--max-loss", "1500.0"]
    system, order = main_cli(raw_args)

    assert system["config"].max_daily_loss == 1500.0
    assert system["kill_switch"].max_daily_loss == 1500.0
    assert order is not None
    assert order.status == OrderStatus.FILLED