"""Teste do EnsembleStrategy com candles sinteticos."""
import sys
import os
from datetime import datetime, timezone, timedelta
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.domain.enums import Timeframe
from src.domain.models import Candle
from src.indicators.engine import IndicatorEngine
from src.strategies.ensemble_strategy import EnsembleStrategy


def make_candles(n: int = 500) -> list:
    """Cria candles sinteticos com tendencia."""
    np.random.seed(42)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    price = 130000.0
    prev_ret = 0.0
    for i in range(n):
        # Trend de alta moderado + ruido
        ret = 0.0001 + 0.3 * prev_ret + np.random.randn() * 0.0005
        o = price
        c = price * (1 + ret)
        h = max(o, c) * 1.0003
        l = min(o, c) * 0.9997
        candles.append(Candle(
            symbol="WIN$", timeframe=Timeframe.M5,
            timestamp=base + timedelta(minutes=5 * i),
            open=o, high=h, low=l, close=c, volume=1000.0,
        ))
        price = c
        prev_ret = ret
    return candles


def main():
    candles = make_candles(500)
    engine = IndicatorEngine()

    for mode in ["vote", "weighted", "confidence_weighted"]:
        strat = EnsembleStrategy(mode=mode, min_agreement=0.5, min_confidence=0.5)
        signals = {"BUY": 0, "SELL": 0, "NEUTRAL": 0}

        for i in range(50, len(candles)):
            window = candles[:i+1]
            indicators = engine.compute_all(window)
            sig = strat.evaluate(window, indicator_results=indicators)
            d = str(getattr(sig.direction, "value", sig.direction)).upper()
            if "BUY" in d:
                signals["BUY"] += 1
            elif "SELL" in d:
                signals["SELL"] += 1
            else:
                signals["NEUTRAL"] += 1

        total = sum(signals.values())
        print(f"\nMode: {mode}")
        print(f"  BUY:     {signals['BUY']:>4} ({signals['BUY']/total*100:.1f}%)")
        print(f"  SELL:    {signals['SELL']:>4} ({signals['SELL']/total*100:.1f}%)")
        print(f"  NEUTRAL: {signals['NEUTRAL']:>4} ({signals['NEUTRAL']/total*100:.1f}%)")


if __name__ == "__main__":
    main()