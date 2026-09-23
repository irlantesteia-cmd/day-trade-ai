"""
Model Registry para versionamento e rastreabilidade de modelos treinados.

Metadados por modelo (framework secao 21):
  - model_id
  - model_version
  - dataset_version
  - feature_version
  - feature_keys
  - training_period / validation_period
  - parameters / metrics
  - created_at

Layout em disco:
  models/registry/
    <model_id>__<model_version>/
      model.pkl
      metadata.json
"""
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import joblib


@dataclass
class ModelMetadata:
    model_id: str
    model_version: str
    dataset_version: str
    feature_version: str
    feature_keys: List[str]
    training_period: Tuple[str, str]
    validation_period: Optional[Tuple[str, str]] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    notes: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ModelMetadata":
        # tuples serializam como listas em JSON; converter de volta
        if "training_period" in d and isinstance(d["training_period"], list):
            d["training_period"] = tuple(d["training_period"])
        if d.get("validation_period") and isinstance(d["validation_period"], list):
            d["validation_period"] = tuple(d["validation_period"])
        return cls(**d)


class ModelRegistry:
    def __init__(self, root_dir: str = "models/registry") -> None:
        self.root_dir = root_dir
        os.makedirs(self.root_dir, exist_ok=True)

    def _entry_dir(self, model_id: str, model_version: str) -> str:
        return os.path.join(self.root_dir, f"{model_id}__{model_version}")

    def save(
        self,
        model: Any,
        metadata: ModelMetadata,
        model_filename: str = "model.pkl",
    ) -> str:
        entry = self._entry_dir(metadata.model_id, metadata.model_version)
        os.makedirs(entry, exist_ok=True)

        model_path = os.path.join(entry, model_filename)
        joblib.dump(model, model_path)

        meta_path = os.path.join(entry, "metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)

        return entry

    def load(self, model_id: str, model_version: str) -> Tuple[Any, ModelMetadata]:
        entry = self._entry_dir(model_id, model_version)
        model_path = os.path.join(entry, "model.pkl")
        meta_path = os.path.join(entry, "metadata.json")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo nao encontrado: {model_path}")
        if not os.path.exists(meta_path):
            raise FileNotFoundError(f"Metadados nao encontrados: {meta_path}")

        model = joblib.load(model_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = ModelMetadata.from_dict(json.load(f))

        return model, metadata

    def list_models(self) -> List[Tuple[str, str]]:
        if not os.path.isdir(self.root_dir):
            return []
        entries = []
        for name in sorted(os.listdir(self.root_dir)):
            full = os.path.join(self.root_dir, name)
            if not os.path.isdir(full):
                continue
            if "__" not in name:
                continue
            model_id, model_version = name.split("__", 1)
            entries.append((model_id, model_version))
        return entries

    def get_metadata(self, model_id: str, model_version: str) -> ModelMetadata:
        entry = self._entry_dir(model_id, model_version)
        meta_path = os.path.join(entry, "metadata.json")
        if not os.path.exists(meta_path):
            raise FileNotFoundError(f"Metadados nao encontrados: {meta_path}")
        with open(meta_path, "r", encoding="utf-8") as f:
            return ModelMetadata.from_dict(json.load(f))

    def exists(self, model_id: str, model_version: str) -> bool:
        return os.path.exists(
            os.path.join(self._entry_dir(model_id, model_version), "metadata.json")
        )

    def delete(self, model_id: str, model_version: str) -> None:
        entry = self._entry_dir(model_id, model_version)
        if not os.path.isdir(entry):
            raise FileNotFoundError(f"Entrada nao existe: {entry}")
        for f in os.listdir(entry):
            os.remove(os.path.join(entry, f))
        os.rmdir(entry)