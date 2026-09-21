from datetime import datetime, timezone
from src.backtest.engine import BacktestEngine
from src.domain.enums import Timeframe
from src.domain.models import Candle
from src.strategies.moving_average import MovingAverageCrossoverStrategy


def create_sample_candles():
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
        for i in range(10)
    ]


def test_backtest_engine_run():
    candles = create_sample_candles()
    strategy = MovingAverageCrossoverStrategy()
    
    # Mock de resultado de indicadores acionando sinal de compra
    indicator_results = {"sma_fast": 105.0, "sma_slow": 100.0}

    engine = BacktestEngine(strategy=strategy, initial_balance=10000.0)
    result = engine.run(candles, indicator_results=indicator_results)

    assert result is not None
    assert len(result.equity_curve) == len(candles) + 1
    assert result.metrics.total_trades >= 0
    assert result.initial_balance == 10000.0