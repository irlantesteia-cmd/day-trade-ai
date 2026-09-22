"""Treina o modelo logistico usado pela MLSignalStrategy (v2).

Features: 10 (lags de retorno, formato de candle, volume relativo, ATR).
Label   : direcao do close em N candles a frente (default: 5).

Uso:
    python scripts/train_model.py                     # sintetico
    python scripts/train_model.py --from-mt5          # dados reais do MT5
    python scripts/train_model.py --from-mt5 --symbol "WIN$" --n 20000 --horizon 5
"""
import argparse
import os
import sys
from typing import Dict, List, Tuple

import joblib
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.logistic import LogisticRegressionModel


FEATURE_KEYS = [
    "return_1", "return_2", "return_3", "return_5",
    "body_pct", "range_pct",
    "upper_wick_pct", "lower_wick_pct",
    "vol_ratio_20", "atr_14_norm",
]


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------

def compute_features(
    bars: List[Dict],
    i: int,
    closes: List[float],
    volumes: List[float],
    trs: List[float],
) -> Dict[str, float]:
    """Computa features para a barra i usando historico pre-computado."""
    bar = bars[i]
    o, h, l, c, v = bar["open"], bar["high"], bar["low"], bar["close"], bar["volume"]

    feats: Dict[str, float] = {}

    # Retornos em lags
    for lag in (1, 2, 3, 5):
        if i - lag >= 0:
            past = closes[i - lag]
            feats[f"return_{lag}"] = (c - past) / past if past else 0.0
        else:
            feats[f"return_{lag}"] = 0.0

    # Formato do candle
    feats["body_pct"] = (c - o) / c if c else 0.0
    feats["range_pct"] = (h - l) / c if c else 0.0
    feats["upper_wick_pct"] = (h - max(o, c)) / c if c else 0.0
    feats["lower_wick_pct"] = (min(o, c) - l) / c if c else 0.0

    # Volume relativo (media de 20)
    if i >= 19:
        avg_vol = sum(volumes[i - 19:i + 1]) / 20.0
        feats["vol_ratio_20"] = v / avg_vol if avg_vol else 1.0
    else:
        feats["vol_ratio_20"] = 1.0

    # ATR normalizado (media de 14 TRs)
    if i >= 13:
        atr = sum(trs[i - 13:i + 1]) / 14.0
        feats["atr_14_norm"] = atr / c if c else 0.0
    else:
        feats["atr_14_norm"] = 0.0

    return feats


def precompute_indicators(bars: List[Dict]) -> Tuple[List[float], List[float], List[float]]:
    closes = [b["close"] for b in bars]
    volumes = [b["volume"] for b in bars]
    trs = []
    for i, b in enumerate(bars):
        prev_c = closes[i - 1] if i > 0 else b["close"]
        tr = max(b["high"] - b["low"],
                 abs(b["high"] - prev_c),
                 abs(b["low"] - prev_c))
        trs.append(tr)
    return closes, volumes, trs


# ---------------------------------------------------------------------------
# Fontes de dados
# ---------------------------------------------------------------------------

def generate_synthetic_bars(n: int = 5000) -> List[Dict]:
    """Barras sinteticas com momentum + micro-tendencia (para o modelo ter o que aprender)."""
    np.random.seed(42)
    price = 130000.0
    prev_ret = 0.0
    bars = []
    # Adiciona um componente ciclico para criar padrao previsivel
    for k in range(n):
        cycle = 0.0005 * np.sin(2 * np.pi * k / 200.0)
        ret = 0.3 * prev_ret + cycle + np.random.randn() * 0.0008
        o = price
        c = price * (1 + ret)
        h = max(o, c) * (1 + abs(np.random.randn()) * 0.0003)
        l = min(o, c) * (1 - abs(np.random.randn()) * 0.0003)
        v = float(np.random.randint(500, 3000))
        bars.append({"open": o, "high": h, "low": l, "close": c, "volume": v})
        price = c
        prev_ret = ret
    return bars


def fetch_mt5_bars(symbol: str, n: int) -> List[Dict]:
    import MetaTrader5 as mt5

    if not mt5.initialize():
        raise RuntimeError(f"mt5.initialize falhou: {mt5.last_error()}")

    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"Simbolo {symbol} nao encontrado")
        if not info.visible:
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Falha ao adicionar {symbol} ao Market Watch")

        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, n)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"Sem barras para {symbol}: {mt5.last_error()}")

        return [
            {
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r["tick_volume"]),
            }
            for r in rates
        ]
    finally:
        mt5.shutdown()


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

def build_dataset(bars: List[Dict], horizon: int = 5) -> Tuple[List[List[float]], List[int]]:
    closes, volumes, trs = precompute_indicators(bars)

    X: List[List[float]] = []
    y: List[int] = []

    # Precisamos de: i >= 20 (para vol_ratio_20) e i + horizon < len(bars)
    start = 20
    end = len(bars) - horizon

    for i in range(start, end):
        feats = compute_features(bars, i, closes, volumes, trs)
        X.append([feats[k] for k in FEATURE_KEYS])
        future_close = closes[i + horizon]
        y.append(1 if future_close > closes[i] else 0)

    return X, y


# ---------------------------------------------------------------------------
# Normalizacao (para estabilidade do gradiente)
# ---------------------------------------------------------------------------

def standardize(X_train: List[List[float]]) -> Tuple[List[List[float]], List[float], List[float]]:
    n_features = len(X_train[0])
    means = [0.0] * n_features
    stds = [1.0] * n_features

    for j in range(n_features):
        col = [row[j] for row in X_train]
        m = sum(col) / len(col)
        var = sum((x - m) ** 2 for x in col) / len(col)
        s = var ** 0.5 if var > 0 else 1.0
        means[j] = m
        stds[j] = s

    X_norm = [[(row[j] - means[j]) / stds[j] for j in range(n_features)] for row in X_train]
    return X_norm, means, stds


def apply_standardize(X: List[List[float]], means: List[float], stds: List[float]) -> List[List[float]]:
    return [[(row[j] - means[j]) / stds[j] for j in range(len(means))] for row in X]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Treina modelo logistico v2")
    parser.add_argument("--from-mt5", action="store_true")
    parser.add_argument("--symbol", default="WIN$")
    parser.add_argument("--n", type=int, default=5000)
    parser.add_argument("--horizon", type=int, default=5,
                        help="Candles a frente para o label (default: 5)")
    parser.add_argument("--output", default="models/logistic_v1.pkl")
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--lr", type=float, default=0.3)
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    if args.from_mt5:
        print(f"Buscando {args.n} barras de {args.symbol} no MT5...")
        bars = fetch_mt5_bars(args.symbol, args.n)
    else:
        print(f"Gerando {args.n} barras sinteticas...")
        bars = generate_synthetic_bars(args.n)

    print(f"Barras: {len(bars)}")
    X, y = build_dataset(bars, horizon=args.horizon)
    if not X:
        raise SystemExit("Dataset vazio. Abortando.")

    # Split treino/teste (walk-forward, sem shuffle!)
    split = int(len(X) * (1 - args.test_size))
    X_train_raw, X_test_raw = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # Normalizacao
    X_train, means, stds = standardize(X_train_raw)
    X_test = apply_standardize(X_test_raw, means, stds)

    n_pos = sum(y_train)
    print(f"Treino: {len(X_train)} amostras | {n_pos} positivos ({100.0 * n_pos / len(y_train):.1f}%)")
    print(f"Teste : {len(X_test)} amostras")

    print(f"Treinando (epochs={args.epochs}, lr={args.lr})...")
    model = LogisticRegressionModel(learning_rate=args.lr, epochs=args.epochs)
    model.fit(X_train, y_train)

    # Metricas treino
    preds_tr = model.predict(X_train, threshold=0.5)
    acc_tr = sum(1 for p, t in zip(preds_tr, y_train) if p == t) / len(y_train)

    # Metricas teste (out-of-sample)
    preds_te = model.predict(X_test, threshold=0.5)
    acc_te = sum(1 for p, t in zip(preds_te, y_test) if p == t) / len(y_test)
    baseline_te = max(sum(y_test) / len(y_test), 1 - sum(y_test) / len(y_test))

    print(f"Acuracia treino      : {acc_tr:.3f}")
    print(f"Acuracia teste (OOS) : {acc_te:.3f}")
    print(f"Baseline teste (maior classe): {baseline_te:.3f}")
    print(f"Edge sobre baseline  : {(acc_te - baseline_te) * 100:+.2f} p.p.")

    # Salva modelo + metadados
    joblib.dump(model, args.output)
    with open(args.output + ".keys", "w") as f:
        f.write(",".join(FEATURE_KEYS))
    with open(args.output + ".norm", "w") as f:
        f.write("means=" + ",".join(str(m) for m in means) + "\n")
        f.write("stds=" + ",".join(str(s) for s in stds) + "\n")

    print(f"Modelo salvo: {args.output}")
    print(f"Feature keys: {args.output}.keys")
    print(f"Normalizacao: {args.output}.norm")
    print(f"weights={model.weights}")
    print(f"bias={model.bias}")


if __name__ == "__main__":
    main()