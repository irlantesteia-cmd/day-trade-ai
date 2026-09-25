"""Teste rapido do ConsensusEngine."""
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.domain.enums import SignalDirection, Timeframe
from src.domain.models import Signal
from src.signals.consensus import ConsensusEngine


def make_signal(direction: str, confidence: float = 0.7) -> Signal:
    return Signal(
        symbol="WIN$",
        timeframe=Timeframe.M5,
        timestamp=datetime.now(timezone.utc),
        direction=SignalDirection.BUY if direction == "BUY" else (
            SignalDirection.SELL if direction == "SELL" else SignalDirection.NEUTRAL
        ),
        confidence=confidence,
    )


def show(label: str, sig: Signal) -> None:
    d = getattr(sig.direction, "value", sig.direction)
    c = getattr(sig, "confidence", None)
    reason = sig.metadata.get("reason", "") if sig.metadata else ""
    print(f"  {label:30s} -> {d:8s} conf={c} ({reason})")


def main():
    signals_2buy_1sell = [
        make_signal("BUY", 0.8),
        make_signal("BUY", 0.7),
        make_signal("SELL", 0.6),
    ]
    signals_1buy_2sell = [
        make_signal("BUY", 0.9),
        make_signal("SELL", 0.5),
        make_signal("SELL", 0.5),
    ]
    signals_unanimous_buy = [
        make_signal("BUY", 0.9),
        make_signal("BUY", 0.7),
        make_signal("BUY", 0.6),
    ]

    for mode in ["vote", "weighted", "unanimous", "confidence_weighted"]:
        print(f"\nMode: {mode}")
        engine = ConsensusEngine(mode=mode, min_agreement=0.5, min_confidence=0.5)
        show("2 buy 1 sell", engine.combine(signals_2buy_1sell))
        show("1 buy 2 sell", engine.combine(signals_1buy_2sell))
        show("3 buy (unanimous)", engine.combine(signals_unanimous_buy))


if __name__ == "__main__":
    main()