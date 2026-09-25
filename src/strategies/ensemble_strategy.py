"""
EnsembleStrategy - combina N estrategias via ConsensusEngine.

Instancia internamente:
  - MovingAverageCrossoverStrategy
  - RSIMeanReversionStrategy
  - VolatilityBreakoutStrategy
  - RegimeFilteredMAStrategy (opcional, mais restritiva)

Em cada candle:
  1. Coleta sinais individuais
  2. Aplica ConsensusEngine
  3. Retorna sinal agregado ou NEUTRAL

Uso:
    strategy = EnsembleStrategy(
        mode="vote",
        min_agreement=0.5,
        include_regime_filtered=False,
    )
    sig = strategy.evaluate(candles, indicators, features)
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.domain.enums import SignalDirection, Timeframe
from src.domain.models import Candle, Signal
from src.signals.consensus import ConsensusEngine

from src.strategies.moving_average import MovingAverageCrossoverStrategy
from src.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from src.strategies.volatility_breakout import VolatilityBreakoutStrategy
from src.strategies.regime_filtered_ma import RegimeFilteredMAStrategy

logger = logging.getLogger(__name__)


class EnsembleStrategy:
    def __init__(
        self,
        mode: str = "vote",
        min_agreement: float = 0.5,
        min_confidence: float = 0.5,
        name: str = "ENSEMBLE",
        include_regime_filtered: bool = True,
    ):
        self.name = name
        self.consensus = ConsensusEngine(
            mode=mode,
            min_agreement=min_agreement,
            min_confidence=min_confidence,
        )

        # Estrategias base
        self.strategies: List[Any] = [
            MovingAverageCrossoverStrategy(),
            RSIMeanReversionStrategy(rsi_key="rsi"),
            VolatilityBreakoutStrategy(lookback=20, vol_threshold=1.5),
        ]
        if include_regime_filtered:
            self.strategies.append(
                RegimeFilteredMAStrategy(
                    vol_window=20, vol_lookback=500, vol_percentile=66.0
                )
            )

    def _neutral(self, candles: List[Candle], reason: str) -> Signal:
        if candles:
            last = candles[-1]
            return Signal(
                symbol=last.symbol,
                timeframe=last.timeframe,
                timestamp=last.timestamp,
                direction=SignalDirection.NEUTRAL,
                confidence=0.0,
                strategy_name=self.name,
                metadata={"reason": reason},
            )
        return Signal(
            symbol="UNKNOWN",
            timeframe=Timeframe.M5,
            timestamp=datetime.now(timezone.utc),
            direction=SignalDirection.NEUTRAL,
            confidence=0.0,
            strategy_name=self.name,
            metadata={"reason": reason},
        )

    def evaluate(
        self,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
        feature_results: Optional[Dict[str, Any]] = None,
    ) -> Signal:
        if not candles:
            return self._neutral(candles, "sem candles")

        # Coleta sinais de cada estrategia
        individual_signals: List[Signal] = []
        for strat in self.strategies:
            try:
                sig = strat.evaluate(candles, indicator_results, feature_results)
                if sig is not None:
                    individual_signals.append(sig)
            except Exception as exc:
                logger.debug(
                    "Estrategia %s falhou: %s",
                    getattr(strat, "name", type(strat).__name__),
                    exc,
                )

        if not individual_signals:
            return self._neutral(candles, "sem sinais individuais")

        # Combina via consensus
        aggregated = self.consensus.combine(individual_signals)

        # Anexa metadata extra
        if aggregated.metadata is None:
            aggregated.metadata = {}
        aggregated.metadata["n_individual_signals"] = len(individual_signals)
        aggregated.strategy_name = self.name

        return aggregated