from datetime import datetime, timezone
from src.domain.enums import Timeframe
from src.domain.models import Candle
from src.pipeline import TradingPipeline


def create_mock_candles(qty: int = 20) -> list[Candle]:
    return [
        Candle(
            symbol="WIN",
            timeframe=Timeframe.M5,
            timestamp=datetime.now(timezone.utc),
            open=100.0 + i,
            high=102.0 + i,
            low=99.0 + i,
            close=101.0 + i,
            volume=1000.0,
        )
        for i in range(qty)
    ]


def test_trading_pipeline_end_to_end():
    pipeline = TradingPipeline(initial_balance=10000.0)
    candles = create_mock_candles(15)

    result = pipeline.process_candle_series(candles, strategy_name="moving_average")

    assert result.candles_processed == 15
    assert isinstance(result.signals_generated, list)
    assert isinstance(result.orders_executed, list)
    assert pipeline.execution_engine.portfolio.equity >= 0.0