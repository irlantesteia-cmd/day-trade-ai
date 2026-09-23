from datetime import datetime, timedelta

import pytest

from src.domain.models import Candle
from src.features.sets import (
    FeatureSet,
    FeatureSetRegistry,
    basic_v1,
    records_from_candles,
    register_default_sets,
)


def _make_candles(n: int, base_ts: datetime = None, symbol: str = "WIN$") -> list:
    if base_ts is None:
        base_ts = datetime(2026, 1, 1, 10, 0, 0)
    candles = []
    price = 100.0
    for i in range(n):
        o = price
        c = price * (1 + 0.001 * ((-1) ** i))
        h = max(o, c) * 1.001
        l = min(o, c) * 0.999
        v = 1000.0 + i
        candles.append(
            Candle(
                symbol=symbol,
                timestamp=base_ts + timedelta(minutes=i),
                open=o,
                high=h,
                low=l,
                close=c,
                volume=v,
            )
        )
        price = c
    return candles


def test_basic_v1_feature_keys():
    fs = basic_v1()
    keys = fs.feature_keys
    assert keys == [
        "log_return_1",
        "log_return_2",
        "log_return_3",
        "log_return_5",
        "body_ratio",
        "upper_shadow_ratio",
        "lower_shadow_ratio",
        "sin_time",
        "cos_time",
    ]


def test_registry_register_and_get():
    reg = FeatureSetRegistry()
    register_default_sets(reg)
    fs = reg.get("basic", "v1")
    assert isinstance(fs, FeatureSet)
    assert fs.name == "basic"
    assert fs.version == "v1"


def test_registry_missing_raises():
    reg = FeatureSetRegistry()
    register_default_sets(reg)
    with pytest.raises(KeyError):
        reg.get("nao_existe", "v0")


def test_registry_list_available():
    reg = FeatureSetRegistry()
    register_default_sets(reg)
    assert ("basic", "v1") in reg.list_available()


def test_records_from_candles_empty():
    fs = basic_v1()
    assert records_from_candles([], fs) == []


def test_records_from_candles_generates_expected_fields():
    fs = basic_v1()
    candles = _make_candles(20)
    records = records_from_candles(candles, fs, min_history=6)

    # 20 candles - 6 de historico = 14 records
    assert len(records) == 14

    rec = records[0]
    for k in ("timestamp", "open", "high", "low", "close", "volume"):
        assert k in rec
    for k in fs.feature_keys:
        assert k in rec, f"feature '{k}' ausente"


def test_records_from_candles_no_look_ahead():
    """O ultimo record deve usar apenas candles[0..i], nunca candles[i+1:]."""
    fs = basic_v1()
    candles = _make_candles(20)
    records = records_from_candles(candles, fs, min_history=6)

    assert records[0]["timestamp"] == candles[6].timestamp
    assert records[-1]["timestamp"] == candles[19].timestamp


def test_custom_feature_set():
    """Um FeatureSet vazio ainda deve funcionar (0 features)."""
    fs = FeatureSet(name="empty", version="v0", extractors=[])
    assert fs.feature_keys == []
    pipeline = fs.build_pipeline()
    assert pipeline is not None