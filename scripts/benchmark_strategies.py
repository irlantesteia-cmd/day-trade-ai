"""Benchmark de estrategias nao-ML via walk-forward.

Roda estrategias ja implementadas (MovingAverageCrossover, RSIMeanReversion)
contra dados reais do MT5 usando o mesmo walk-forward do pipeline ML
(scripts/train_model_v3.py).

Objetivo: responder "alguma estrategia existente tem edge em WINV26 M5/M15?"

Uso:
    python scripts/benchmark_strategies.py --from-mt5 --symbol WINV26 --timeframe M5
    python scripts/benchmark_strategies.py --from-mt5 --symbol WINV26 --timeframe M15
    python scripts/benchmark_strategies.py  # sintetico, rapido
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


TIMEFRAME_MAP = {
    "M1":  "TIMEFRAME_M1",
    "M5":  "TIMEFRAME_M5",
    "M15": "TIMEFRAME_M15",
    "M30": "TIMEFRAME_M30",
    "H1":  "TIMEFRAME_H1",
}


from src.domain.models import Candle
from src.indicators.engine import IndicatorEngine
from src.strategies.moving_average import MovingAverageCrossoverStrategy
from src.strategies.rsi_mean_reversion import RSIMeanReversionStrategy


# ---------------------------------------------------------------------------
# Fontes de dados (mesmas do train_model_v3)
# ---------------------------------------------------------------------------

def candles_sinteticos(n: int = 5000) -> List[Candle]:
    """AR(1) puro, sem ciclo (ADR-013)."""
    from datetime import timedelta
    np.random.seed(42)
    price = 130000.0
    prev_ret = 0.0
    base_ts = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    candles: List[Candle] = []
    for i in range(n):
        ret = 0.3 * prev_ret + np.random.randn() * 0.0008
        o = price
        c = price * (1 + ret)
        h = max(o, c) * (1 + abs(np.random.randn()) * 0.0003)
        l = min(o, c) * (1 - abs(np.random.randn()) * 0.0003)
        v = float(np.random.randint(500, 3000))
        candles.append(Candle(
            symbol="SYNTH",
            timestamp=base_ts + timedelta(minutes=i),
            open=o, high=h, low=l, close=c, volume=v,
        ))
        price = c
        prev_ret = ret
    return candles


def candles_mt5(symbol: str, n: int, timeframe: str = "M1") -> List[Candle]:
    from datetime import datetime, timezone
    import MetaTrader5 as mt5

    if timeframe not in TIMEFRAME_MAP:
        raise ValueError(f"Timeframe invalido: {timeframe}")

    tf_const = getattr(mt5, TIMEFRAME_MAP[timeframe])

    if not mt5.initialize():
        raise RuntimeError(f"mt5.initialize falhou: {mt5.last_error()}")
    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"Simbolo {symbol} nao encontrado")
        if not info.visible:
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Falha ao adicionar {symbol}")

        rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, n)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"Sem barras para {symbol} {timeframe}")

        return [
            Candle(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(int(r["time"]), tz=timezone.utc),
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
                volume=float(r["tick_volume"]),
            )
            for r in rates
        ]
    finally:
        mt5.shutdown()


# ---------------------------------------------------------------------------
# Extracao de label do Signal
# ---------------------------------------------------------------------------

def signal_to_label(sig: Any) -> Optional[int]:
    """
    Converte um Signal em 1 (BUY), 0 (SELL) ou None (NEUTRAL).

    Trata tanto SignalDirection quanto SignalType (ambos tem .value).
    """
    if sig is None:
        return None
    direction = getattr(sig, "direction", None)
    if direction is None:
        direction = getattr(sig, "type", None)
    if direction is None:
        return None
    val = str(getattr(direction, "value", direction)).upper()
    if "BUY" in val:
        return 1
    if "SELL" in val:
        return 0
    return None


# ---------------------------------------------------------------------------
# Predicoes por candle
# ---------------------------------------------------------------------------

def strategy_predictions(
    candles: List[Candle],
    strategy: Any,
    indicator_engine: IndicatorEngine,
    min_history: int = 30,
    horizon: int = 5,
) -> List[Dict[str, Any]]:
    """
    Para cada candle i a partir de min_history, gera Signal via strategy.evaluate
    e compara com direcao real em i+horizon.

    Retorna lista de:
        {"index": i, "label": 1|0|None, "actual": 1|0, "timestamp": dt}
    """
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


# ---------------------------------------------------------------------------
# Walk-forward accuracy
# ---------------------------------------------------------------------------

def walk_forward_accuracy(
    predictions: List[Dict[str, Any]],
    test_window: int = 100,
    min_predictions_per_fold: int = 5,
) -> List[Dict[str, Any]]:
    """
    Divide as predicoes em folds de tamanho test_window. Em cada fold:
      - consideram-se apenas candles em que a estrategia gerou BUY ou SELL
        (label != None)
      - acc = corretos / n
      - baseline = max(rate_up, rate_down) no mesmo subconjunto
      - edge_pp = (acc - baseline) * 100

    Folds com menos de min_predictions_per_fold predicoes nao-None sao
    ignorados.
    """
    folds: List[Dict[str, Any]] = []

    for start in range(0, len(predictions), test_window):
        chunk = predictions[start : start + test_window]
        active = [p for p in chunk if p["label"] is not None]

        if len(active) < min_predictions_per_fold:
            continue

        n = len(active)
        correct = sum(1 for p in active if p["label"] == p["actual"])
        acc = correct / n

        actuals = [p["actual"] for p in active]
        pos_rate = sum(actuals) / n
        baseline = max(pos_rate, 1.0 - pos_rate)
        edge_pp = (acc - baseline) * 100.0

        folds.append({
            "start": start,
            "n_predictions": n,
            "acc": round(acc, 4),
            "baseline": round(baseline, 4),
            "edge_pp": round(edge_pp, 2),
            "pos_rate": round(pos_rate, 4),
        })

    return folds


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_strategies() -> Dict[str, Any]:
    """Instancia as estrategias compativeis com IndicatorEngine.compute_all."""
    return {
        "MA_CROSSOVER": MovingAverageCrossoverStrategy(),
        "RSI_REVERSION": RSIMeanReversionStrategy(rsi_key="rsi"),
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark de estrategias nao-ML")
    parser.add_argument("--from-mt5", action="store_true")
    parser.add_argument("--symbol", default="WINV26")
    parser.add_argument(
        "--timeframe",
        choices=list(TIMEFRAME_MAP.keys()),
        default="M5",
    )
    parser.add_argument("--n", type=int, default=20000)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--min-history", type=int, default=30)
    parser.add_argument("--test-window", type=int, default=100)
    parser.add_argument("--out-dir", default="models/benchmarks")
    args = parser.parse_args()

    # 1. Dados
    if args.from_mt5:
        print(f"Buscando {args.n} candles de {args.symbol} ({args.timeframe})...")
        candles = candles_mt5(args.symbol, args.n, args.timeframe)
    else:
        print(f"Gerando {args.n} candles sinteticos...")
        candles = candles_sinteticos(args.n)

    print(f"Candles: {len(candles)}")

    # 2. Estrategias
    strategies = build_strategies()
    indicator_engine = IndicatorEngine()

    # 3. Para cada estrategia
    results: Dict[str, Any] = {
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "source": "mt5" if args.from_mt5 else "synthetic",
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

    # 4. Salvar
    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = os.path.join(
        args.out_dir,
        f"benchmark_{args.symbol}_{args.timeframe}_{ts}.json",
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResultado salvo em: {out_path}")


if __name__ == "__main__":
    main()