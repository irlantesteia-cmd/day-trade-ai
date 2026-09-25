"""Teste do EnsembleLiveAdapter end-to-end."""
import sys
import os
from datetime import datetime, timezone, timedelta
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.domain.enums import Timeframe
from src.indicators.engine import IndicatorEngine
from src.strategies.ensemble_strategy import EnsembleStrategy
from src.strategies.ensemble_live_adapter import EnsembleLiveAdapter


def main():
    internal = EnsembleStrategy(mode="vote", min_agreement=0.5)
    engine = IndicatorEngine()
    adapter = EnsembleLiveAdapter(
        internal_strategy=internal,
        indicator_engine=engine,
        max_buffer=200,
        min_history=50,
    )

    # Simula 100 bars como dicts (mesmo formato do MT5Adapter.fetch_latest_bar)
    np.random.seed(42)
    base_ts = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
    price = 130000.0
    prev_ret = 0.0
    signals = {"BUY": 0, "SELL": 0, "NEUTRAL": 0, "NONE": 0}

    for i in range(100):
        ret = 0.0001 + 0.3 * prev_ret + np.random.randn() * 0.0005
        o = price
        c = price * (1 + ret)
        h = max(o, c) * 1.0003
        l = min(o, c) * 0.9997
        bar = {
            "symbol": "WIN$",
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": 1000.0,
            "timestamp": base_ts + 300 * i,
        }
        sig = adapter.generate_signal(bar)
        if sig is None:
            signals["NONE"] += 1
        else:
            d = str(getattr(sig.direction, "value", sig.direction)).upper()
            if "BUY" in d:
                signals["BUY"] += 1
            elif "SELL" in d:
                signals["SELL"] += 1
            else:
                signals["NEUTRAL"] += 1
        price = c
        prev_ret = ret

    print(f"Buffer final: {adapter.buffer_size()}")
    print(f"Signals gerados:")
    for k, v in signals.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()