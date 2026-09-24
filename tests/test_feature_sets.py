from datetime import datetime, timedelta, timezone

import pytest

from src.domain.enums import Timeframe
from src.domain.models import Candle
from src.features.sets import (
    FeatureSet,
    FeatureSetRegistry,
    basic_v1,
    records_from_candles,
    records_from_candles_with_indicators,
    register_default_sets,
    technical_v1,
)
from src.indicators.engine import IndicatorEngine


def _make_candles(n: int, base_ts: datetime = None, symbol: str = "WIN$") -> list:
    if base_ts is None:
        base_ts = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
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
                timeframe=Timeframe.M1,
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


# ---------------------------------------------------------------------------
# basic_v1 (existentes)
# ---------------------------------------------------------------------------

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
    assert ("technical", "v1") in reg.list_available()


def test_records_from_candles_empty():
    fs = basic_v1()
    assert records_from_candles([], fs) == []


def test_records_from_candles_generates_expected_fields():
    fs = basic_v1()
    candles = _make_candles(20)
    records = records_from_candles(candles, fs, min_history=6)

    assert len(records) == 14
    rec = records[0]
    for k in ("timestamp", "open", "high", "low", "close", "volume"):
        assert k in rec
    for k in fs.feature_keys:
        assert k in rec, f"feature '{k}' ausente"


def test_records_from_candles_no_look_ahead():
    fs = basic_v1()
    candles = _make_candles(20)
    records = records_from_candles(candles, fs, min_history=6)

    assert records[0]["timestamp"] == candles[6].timestamp
    assert records[-1]["timestamp"] == candles[19].timestamp


def test_custom_feature_set():
    fs = FeatureSet(name="empty", version="v0", extractors=[])
    assert fs.feature_keys == []
    pipeline = fs.build_pipeline()
    assert pipeline is not None


# ---------------------------------------------------------------------------
# technical_v1 (novos)
# ---------------------------------------------------------------------------

def test_technical_v1_feature_keys():
    fs = technical_v1()
    keys = fs.feature_keys
    assert "log_return_1" in keys
    assert "log_return_3" in keys
    assert "body_ratio" in keys
    assert "upper_shadow_ratio" in keys
    assert "lower_shadow_ratio" in keys
    assert "rsi_norm" in keys
    assert "sma_fast_dist_pct" in keys
    assert "atr_norm" in keys
    assert len(keys) == 8


def test_technical_v1_registered():
    reg = FeatureSetRegistry()
    register_default_sets(reg)
    fs = reg.get("technical", "v1")
    assert fs.name == "technical"
    assert fs.version == "v1"


def test_records_with_indicators_generates_features():
    fs = technical_v1()
    engine = IndicatorEngine()
    candles = _make_candles(60)
    records = records_from_candles_with_indicators(
        candles, fs, engine, min_history=30
    )

    # Deve ter records (apos min_history)
    assert len(records) > 0
    rec = records[0]
    for k in fs.feature_keys:
        assert k in rec, f"feature '{k}' ausente"
        assert rec[k] is not None, f"feature '{k}' e None"


def test_records_with_indicators_no_look_ahead():
    """Ultimo record usa candles[:i+1] — nao deve depender do futuro."""
    fs = technical_v1()
    engine = IndicatorEngine()
    candles = _make_candles(50)

    records = records_from_candles_with_indicators(
        candles, fs, engine, min_history=30
    )
    assert records[-1]["timestamp"] == candles[49].timestamp


def test_records_with_indicators_empty():
    fs = technical_v1()
    engine = IndicatorEngine()
    assert records_from_candles_with_indicators([], fs, engine) == []


def test_records_with_indicators_drops_none_by_default():
    """
    Com poucos candles (< periodo de indicadores), features podem ser None.
    drop_none_features=True descarta esses records.
    """
    fs = technical_v1()
    engine = IndicatorEngine()
    candles = _make_candles(35)

    # min_history muito baixo: primeiro record pode ter ATR valido (default 1.0)
    # mas com drop_none=True nao deve retornar nenhum record com feature None
    records = records_from_candles_with_indicators(
        candles, fs, engine, min_history=5, drop_none_features=True
    )
    for rec in records:
        for k in fs.feature_keys:
            assert rec.get(k) is not None, f"feature {k} foi None apos drop"