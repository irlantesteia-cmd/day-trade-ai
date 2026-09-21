from datetime import datetime, timezone
from src.domain.enums import SignalType, Timeframe
from src.domain.models import Candle
from src.strategies.engine import StrategyEngine
from src.strategies.moving_average import MovingAverageCrossoverStrategy
from src.strategies.registry import StrategyRegistry
from src.strategies.rsi_mean_reversion import RSIMeanReversionStrategy


def create_sample_candle() -> Candle:
    return Candle(
        symbol="WIN",
        timeframe=Timeframe.M1,
        timestamp=datetime.now(timezone.utc),
        open=100.0,
        high=105.0,
        low=95.0,
        close=102.0,
        volume=1000.0,
    )


def test_moving_average_crossover_buy_signal():
    candle = create_sample_candle()
    strategy = MovingAverageCrossoverStrategy(fast_key="sma_10", slow_key="sma_30")

    mock_indicators = {"sma_10": 105.0, "sma_30": 100.0}
    signal = strategy.evaluate([candle], indicator_results=mock_indicators)

    assert signal.type == SignalType.BUY
    assert signal.strategy_name == "MA_CROSSOVER"
    assert signal.confidence > 0.5


def test_moving_average_crossover_sell_signal():
    candle = create_sample_candle()
    strategy = MovingAverageCrossoverStrategy(fast_key="sma_10", slow_key="sma_30")

    mock_indicators = {"sma_10": 95.0, "sma_30": 100.0}
    signal = strategy.evaluate([candle], indicator_results=mock_indicators)

    assert signal.type == SignalType.SELL
    assert signal.confidence > 0.5


def test_rsi_mean_reversion_oversold_buy():
    candle = create_sample_candle()
    strategy = RSIMeanReversionStrategy(rsi_key="rsi_14", oversold=30.0, overbought=70.0)

    mock_indicators = {"rsi_14": 20.0}
    signal = strategy.evaluate([candle], indicator_results=mock_indicators)

    assert signal.type == SignalType.BUY
    assert signal.confidence > 0.5


def test_rsi_mean_reversion_overbought_sell():
    candle = create_sample_candle()
    strategy = RSIMeanReversionStrategy(rsi_key="rsi_14", oversold=30.0, overbought=70.0)

    mock_indicators = {"rsi_14": 80.0}
    signal = strategy.evaluate([candle], indicator_results=mock_indicators)

    assert signal.type == SignalType.SELL
    assert signal.confidence > 0.5


def test_strategy_missing_indicators_returns_neutral():
    candle = create_sample_candle()
    strategy = RSIMeanReversionStrategy()

    signal = strategy.evaluate([candle], indicator_results={})

    assert signal.type == SignalType.NEUTRAL
    assert signal.confidence == 0.0


def test_strategy_engine_and_registry():
    registry = StrategyRegistry()
    registry.register("MA_CROSSOVER", MovingAverageCrossoverStrategy)
    registry.register("RSI_REVERSION", RSIMeanReversionStrategy)

    engine = StrategyEngine()
    engine.add_strategy(registry.get("MA_CROSSOVER"))
    engine.add_strategy(registry.get("RSI_REVERSION"))

    candle = create_sample_candle()
    mock_indicators = {"sma_fast": 105.0, "sma_slow": 100.0, "rsi_14": 25.0}

    signals = engine.evaluate_all([candle], indicator_results=mock_indicators)

    assert len(signals) == 2
    assert signals[0].type == SignalType.BUY
    assert signals[1].type == SignalType.BUY