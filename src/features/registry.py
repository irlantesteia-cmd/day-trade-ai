from typing import Dict, Type
from src.features.base import FeatureExtractor


class FeatureRegistry:
    def __init__(self) -> None:
        self._registry: Dict[str, Type[FeatureExtractor]] = {}

    def register(self, name: str, extractor_cls: Type[FeatureExtractor]) -> None:
        self._registry[name.upper()] = extractor_cls

    def get(self, name: str, **kwargs) -> FeatureExtractor:
        name_upper = name.upper()
        if name_upper not in self._registry:
            raise KeyError(f"Extrator '{name}' não registrado no FeatureRegistry.")
        return self._registry[name_upper](**kwargs)

    def list_available(self) -> list[str]:
        return list(self._registry.keys())