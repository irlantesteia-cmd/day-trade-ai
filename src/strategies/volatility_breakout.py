"""
VolatilityBreakoutStrategy - breakout condicionado a expansao de volatilidade.

Baseada no achado do ADR-023: e possivel prever "movimento grande" no
WIN M5 em horizonte curto (H=3..5) com edge modesto (+3 a +6 p.p.).

Target do modelo original: |close[t+H] - close[t]| / close[t] > threshold
(volatilidade, NAO direcao).

Esta estrategia converte o sinal em acao direcional usando breakout:
  - Se vol expandiu (vol_ratio > threshold) E preco rompeu maxima
    recente → BUY (aposta em continuacao)
  - Se vol expandiu E preco rompeu minima recente → SELL
  - Caso contrario → NEUTRAL (nao opera)

Design:
  - Sem look-ahead: usa apenas candles[:i+1] via janela
  - Confia em IndicatorEngine para ATR/volatilidade (nao recalcula)
  - Parametrizavel: lookback, vol_threshold, atr_mult
  - Nao define SL/TP (deixa para RiskEngine via ATR do metadata)
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.domain.enums import SignalDirection, Timeframe
from src.domain.models import Candle, Signal


class VolatilityBreakoutStrategy:
    def __init__(
        self,
        lookback: int = 20,
        vol_threshold: float = 1.3,
        atr_key: str = "atr",
        name: str = "VOLATILITY_BREAKOUT",
    ):
        """
        Args:
            lookback: N de candles para calcular maxima/minima de referencia
            vol_threshold: razao minima entre range atual e range medio
                (range_atual / range_medio > threshold = expansao)
            atr_key: chave do ATR em indicator_results
            name: nome identificador
        """
        if lookback < 2:
            raise ValueError("lookback deve ser >= 2")
        if vol_threshold <= 0:
            raise ValueError("vol_threshold deve ser positivo")

        self.lookback = lookback
        self.vol_threshold = vol_threshold
        self.atr_key = atr_key
        self.name = name

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

    def _is_volatility_expanded(
        self, candles: List[Candle], indicator_results: Optional[Dict[str, Any]]
    ) -> bool:
        """
        True se a volatilidade esta expandindo.

        Dois criterios alternativos (OR):
          A. range atual / range medio > vol_threshold
          B. ATR atual / close > mediana de ATR/close dos ultimos N
             (implícito no range ratio acima — usamos apenas A)

        Usamos criterio A por ser mais simples e nao depender de historico
        grande de ATR.
        """
        if len(candles) < self.lookback + 1:
            return False

        window = candles[-(self.lookback + 1):]
        last = window[-1]
        prev_window = window[:-1]

        ranges = [c.high - c.low for c in prev_window if c.high > c.low]
        if not ranges:
            return False

        avg_range = sum(ranges) / len(ranges)
        if avg_range <= 0:
            return False

        current_range = last.high - last.low
        if current_range <= 0:
            return False

        return (current_range / avg_range) >= self.vol_threshold

    def _get_breakout(
        self, candles: List[Candle]
    ) -> Optional[str]:
        """
        Retorna "up" se close atual > max(high) das ultimas N barras (sem
        incluir a atual), "down" se close < min(low), None caso contrario.
        """
        if len(candles) < self.lookback + 1:
            return None

        window = candles[-(self.lookback + 1):-1]
        if not window:
            return None

        last = candles[-1]
        prior_high = max(c.high for c in window)
        prior_low = min(c.low for c in window)

        if last.close > prior_high:
            return "up"
        if last.close < prior_low:
            return "down"
        return None

    def evaluate(
        self,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
        feature_results: Optional[Dict[str, Any]] = None,
    ) -> Signal:
        if not candles:
            return self._neutral(candles, "sem candles")

        if len(candles) < self.lookback + 1:
            return self._neutral(candles, f"historico insuficiente (<{self.lookback + 1})")

        # 1. Condicao de volatilidade (pre-requisito)
        if not self._is_volatility_expanded(candles, indicator_results):
            return self._neutral(candles, "volatilidade nao expandiu")

        # 2. Direcao via breakout
        direction = self._get_breakout(candles)
        if direction is None:
            return self._neutral(candles, "sem breakout direcional")

        last = candles[-1]

        # 3. ATR (opcional, para SL/TP dinamico via RiskEngine)
        atr_val = None
        if indicator_results:
            atr_val = indicator_results.get(self.atr_key)

        metadata: Dict[str, Any] = {
            "price": last.close,
            "breakout": direction,
        }
        if atr_val is not None:
            metadata["atr"] = atr_val

        if direction == "up":
            return Signal(
                symbol=last.symbol,
                timeframe=last.timeframe,
                timestamp=last.timestamp,
                direction=SignalDirection.BUY,
                confidence=0.7,
                strategy_name=self.name,
                metadata=metadata,
            )

        return Signal(
            symbol=last.symbol,
            timeframe=last.timeframe,
            timestamp=last.timestamp,
            direction=SignalDirection.SELL,
            confidence=0.7,
            strategy_name=self.name,
            metadata=metadata,
        )