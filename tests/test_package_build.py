import importlib.metadata
import pytest
from src.cli.runner import main_cli


def test_cli_entrypoint_importable():
    # Garante que a funcao de entrada configurada no script da CLI existe e e invocavel
    assert callable(main_cli)


def test_package_structure_integrity():
    import src.main
    import src.config
    import src.cli
    import src.engine

    assert hasattr(src.main, "run_app")
    assert hasattr(src.config, "AppConfig")
    assert hasattr(src.cli, "main_cli")
    assert hasattr(src.engine, "LiveTradingEngine")