from datetime import datetime, timedelta, timezone
from src.domain.enums import Timeframe
from src.domain.models import Candle
from src.features.pipeline import FeaturePipeline
from src.features.price_action import CandleMorphologyExtractor, LogReturnExtractor
from src.features.registry import FeatureRegistry
from src.features.technical import (
    BollingerPercentBExtractor,
    NormalizedRSIExtractor,
    SMADistanceExtractor,
)
from src.features.temporal import TimeOfDayExtractor


def generate_synthetic_candles(count: int) -> list[Candle]:
    start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    candles = []
    base_price = 100.0

    for i in range(count):
        close_price = base_price + (1.0 if i % 2 == 0 else -0.5)
        candles.append(
            Candle(
                symbol="WIN",
                timeframe=Timeframe.M1,
                timestamp=start + timedelta(minutes=i),
                open=base_price,
                high=max(base_price, close_price) + 0.5,
                low=min(base_price, close_price) - 0.5,
                close=close_price,
                volume=1000.0,
            )
        )
        base_price = close_price
    return candles


def test_log_return_extractor():
    candles = generate_synthetic_candles(3)
    extractor = LogReturnExtractor(period=1)
    res = extractor.extract(candles)
    assert "log_return_1" in res
    assert res["log_return_1"] is not None


def test_candle_morphology_extractor():
    start = datetime.now(timezone.utc)
    candle = Candle(
        symbol="WIN",
        timeframe=Timeframe.M1,
        timestamp=start,
        open=100.0,
        high=110.0,
        low=90.0,
        close=105.0,
        volume=1000.0,
    )
    extractor = CandleMorphologyExtractor()
    res = extractor.extract([candle])

    assert res["body_ratio"] == 0.25
    assert res["upper_shadow_ratio"] == 0.25
    assert res["lower_shadow_ratio"] == 0.5


def test_time_of_day_extractor():
    candles = generate_synthetic_candles(1)
    extractor = TimeOfDayExtractor()
    res = extractor.extract(candles)
    assert "sin_time" in res
    assert "cos_time" in res
    assert -1.0 <= res["sin_time"] <= 1.0


def test_technical_features_with_indicator_data():
    candles = generate_synthetic_candles(5)
    rsi_ext = NormalizedRSIExtractor(rsi_key="rsi_14")
    bb_ext = BollingerPercentBExtractor(bb_key="bb_20")
    sma_ext = SMADistanceExtractor(sma_key="sma_20")

    mock_indicators = {
        "rsi_14": 75.0,
        "bb_20": {"upper": 110.0, "lower": 90.0, "middle": 100.0},
        "sma_20": 100.0,
    }

    rsi_res = rsi_ext.extract(candles, mock_indicators)
    bb_res = bb_ext.extract(candles, mock_indicators)
    sma_res = sma_ext.extract(candles, mock_indicators)

    # RSI 75 -> norm: (75 - 50) / 50 = 0.5
    assert rsi_res["rsi_14_norm"] == 0.5
    # Close do 5º candle e 102.0 -> %B: (102.0 - 90) / 20 = 0.6
    assert bb_res["bb_20_percent_b"] == 0.6
    # Distancia da SMA 20 -> ((102.0 - 100) / 100) * 100 = 2.0%
    assert sma_res["sma_20_dist_pct"] == 2.0


def test_feature_pipeline():
    pipeline = FeaturePipeline()
    pipeline.add_extractor(LogReturnExtractor(period=1))
    pipeline.add_extractor(CandleMorphologyExtractor())
    pipeline.add_extractor(TimeOfDayExtractor())

    candles = generate_synthetic_candles(3)
    features = pipeline.extract_all(candles)

    assert "log_return_1" in features
    assert "body_ratio" in features
    assert "sin_time" in features
    assert len(features) >= 5


def test_feature_registry():
    registry = FeatureRegistry()
    registry.register("LOG_RETURN", LogReturnExtractor)

    extractor = registry.get("LOG_RETURN", period=2)
    assert extractor.name == "log_return_2"