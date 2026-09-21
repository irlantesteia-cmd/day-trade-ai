from typing import Dict, Type
from src.indicators.base import Indicator


class IndicatorRegistry:
    def __init__(self) -> None:
        self._registry: Dict[str, Type[Indicator]] = {}

    def register(self, name: str, indicator_cls: Type[Indicator]) -> None:
        self._registry[name.upper()] = indicator_cls

    def get(self, name: str, **kwargs) -> Indicator:
        name_upper = name.upper()
        if name_upper not in self._registry:
            raise KeyError(f"Indicador '{name}' não está registrado no IndicatorRegistry.")
        return self._registry[name_upper](**kwargs)

    def list_available(self) -> list[str]:
        return list(self._registry.keys())