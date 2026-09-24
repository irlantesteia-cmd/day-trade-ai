"""Benchmark de previsao de VOLATILIDADE (nao-direcional).

Diferente do benchmark de estrategias (ADR-019) e do ML direcional
(ADR-012/014), este testa se e possivel prever "vai ter movimento
GRANDE no proximo horizonte", independente de direcao.

Target binario:
    label = 1 se |close[t+H] - close[t]| / close[t] > threshold
    label = 0 caso contrario

Threshold: mediana dos movimentos absolutos (auto-balanceia classes).

Features: 4 features de volatilidade (src/features/volatility.py).

Modelo: LogisticRegressionModel (mesmo do pipeline ML).

Uso:
    python scripts/benchmark_volatility.py --from-mt5 --symbol WINV26 --timeframe M5
    python scripts/benchmark_volatility.py --from-mt5 --symbol PETR4 --timeframe M5
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

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
from src.features.volatility import (
    BollingerWidthExtractor,
    RangeRatioExtractor,
    RealizedVolatilityExtractor,
    VolatilityRatioExtractor,
)
from src.models.logistic import LogisticRegressionModel


FEATURE_EXTRACTORS = [
    RealizedVolatilityExtractor(period=20),
    VolatilityRatioExtractor(short_period=5, long_period=20),
    RangeRatioExtractor(period=14),
    BollingerWidthExtractor(period=20),
]


FEATURE_KEYS = [
    "realized_vol_20",
    "vol_ratio_5_20",
    "range_ratio_14",
    "bb_width_20",
]


# ---------------------------------------------------------------------------
# Dados (mesmas funcoes do benchmark_strategies)
# ---------------------------------------------------------------------------

def candles_sinteticos(n: int = 5000) -> List[Candle]:
    """AR(1) puro com volatilidade constante (sem clustering)."""
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
# Construcao de dataset
# ---------------------------------------------------------------------------

def extract_features_at(
    candles: List[Candle],
    i: int,
) -> Optional[Dict[str, float]]:
    """Extrai as 4 features de volatilidade usando candles[:i+1]."""
    window = candles[: i + 1]
    feats: Dict[str, float] = {}
    for ext in FEATURE_EXTRACTORS:
        out = ext.extract(window, None)
        for k, v in out.items():
            if v is None:
                return None
            feats[k] = v
    return feats


def build_dataset(
    candles: List[Candle],
    horizon: int = 5,
    min_history: int = 25,
) -> Tuple[List[List[float]], List[int], float]:
    """
    Retorna (X, y, threshold_usado).

    Threshold: mediana dos movimentos absolutos futuros (balanceia classes).
    """
    if len(candles) < min_history + horizon + 10:
        return [], [], 0.0

    closes = [c.close for c in candles]

    # 1. Passo 1: calcular movimentos futuros absolutos (para threshold)
    future_moves: List[float] = []
    for i in range(min_history, len(candles) - horizon):
        c_now = closes[i]
        c_future = closes[i + horizon]
        if c_now > 0:
            future_moves.append(abs(c_future - c_now) / c_now)

    if not future_moves:
        return [], [], 0.0

    threshold = float(np.median(future_moves))

    # 2. Passo 2: extrair features + label
    X: List[List[float]] = []
    y: List[int] = []

    for i in range(min_history, len(candles) - horizon):
        feats = extract_features_at(candles, i)
        if feats is None:
            continue

        c_now = closes[i]
        c_future = closes[i + horizon]
        if c_now <= 0:
            continue

        move = abs(c_future - c_now) / c_now
        label = 1 if move > threshold else 0

        X.append([feats[k] for k in FEATURE_KEYS])
        y.append(label)

    return X, y, threshold


# ---------------------------------------------------------------------------
# Padronizacao
# ---------------------------------------------------------------------------

def fit_scaler(X: List[List[float]]) -> Tuple[List[float], List[float]]:
    n_features = len(X[0])
    means = [0.0] * n_features
    stds = [1.0] * n_features
    for j in range(n_features):
        col = [row[j] for row in X]
        m = sum(col) / len(col)
        var = sum((x - m) ** 2 for x in col) / len(col)
        s = var ** 0.5 if var > 0 else 1.0
        means[j] = m
        stds[j] = s
    return means, stds


def apply_scaler(X: List[List[float]], means: List[float], stds: List[float]) -> List[List[float]]:
    return [[(row[j] - means[j]) / stds[j] for j in range(len(means))] for row in X]


# ---------------------------------------------------------------------------
# Walk-forward
# ---------------------------------------------------------------------------

def walk_forward(
    X: List[List[float]],
    y: List[int],
    train_window: int = 500,
    test_window: int = 100,
    epochs: int = 500,
    lr: float = 0.3,
) -> List[Dict[str, Any]]:
    folds: List[Dict[str, Any]] = []
    n = len(X)

    start = 0
    while start + train_window + test_window <= n:
        tr_end = start + train_window
        te_end = tr_end + test_window

        X_tr_raw = X[start:tr_end]
        y_tr = y[start:tr_end]
        X_te_raw = X[tr_end:te_end]
        y_te = y[tr_end:te_end]

        means, stds = fit_scaler(X_tr_raw)
        X_tr = apply_scaler(X_tr_raw, means, stds)
        X_te = apply_scaler(X_te_raw, means, stds)

        model = LogisticRegressionModel(learning_rate=lr, epochs=epochs)
        model.fit(X_tr, y_tr)

        preds = model.predict(X_te, threshold=0.5)
        acc = sum(1 for p, t in zip(preds, y_te) if p == t) / len(y_te)
        pos_rate = sum(y_te) / len(y_te)
        baseline = max(pos_rate, 1 - pos_rate)
        edge_pp = (acc - baseline) * 100.0

        folds.append({
            "start": start,
            "acc": round(acc, 4),
            "baseline": round(baseline, 4),
            "pos_rate": round(pos_rate, 4),
            "edge_pp": round(edge_pp, 2),
            "n_test": len(y_te),
        })

        start += test_window

    return folds


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Benchmark de volatilidade (nao-direcional)")
    parser.add_argument("--from-mt5", action="store_true")
    parser.add_argument("--symbol", default="WINV26")
    parser.add_argument("--timeframe", choices=list(TIMEFRAME_MAP.keys()), default="M5")
    parser.add_argument("--n", type=int, default=20000)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--min-history", type=int, default=25)
    parser.add_argument("--wf-train", type=int, default=500)
    parser.add_argument("--wf-test", type=int, default=100)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--lr", type=float, default=0.3)
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

    # 2. Dataset
    X, y, threshold = build_dataset(
        candles,
        horizon=args.horizon,
        min_history=args.min_history,
    )

    if not X:
        raise SystemExit("Dataset vazio. Aumente --n.")

    n_pos = sum(y)
    print(f"Dataset: {len(X)} amostras | {n_pos} positivos ({100*n_pos/len(y):.1f}%)")
    print(f"Threshold de movimento: {threshold:.6f} ({threshold*100:.3f}%)")
    print(f"Features: {FEATURE_KEYS}")

    # 3. Walk-forward
    print(f"\nWalk-forward (train={args.wf_train}, test={args.wf_test})...")
    folds = walk_forward(
        X, y,
        train_window=args.wf_train,
        test_window=args.wf_test,
        epochs=args.epochs,
        lr=args.lr,
    )

    if not folds:
        raise SystemExit("Walk-forward nao gerou folds.")

    print(f"\n{'Fold':>4} | {'Acc':>6} | {'Baseline':>8} | {'Edge pp':>8} | {'N':>6}")
    print("-" * 50)
    for i, f in enumerate(folds):
        print(f"{i:>4} | {f['acc']:>6.4f} | {f['baseline']:>8.4f} | {f['edge_pp']:>+8.2f} | {f['n_test']:>6}")

    edges = [f["edge_pp"] for f in folds]
    mean_edge = sum(edges) / len(edges)
    pos_folds = sum(1 for e in edges if e > 0)
    print("-" * 50)
    print(f"Edge medio: {mean_edge:+.2f} p.p. | Folds positivos: {pos_folds}/{len(edges)}")

    # 4. Salvar
    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = os.path.join(args.out_dir, f"volatility_{args.symbol}_{args.timeframe}_{ts}.json")
    results = {
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "source": "mt5" if args.from_mt5 else "synthetic",
        "n_candles": len(candles),
        "horizon": args.horizon,
        "threshold": threshold,
        "n_samples": len(X),
        "positive_rate": n_pos / len(y),
        "feature_keys": FEATURE_KEYS,
        "mean_edge_pp": round(mean_edge, 2),
        "positive_folds": pos_folds,
        "total_folds": len(folds),
        "folds": folds,
    }
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(results, fp, indent=2, default=str)
    print(f"\nResultado salvo em: {out_path}")


if __name__ == "__main__":
    main()