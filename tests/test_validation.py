from datetime import datetime, timedelta
import pytest
from src.validation.splitter import OutOfSampleSplitter, WalkForwardSplitter


class DummyCandle:
    def __init__(self, idx: int, ts: datetime):
        self.idx = idx
        self.timestamp = ts


@pytest.fixture
def sample_candles():
    base = datetime(2026, 1, 1, 9, 0)
    return [DummyCandle(i, base + timedelta(minutes=i)) for i in range(100)]


def test_oos_splitter_basic(sample_candles):
    splitter = OutOfSampleSplitter(test_size=0.3)
    res = splitter.split(sample_candles)

    assert len(res.train_data) == 70
    assert len(res.test_data) == 30
    assert res.train_data[-1].timestamp < res.test_data[0].timestamp


def test_oos_splitter_leakage_detection():
    base = datetime(2026, 1, 1, 9, 0)
    # mock same timestamp to trigger leakage assertion
    bad_data = [DummyCandle(i, base) for i in range(10)]
    splitter = OutOfSampleSplitter(test_size=0.3)
    with pytest.raises(ValueError, match="Data leakage detected"):
        splitter.split(bad_data)


def test_walk_forward_splitter(sample_candles):
    splitter = WalkForwardSplitter(train_window=50, test_window=20, step_size=10)
    splits = splitter.split(sample_candles)

    assert len(splits) > 0
    for split in splits:
        assert len(split.train_data) == 50
        assert len(split.test_data) == 20
        assert split.train_data[-1].timestamp < split.test_data[0].timestamp


def test_walk_forward_invalid_window(sample_candles):
    with pytest.raises(ValueError):
        WalkForwardSplitter(train_window=200, test_window=50).split(sample_candles)