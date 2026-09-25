"""
EnsembleLiveAdapter - ponte entre LiveTradingEngine e EnsembleStrategy.

Problema:
  LiveTradingEngine chama strategy.generate_signal(bar_dict)
  EnsembleStrategy (e MA/RSI/VB/RFMA) expoe evaluate(candles, indicators)

Solucao:
  Este adapter:
    1. Mantem buffer de Candles
    2. Recebe bar dict, converte em Candle, adiciona ao buffer
    3. Computa indicadores via IndicatorEngine
    4. Chama a estrategia interna .evaluate(candles, indicators)
    5. Retorna Signal

Uso:
    adapter = EnsembleLiveAdapter(
        internal_strategy=EnsembleStrategy(mode="vote"),
        indicator_engine=IndicatorEngine(),
        max_buffer=500,
    )
    # em loop:
    sig = adapter.generate_signal(bar_dict)
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.domain.enums import Timeframe
from src.domain.models import Candle, Signal

logger = logging.getLogger(__name__)


class EnsembleLiveAdapter:
    def __init__(
        self,
        internal_strategy: Any,
        indicator_engine: Any,
        max_buffer: int = 500,
        min_history: int = 50,
        timeframe: Timeframe = Timeframe.M5,
    ):
        self.strategy = internal_strategy
        self.indicator_engine = indicator_engine
        self.max_buffer = max_buffer
        self.min_history = min_history
        self.timeframe = timeframe
        self._buffer: List[Candle] = []
        self._seen_timestamps: set = set()

    def _bar_to_candle(self, bar: Dict[str, Any]) -> Optional[Candle]:
        """Converte bar dict em Candle. Retorna None se invalido."""
        try:
            ts = bar.get("timestamp")
            if isinstance(ts, int):
                ts_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            elif isinstance(ts, datetime):
                ts_dt = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
            else:
                ts_dt = datetime.now(timezone.utc)

            return Candle(
                symbol=bar.get("symbol", "UNKNOWN"),
                timeframe=self.timeframe,
                timestamp=ts_dt,
                open=float(bar["open"]),
                high=float(bar["high"]),
                low=float(bar["low"]),
                close=float(bar["close"]),
                volume=float(bar.get("volume", 0.0)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.debug("Bar invalido: %s", exc)
            return None

    def generate_signal(self, bar: Dict[str, Any]) -> Optional[Signal]:
        """
        Recebe bar dict, mantem buffer, chama a estrategia interna.
        """
        candle = self._bar_to_candle(bar)
        if candle is None:
            return None

        # Dedup por timestamp
        ts_key = candle.timestamp
        if ts_key in self._seen_timestamps:
            return None
        self._seen_timestamps.add(ts_key)

        # Adiciona ao buffer
        self._buffer.append(candle)
        if len(self._buffer) > self.max_buffer:
            self._buffer = self._buffer[-self.max_buffer:]
            # Limpa set de timestamps antigos
            self._seen_timestamps = {c.timestamp for c in self._buffer}

        # Historico insuficiente
        if len(self._buffer) < self.min_history:
            return None

        # Computa indicadores
        try:
            indicators = self.indicator_engine.compute_all(self._buffer)
        except Exception as exc:
            logger.debug("IndicatorEngine falhou: %s", exc)
            indicators = {}

        # Chama estrategia interna
        try:
            sig = self.strategy.evaluate(
                candles=self._buffer,
                indicator_results=indicators,
                feature_results=None,
            )
            return sig
        except Exception as exc:
            logger.exception("Estrategia interna falhou: %s", exc)
            return None

    def reset(self) -> None:
        """Limpa buffer. Util para testes."""
        self._buffer.clear()
        self._seen_timestamps.clear()

    def buffer_size(self) -> int:
        return len(self._buffer)