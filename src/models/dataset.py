from typing import List, Dict, Any


class MLDataset:
    def __init__(self, X: List[List[float]], y: List[int], feature_names: List[str]):
        self.X = X
        self.y = y
        self.feature_names = feature_names


class DatasetBuilder:
    def __init__(self, target_horizon: int = 1, threshold: float = 0.0):
        if target_horizon < 1:
            raise ValueError("target_horizon must be at least 1")
        self.target_horizon = target_horizon
        self.threshold = threshold

    def build_binary_classification_dataset(
        self,
        records: List[Dict[str, Any]],
        feature_keys: List[str],
        price_key: str = "close",
    ) -> MLDataset:
        if not records:
            raise ValueError("Records list cannot be empty")
        if not feature_keys:
            raise ValueError("feature_keys list cannot be empty")

        n = len(records)
        if n <= self.target_horizon:
            raise ValueError(f"Insufficient records ({n}) for target_horizon ({self.target_horizon})")

        X: List[List[float]] = []
        y: List[int] = []

        for i in range(n - self.target_horizon):
            current_rec = records[i]
            target_rec = records[i + self.target_horizon]

            feat_vector = []
            for k in feature_keys:
                if k not in current_rec:
                    raise KeyError(f"Feature key '{k}' missing from record at index {i}")
                val = current_rec[k]
                if val is None:
                    raise ValueError(f"None value found for feature '{k}' at index {i}")
                feat_vector.append(float(val))

            curr_price = float(current_rec[price_key])
            future_price = float(target_rec[price_key])
            ret = (future_price - curr_price) / curr_price if curr_price > 0 else 0.0

            label = 1 if ret > self.threshold else 0

            X.append(feat_vector)
            y.append(label)

        return MLDataset(X=X, y=y, feature_names=feature_keys)