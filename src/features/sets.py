"""
Feature Sets nomeados e versionados.

Um FeatureSet agrupa extratores de features sob um nome+versao unicos,
permitindo que datasets e modelos referenciem qual conjunto foi usado.

Tambem fornece um helper para converter uma serie de Candles em uma lista
de records (dicts) compativel com o DatasetBuilder.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.domain.models import Candle
from src.features.base import FeatureExtractor
from src.features.pipeline import FeaturePipeline
from src.features.price_action import (
    CandleMorphologyExtractor,
    LogReturnExtractor,
)
from src.features.temporal import TimeOfDayExtractor


# ---------------------------------------------------------------------------
# FeatureSet
# ---------------------------------------------------------------------------

@dataclass
class FeatureSet:
    name: str
    version: str
    extractors: List[FeatureExtractor] = field(default_factory=list)
    description: str = ""

    @property
    def feature_keys(self) -> List[str]:
        """Nomes das features que este conjunto gera, em ordem deterministica."""
        keys: List[str] = []
        for ext in self.extractors:
            probe = ext.extract([], None)
            keys.extend(probe.keys())
        return keys

    def build_pipeline(self) -> FeaturePipeline:
        pipe = FeaturePipeline()
        for ext in self.extractors:
            pipe.add_extractor(ext)
        return pipe


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class FeatureSetRegistry:
    def __init__(self) -> None:
        self._registry: Dict[Tuple[str, str], FeatureSet] = {}

    def register(self, fs: FeatureSet) -> None:
        self._registry[(fs.name, fs.version)] = fs

    def get(self, name: str, version: str) -> FeatureSet:
        key = (name, version)
        if key not in self._registry:
            raise KeyError(f"FeatureSet '{name}' v{version} nao registrado.")
        return self._registry[key]

    def list_available(self) -> List[Tuple[str, str]]:
        return sorted(self._registry.keys())


# ---------------------------------------------------------------------------
# Feature Sets builtin
# ---------------------------------------------------------------------------

def basic_v1() -> FeatureSet:
    """Conjunto sem dependencia de indicadores. 9 features."""
    return FeatureSet(
        name="basic",
        version="v1",
        extractors=[
            LogReturnExtractor(period=1),
            LogReturnExtractor(period=2),
            LogReturnExtractor(period=3),
            LogReturnExtractor(period=5),
            CandleMorphologyExtractor(),
            TimeOfDayExtractor(),
        ],
        description="Log returns (1/2/3/5) + candle morphology + time of day",
    )


def register_default_sets(registry: FeatureSetRegistry) -> None:
    registry.register(basic_v1())


# ---------------------------------------------------------------------------
# Helper: serie de candles -> records
# ---------------------------------------------------------------------------

def records_from_candles(
    candles: List[Candle],
    feature_set: FeatureSet,
    min_history: int = 6,
) -> List[Dict[str, Any]]:
    """
    Aplica o feature set a cada candle (a partir de min_history) usando
    apenas candles anteriores (sem look-ahead).

    Retorna lista de dicts com:
      - timestamp, open, high, low, close, volume
      - todas as features do feature set
    """
    if not candles:
        return []

    pipeline = feature_set.build_pipeline()
    records: List[Dict[str, Any]] = []

    for i in range(min_history, len(candles)):
        window = candles[: i + 1]
        feats = pipeline.extract_all(window, indicator_results=None)

        rec: Dict[str, Any] = {
            "timestamp": candles[i].timestamp,
            "open": candles[i].open,
            "high": candles[i].high,
            "low": candles[i].low,
            "close": candles[i].close,
            "volume": candles[i].volume,
        }
        rec.update(feats)
        records.append(rec)

    return records