"""
Benchmark de estrategias em cripto via Binance.

Reusa a logica de walk-forward do benchmark_strategies.py, mas
troca a fonte de dados para Binance (API publica).

Uso:
    python scripts/benchmark_crypto.py --symbol BTCUSDT --timeframe M5
    python scripts/benchmark_crypto.py --symbol ETHUSDT --timeframe M15 --n 5000
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from src.adapters.binance_adapter import BinanceDataProvider
from src.domain.enums import Timeframe
from src.domain.models import Candle
from src.indicators.engine import IndicatorEngine
from src.strategies.moving_average import MovingAverageCrossoverStrategy
from src.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from scripts.benchmark_strategies import (
    signal_to_label,
    walk_forward_accuracy,
)


TIMEFRAME_MAP = {
    "M1":  Timeframe.M1,
    "M5":  Timeframe.M5,
    "M15": Timeframe.M15,
    "H1":  Timeframe.H1,
    "D1":  Timeframe.D1,
}


def fetch_binance_bars(
    symbol: str,
    timeframe: str,
    n: int,
) -> List[Candle]:
    """Busca N candles mais recentes da Binance."""
    tf = TIMEFRAME_MAP[timeframe]
    # Binance limita 1000 por request; para n>1000, fazemos paginacao
    provider = BinanceDataProvider()
    try:
        if n <= 1000:
            return provider.fetch_latest_bars(symbol, tf, n=n)

        # Paginacao: busca em chunks de 1000, cada vez mais antigos
        all_bars: List[Candle] = []
        remaining = n
        # endTime nao e suportado em fetch_latest_bars; usamos fetch_candles
        from datetime import timedelta
        end = datetime.now(timezone.utc)
        while remaining > 0:
            chunk = min(1000, remaining)
            start = end - timedelta(minutes=chunk * _tf_minutes(timeframe) + 5)
            bars = provider.fetch_candles(symbol, tf, start, end, limit=chunk)
            if not bars:
                break
            all_bars = bars + all_bars
            end = bars[0].timestamp
            remaining -= len(bars)
            if len(bars) < chunk:
                break
        return all_bars[-n:]
    finally:
        provider.close()


def _tf_minutes(tf: str) -> int:
    mapping = {"M1": 1, "M5": 5, "M15": 15, "H1": 60, "D1": 1440}
    return mapping.get(tf, 5)


def strategy_predictions(
    candles: List[Candle],
    strategy: Any,
    indicator_engine: IndicatorEngine,
    min_history: int = 30,
    horizon: int = 5,
) -> List[Dict[str, Any]]:
    """Adaptado de benchmark_strategies.py para aceitar Candle."""
    if len(candles) <= min_history + horizon:
        return []

    closes = [c.close for c in candles]
    predictions: List[Dict[str, Any]] = []

    for i in range(min_history, len(candles) - horizon):
        window = candles[: i + 1]
        try:
            indicators = indicator_engine.compute_all(window)
            sig = strategy.evaluate(window, indicators, None)
        except Exception:
            continue

        label = signal_to_label(sig)
        actual = 1 if closes[i + horizon] > closes[i] else 0

        predictions.append({
            "index": i,
            "label": label,
            "actual": actual,
            "timestamp": candles[i].timestamp,
        })

    return predictions


def build_strategies() -> Dict[str, Any]:
    return {
        "MA_CROSSOVER": MovingAverageCrossoverStrategy(),
        "RSI_REVERSION": RSIMeanReversionStrategy(rsi_key="rsi"),
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark de estrategias em cripto")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--timeframe", choices=list(TIMEFRAME_MAP.keys()), default="M5")
    parser.add_argument("--n", type=int, default=5000)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--min-history", type=int, default=30)
    parser.add_argument("--test-window", type=int, default=100)
    parser.add_argument("--out-dir", default="models/benchmarks")
    args = parser.parse_args()

    print(f"Buscando {args.n} candles de {args.symbol} ({args.timeframe}) na Binance...")
    candles = fetch_binance_bars(args.symbol, args.timeframe, args.n)
    print(f"Candles: {len(candles)}")
    if candles:
        print(f"  Range: {candles[0].timestamp.isoformat()} -> {candles[-1].timestamp.isoformat()}")
        print(f"  Close inicial: {candles[0].close:.2f} | Close final: {candles[-1].close:.2f}")

    strategies = build_strategies()
    indicator_engine = IndicatorEngine()

    results: Dict[str, Any] = {
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "source": "binance",
        "n_candles": len(candles),
        "horizon": args.horizon,
        "test_window": args.test_window,
        "strategies": {},
    }

    print(f"\n{'Estrategia':<16} | {'Folds':>5} | {'Edge medio':>10} | {'Folds +':>8} | {'Total preds':>11}")
    print("-" * 66)

    for name, strategy in strategies.items():
        preds = strategy_predictions(
            candles, strategy, indicator_engine,
            min_history=args.min_history, horizon=args.horizon,
        )
        if not preds:
            print(f"{name:<16} | {'0':>5} | {'-':>10} | {'-':>8} | {'0':>11}")
            continue

        folds = walk_forward_accuracy(preds, test_window=args.test_window)
        if not folds:
            print(f"{name:<16} | {'0':>5} | {'-':>10} | {'-':>8} | {'0':>11}")
            continue

        edges = [f["edge_pp"] for f in folds]
        mean_edge = sum(edges) / len(edges)
        pos_folds = sum(1 for e in edges if e > 0)
        total_preds = sum(f["n_predictions"] for f in folds)

        print(f"{name:<16} | {len(folds):>5} | {mean_edge:>+10.2f} | {pos_folds:>3}/{len(folds):<3} | {total_preds:>11}")

        results["strategies"][name] = {
            "n_predictions_total": total_preds,
            "n_folds": len(folds),
            "mean_edge_pp": round(mean_edge, 2),
            "positive_folds": pos_folds,
            "folds": folds,
        }

    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = os.path.join(args.out_dir, f"benchmark_crypto_{args.symbol}_{args.timeframe}_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResultado salvo em: {out_path}")


if __name__ == "__main__":
    main()