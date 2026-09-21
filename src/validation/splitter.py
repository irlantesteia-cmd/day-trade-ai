from typing import List, Tuple, Any, Optional
from datetime import datetime


class SplitResult:
    def __init__(
        self,
        train_data: List[Any],
        test_data: List[Any],
        train_indices: Tuple[int, int],
        test_indices: Tuple[int, int],
    ):
        self.train_data = train_data
        self.test_data = test_data
        self.train_indices = train_indices
        self.test_indices = test_indices


class OutOfSampleSplitter:
    def __init__(self, test_size: float = 0.3):
        if not 0.0 < test_size < 1.0:
            raise ValueError("test_size must be between 0.0 and 1.0 exclusive.")
        self.test_size = test_size

    def _get_ts(self, item: Any) -> datetime:
        if hasattr(item, "timestamp"):
            ts = item.timestamp
            if isinstance(ts, datetime):
                return ts
        elif isinstance(item, dict) and "timestamp" in item:
            return item["timestamp"]
        raise TypeError(f"Item must have a valid datetime 'timestamp' attribute or dict key.")

    def split(self, data: List[Any]) -> SplitResult:
        if not data:
            raise ValueError("Data list cannot be empty for OOS split.")

        n = len(data)
        test_count = int(n * self.test_size)
        if test_count == 0 or test_count >= n:
            raise ValueError("Dataset size insufficient for the specified test_size ratio.")

        train_data = data[: n - test_count]
        test_data = data[n - test_count :]

        max_train_ts = self._get_ts(train_data[-1])
        min_test_ts = self._get_ts(test_data[0])
        if max_train_ts >= min_test_ts:
            raise ValueError("Data leakage detected: train end timestamp >= test start timestamp.")

        return SplitResult(
            train_data=train_data,
            test_data=test_data,
            train_indices=(0, n - test_count),
            test_indices=(n - test_count, n),
        )


class WalkForwardSplitter:
    def __init__(self, train_window: int, test_window: int, step_size: Optional[int] = None):
        if train_window <= 0 or test_window <= 0:
            raise ValueError("Window sizes must be positive integers.")
        self.train_window = train_window
        self.test_window = test_window
        self.step_size = step_size if step_size is not None else test_window

    def split(self, data: List[Any]) -> List[SplitResult]:
        if not data:
            raise ValueError("Data list cannot be empty for Walk-Forward split.")

        n = len(data)
        required_len = self.train_window + self.test_window
        if n < required_len:
            raise ValueError(f"Dataset length ({n}) smaller than required window ({required_len}).")

        splits = []
        start_idx = 0
        while start_idx + self.train_window + self.test_window <= n:
            train_end = start_idx + self.train_window
            test_end = train_end + self.test_window

            train_data = data[start_idx:train_end]
            test_data = data[train_end:test_end]

            splits.append(
                SplitResult(
                    train_data=train_data,
                    test_data=test_data,
                    train_indices=(start_idx, train_end),
                    test_indices=(train_end, test_end),
                )
            )
            start_idx += self.step_size

        return splits