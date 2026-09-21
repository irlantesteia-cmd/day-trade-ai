from typing import Any, Dict, List, Optional
from src.domain.enums import SignalType
from src.domain.models import Candle, Signal


class RSIMeanReversionStrategy:
    def __init__(
        self,
        rsi_key: str = "rsi_14",
        oversold: float = 30.0,
        overbought: float = 70.0,
        name: str = "RSI_REVERSION",
    ):
        self.rsi_key = rsi_key
        self.oversold = oversold
        self.overbought = overbought
        self.name = name

    def evaluate(
        self,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
        feature_results: Optional[Dict[str, Any]] = None,
    ) -> Signal:
        if not candles:
            raise ValueError("A lista de candles não pode estar vazia.")

        last_candle = candles[-1]

        if not indicator_results or self.rsi_key not in indicator_results:
            return Signal(
                symbol=last_candle.symbol,
                timeframe=last_candle.timeframe,
                timestamp=last_candle.timestamp,
                direction=SignalType.NEUTRAL,
                strategy_id=self.name,
                strategy_version="1.0.0",
                confidence=0.0,
                metadata={"reason": "Indicador RSI ausente"},
            )

        rsi_val = indicator_results.get(self.rsi_key)

        if rsi_val is None:
            return Signal(
                symbol=last_candle.symbol,
                timeframe=last_candle.timeframe,
                timestamp=last_candle.timestamp,
                direction=SignalType.NEUTRAL,
                strategy_id=self.name,
                strategy_version="1.0.0",
                confidence=0.0,
                metadata={"reason": "Valor do RSI nulo"},
            )

        if rsi_val <= self.oversold:
            sig_type = SignalType.BUY
            confidence = max(0.5, min(1.0, 0.5 + (self.oversold - rsi_val) / self.oversold))
        elif rsi_val >= self.overbought:
            sig_type = SignalType.SELL
            confidence = max(
                0.5, min(1.0, 0.5 + (rsi_val - self.overbought) / (100.0 - self.overbought))
            )
        else:
            sig_type = SignalType.NEUTRAL
            confidence = 0.0

        return Signal(
            symbol=last_candle.symbol,
            timeframe=last_candle.timeframe,
            timestamp=last_candle.timestamp,
            direction=sig_type,
            strategy_id=self.name,
            strategy_version="1.0.0",
            confidence=round(confidence, 4),
            metadata={"rsi_val": rsi_val},
        )