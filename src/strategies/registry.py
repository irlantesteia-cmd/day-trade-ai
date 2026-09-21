from typing import Dict, Type
from src.strategies.base import Strategy


class StrategyRegistry:
    def __init__(self) -> None:
        self._registry: Dict[str, Type[Strategy]] = {}

    def register(self, name: str, strategy_cls: Type[Strategy]) -> None:
        self._registry[name.upper()] = strategy_cls

    def get(self, name: str, **kwargs) -> Strategy:
        name_upper = name.upper()
        if name_upper not in self._registry:
            raise KeyError(f"Estratégia '{name}' não encontrada no StrategyRegistry.")
        return self._registry[name_upper](**kwargs)

    def list_available(self) -> list[str]:
        return list(self._registry.keys())