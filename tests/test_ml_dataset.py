import pytest
from src.models.dataset import DatasetBuilder, MLDataset


def test_dataset_builder_basic():
    records = [
        {"close": 100.0, "rsi": 30.0, "sma": 98.0},
        {"close": 102.0, "rsi": 35.0, "sma": 99.0},
        {"close": 101.0, "rsi": 32.0, "sma": 100.0},
        {"close": 105.0, "rsi": 40.0, "sma": 101.0},
    ]
    builder = DatasetBuilder(target_horizon=1, threshold=0.0)
    ds = builder.build_binary_classification_dataset(
        records=records,
        feature_keys=["rsi", "sma"],
        price_key="close",
    )

    assert isinstance(ds, MLDataset)
    assert len(ds.X) == 3
    assert len(ds.y) == 3
    assert ds.feature_names == ["rsi", "sma"]

    # Index 0: 100 -> 102 (+2%) -> y=1
    assert ds.X[0] == [30.0, 98.0]
    assert ds.y[0] == 1

    # Index 1: 102 -> 101 (-0.98%) -> y=0
    assert ds.X[1] == [35.0, 99.0]
    assert ds.y[1] == 0

    # Index 2: 101 -> 105 (+3.96%) -> y=1
    assert ds.X[2] == [32.0, 100.0]
    assert ds.y[2] == 1


def test_dataset_builder_horizon_and_threshold():
    records = [
        {"close": 100.0, "f1": 1.0},
        {"close": 101.0, "f1": 2.0},
        {"close": 103.0, "f1": 3.0},
    ]
    builder = DatasetBuilder(target_horizon=2, threshold=0.02)
    ds = builder.build_binary_classification_dataset(
        records=records, feature_keys=["f1"]
    )

    assert len(ds.X) == 1
    # 100 -> 103 (+3% > 2%) -> y=1
    assert ds.y[0] == 1


def test_dataset_builder_invalid_inputs():
    builder = DatasetBuilder(target_horizon=1)
    with pytest.raises(ValueError):
        builder.build_binary_classification_dataset([], feature_keys=["f1"])

    with pytest.raises(ValueError):
        builder.build_binary_classification_dataset(
            [{"close": 100.0, "f1": 1.0}], feature_keys=["f1"]
        )