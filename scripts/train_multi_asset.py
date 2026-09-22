"""
Treina modelos por (symbol, timeframe) e salva em models/multi/{symbol}_{tf}.pkl.
Usa features enriquecidas + label de horizonte + regime.
"""
import os
import sys
import argparse
from typing import Dict, List, Tuple

import joblib
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.adapters.multi_market_adapter import MultiMarketAdapter
from src.models.logistic import LogisticRegressionModel


FEATURE_KEYS = [
    "return_1", "return_2", "return_3", "return_5",
    "body_pct", "range_pct",
    "upper_wick_pct", "lower_wick_pct",
    "vol_ratio_20", "atr_14_norm",
    "regime_calm", "regime_normal", "regime_volatile",
]


def compute_features(bars, i):
    closes = [b["close"] for b in bars]
    vols = [b["volume"] for b in bars]
    c = closes[i]
    o, h, l = bars[i]["open"], bars[i]["high"], bars[i]["low"]

    feats = {}
    for lag in (1, 2, 3, 5):
        if i - lag >= 0:
            feats[f"return_{lag}"] = (c - closes[i - lag]) / closes[i - lag] if closes[i - lag] else 0.0
        else:
            feats[f"return_{lag}"] = 0.0
    feats["body_pct"] = (c - o) / c if c else 0.0
    feats["range_pct"] = (h - l) / c if c else 0.0
    feats["upper_wick_pct"] = (h - max(o, c)) / c if c else 0.0
    feats["lower_wick_pct"] = (min(o, c) - l) / c if c else 0.0

    if i >= 20:
        avg_vol = sum(vols[i - 19:i + 1]) / 20.0
        feats["vol_ratio_20"] = vols[i] / avg_vol if avg_vol else 1.0
    else:
        feats["vol_ratio_20"] = 1.0

    if i >= 14:
        trs = [max(bars[j]["high"] - bars[j]["low"],
                   abs(bars[j]["high"] - closes[j - 1]),
                   abs(bars[j]["low"] - closes[j - 1]))
               for j in range(i - 13, i + 1)]
        atr = sum(trs) / 14.0
        feats["atr_14_norm"] = atr / c if c else 0.0
    else:
        feats["atr_14_norm"] = 0.0

    # Regime one-hot
    atr_norm = feats["atr_14_norm"]
    if atr_norm < 0.001:
        regime = 0
    elif atr_norm > 0.003:
        regime = 2
    else:
        regime = 1
    feats["regime_calm"] = 1.0 if regime == 0 else 0.0
    feats["regime_normal"] = 1.0 if regime == 1 else 0.0
    feats["regime_volatile"] = 1.0 if regime == 2 else 0.0
    return feats


def build_dataset(bars: List[dict], horizon: int = 5) -> Tuple[List, List]:
    X, y = [], []
    for i in range(20, len(bars) - horizon):
        feats = compute_features(bars, i)
        X.append([feats[k] for k in FEATURE_KEYS])
        y.append(1 if bars[i + horizon]["close"] > bars[i]["close"] else 0)
    return X, y


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=["WIN$", "WDO$", "PETR4", "VALE3"])
    parser.add_argument("--timeframes", nargs="+", default=["M1", "M5", "M15", "M30", "H1"])
    parser.add_argument("--n", type=int, default=5000)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--out-dir", default="models/multi")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    adapter = MultiMarketAdapter(args.symbols, args.timeframes)
    if not adapter.initialize():
        raise SystemExit("Falha ao conectar MT5")

    results = []
    for sym in args.symbols:
        for tf in args.timeframes:
            print(f"\n=== {sym} {tf} ===")
            bars = adapter.fetch_bars(sym, tf, n=args.n)
            if len(bars) < 100:
                print(f"  Barras insuficientes: {len(bars)}")
                continue

            X, y = build_dataset(bars, horizon=args.horizon)
            if len(X) < 200:
                print(f"  Dataset pequeno: {len(X)}")
                continue

            split = int(len(X) * 0.8)
            X_tr, X_te = X[:split], X[split:]
            y_tr, y_te = y[:split], y[split:]

            model = LogisticRegressionModel(learning_rate=0.3, epochs=500)
            model.fit(X_tr, y_tr)

            acc_tr = sum(1 for p, t in zip(model.predict(X_tr), y_tr) if p == t) / len(y_tr)
            acc_te = sum(1 for p, t in zip(model.predict(X_te), y_te) if p == t) / len(y_te)
            baseline = max(sum(y_te)/len(y_te), 1 - sum(y_te)/len(y_te))

            print(f"  Treino: {acc_tr:.3f} | Teste: {acc_te:.3f} | Baseline: {baseline:.3f} | Edge: {(acc_te-baseline)*100:+.2f}p.p.")
            results.append((sym, tf, acc_te, baseline))

            path = os.path.join(args.out_dir, f"{sym}_{tf}.pkl")
            joblib.dump(model, path)
            with open(path + ".keys", "w") as f:
                f.write(",".join(FEATURE_KEYS))

    adapter.shutdown()

    print("\n=== RESUMO ===")
    for sym, tf, acc, base in results:
        edge = (acc - base) * 100
        flag = "✅" if edge > 1.0 else ("⚠️" if edge > 0 else "❌")
        print(f"{flag} {sym:8s} {tf:4s} acc={acc:.3f} edge={edge:+.2f}p.p.")


if __name__ == "__main__":
    main()