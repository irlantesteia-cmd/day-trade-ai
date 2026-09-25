"""
ConsensusEngine - combina N sinais em um so.

Modos de agregacao:
  - vote:     maioria simples (ex: 2 de 3 = opera)
  - weighted: soma ponderada por confianca
  - unanimous: todos precisam concordar
  - confidence_weighted: pesos por confianca + threshold

Retorna Signal agregado (BUY/SELL/NEUTRAL) com confidence media.

Uso:
    engine = ConsensusEngine(mode="vote", min_agreement=0.5)
    sig = engine.combine([sig1, sig2, sig3])
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.domain.enums import SignalDirection, Timeframe
from src.domain.models import Signal

logger = logging.getLogger(__name__)


def _extract_direction(sig: Signal) -> str:
    """
    Normaliza direction de Signal para 'BUY' | 'SELL' | 'NEUTRAL'.

    Estrategias usam SignalDirection OU SignalType (inconsistencia historica).
    """
    raw = getattr(sig, "direction", None)
    if raw is None:
        return "NEUTRAL"
    val = str(getattr(raw, "value", raw)).upper()
    if "BUY" in val:
        return "BUY"
    if "SELL" in val:
        return "SELL"
    return "NEUTRAL"


def _extract_confidence(sig: Signal) -> float:
    """
    Extrai confidence de Signal.

    MA usa 'strength', RSI/VB usam 'confidence'. Aceita ambos.
    """
    for attr in ("confidence", "strength"):
        v = getattr(sig, attr, None)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return 0.5


class ConsensusEngine:
    def __init__(
        self,
        mode: str = "vote",
        min_agreement: float = 0.5,
        min_confidence: float = 0.5,
    ):
        """
        Args:
            mode: 'vote' | 'weighted' | 'unanimous' | 'confidence_weighted'
            min_agreement: fracao minima de votos concordantes (0.5 = maioria)
            min_confidence: threshold minimo para considerar o sinal final
        """
        valid = {"vote", "weighted", "unanimous", "confidence_weighted"}
        if mode not in valid:
            raise ValueError(f"mode invalido: {mode}. Use: {valid}")
        if not 0 < min_agreement <= 1:
            raise ValueError("min_agreement deve estar em (0, 1]")
        if not 0 < min_confidence < 1:
            raise ValueError("min_confidence deve estar em (0, 1)")

        self.mode = mode
        self.min_agreement = min_agreement
        self.min_confidence = min_confidence

    def _neutral(self, signals: List[Signal], reason: str) -> Signal:
        if signals and signals[0]:
            s0 = signals[0]
            return Signal(
                symbol=getattr(s0, "symbol", "UNKNOWN"),
                timeframe=getattr(s0, "timeframe", Timeframe.M5),
                timestamp=getattr(s0, "timestamp", datetime.now(timezone.utc)),
                direction=SignalDirection.NEUTRAL,
                confidence=0.0,
                metadata={"consensus": "NEUTRAL", "reason": reason},
            )
        return Signal(
            symbol="UNKNOWN",
            timeframe=Timeframe.M5,
            timestamp=datetime.now(timezone.utc),
            direction=SignalDirection.NEUTRAL,
            confidence=0.0,
            metadata={"consensus": "NEUTRAL", "reason": reason},
        )

    def combine(self, signals: List[Signal]) -> Signal:
        """Combina uma lista de sinais em um unico sinal agregado."""
        if not signals:
            return self._neutral(signals, "sem sinais")

        # Extrai direcoes e confidences
        directions = [_extract_direction(s) for s in signals]
        confidences = [_extract_confidence(s) for s in signals]

        n = len(signals)
        n_buy = sum(1 for d in directions if d == "BUY")
        n_sell = sum(1 for d in directions if d == "SELL")
        n_neutral = n - n_buy - n_sell

        # Modo unanimidade
        if self.mode == "unanimous":
            if n_buy == n and n > 0:
                return self._make_signal(signals, "BUY", sum(confidences) / n, "unanimous_buy")
            if n_sell == n and n > 0:
                return self._make_signal(signals, "SELL", sum(confidences) / n, "unanimous_sell")
            return self._neutral(signals, "sem unanimidade")

        # Modo voto
        if self.mode == "vote":
            if n_buy / n >= self.min_agreement:
                return self._make_signal(signals, "BUY", sum(confidences) / n, f"vote_{n_buy}/{n}")
            if n_sell / n >= self.min_agreement:
                return self._make_signal(signals, "SELL", sum(confidences) / n, f"vote_{n_sell}/{n}")
            return self._neutral(signals, f"sem consenso (buy={n_buy} sell={n_sell})")

        # Modo weighted (soma de confidence com sinal)
        if self.mode == "weighted":
            buy_score = sum(c for d, c in zip(directions, confidences) if d == "BUY")
            sell_score = sum(c for d, c in zip(directions, confidences) if d == "SELL")
            total = buy_score + sell_score
            if total == 0:
                return self._neutral(signals, "sem scores")
            buy_pct = buy_score / total
            sell_pct = sell_score / total
            if buy_pct >= self.min_agreement:
                return self._make_signal(signals, "BUY", buy_pct, f"weighted_buy_{buy_pct:.2f}")
            if sell_pct >= self.min_agreement:
                return self._make_signal(signals, "SELL", sell_pct, f"weighted_sell_{sell_pct:.2f}")
            return self._neutral(signals, f"sem consenso ponderado (b={buy_pct:.2f} s={sell_pct:.2f})")

        # Modo confidence_weighted: peso por confidence, exige direcao dominante
        if self.mode == "confidence_weighted":
            buy_weights = sum(c for d, c in zip(directions, confidences) if d == "BUY")
            sell_weights = sum(c for d, c in zip(directions, confidences) if d == "SELL")
            total_w = sum(confidences)

            if total_w == 0:
                return self._neutral(signals, "peso total zero")

            buy_frac = buy_weights / total_w
            sell_frac = sell_weights / total_w

            if buy_frac >= self.min_agreement and buy_frac >= self.min_confidence:
                return self._make_signal(signals, "BUY", buy_frac, f"cw_buy_{buy_frac:.2f}")
            if sell_frac >= self.min_agreement and sell_frac >= self.min_confidence:
                return self._make_signal(signals, "SELL", sell_frac, f"cw_sell_{sell_frac:.2f}")
            return self._neutral(signals, "sem consenso ponderado por confidence")

        return self._neutral(signals, "modo desconhecido")

    def _make_signal(
        self,
        signals: List[Signal],
        direction: str,
        confidence: float,
        reason: str,
    ) -> Signal:
        s0 = signals[0]
        return Signal(
            symbol=getattr(s0, "symbol", "UNKNOWN"),
            timeframe=getattr(s0, "timeframe", Timeframe.M5),
            timestamp=getattr(s0, "timestamp", datetime.now(timezone.utc)),
            direction=SignalDirection.BUY if direction == "BUY" else SignalDirection.SELL,
            confidence=min(1.0, max(0.0, float(confidence))),
            metadata={
                "consensus": direction,
                "reason": reason,
                "n_signals": len(signals),
            },
        )