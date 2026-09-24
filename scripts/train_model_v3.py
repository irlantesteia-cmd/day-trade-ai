"""Treino v3 - usa o pipeline oficial (features, dataset, registry).

Caracteristicas:
  - Features via src/features/sets.py (FeatureSetRegistry)
  - Dataset via src/models/dataset.py (DatasetBuilder)
  - Walk-forward validation via src/validation/splitter.py
  - Modelo versionado via src/models/registry.py (ModelRegistry)

Uso:
    python scripts/train_model_v3.py                        # basic, sintetico
    python scripts/train_model_v3.py --from-mt5             # basic, MT5
    python scripts/train_model_v3.py --from-mt5 --feature-set technical
"""
import argparse
import os
import sys
from typing import Dict, List, Tuple

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.domain.models import Candle
from src.features.sets import (
    FeatureSetRegistry,
    records_from_candles,
    records_from_candles_with_indicators,
    register_default_sets,
)
from src.indicators.engine import IndicatorEngine
from src.models.dataset import DatasetBuilder
from src.models.logistic import LogisticRegressionModel
from src.models.registry import ModelMetadata, ModelRegistry
from src.validation.splitter import WalkForwardSplitter


# ---------------------------------------------------------------------------
# Padronizacao (z-score)
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
    return [
        [(row[j] - means[j]) / stds[j] for j in range(len(means))]
        for row in X
    ]


# ---------------------------------------------------------------------------
# Fontes de dados
# ---------------------------------------------------------------------------

def candles_sinteticos(n: int = 5000) -> List[Candle]:
    """
    Candles sinteticos realistas: AR(1) de retornos com ruido.

    NAO inclui ciclo senoidal (removido no ADR-013). O ciclo anterior
    era detectado por RSI/SMA/ATR e inflava artificialmente o edge
    no walk-forward (edge sintetico +17 p.p. vs. MT5 real -9.40 p.p.).

    Caracteristicas:
      - ret[t] = 0.3 * ret[t-1] + N(0, 0.0008)   (inercia fraca + ruido)
      - Sem componente deterministica
      - Volatilidade similar ao WIN$ M1 em escala relativa
    """
    from datetime import datetime, timedelta
    np.random.seed(42)
    price = 130000.0
    prev_ret = 0.0
    base_ts = datetime(2026, 1, 1, 9, 0, 0)
    candles: List[Candle] = []
    for i in range(n):
        # AR(1) puro, sem ciclo
        ret = 0.3 * prev_ret + np.random.randn() * 0.0008
        o = price
        c = price * (1 + ret)
        h = max(o, c) * (1 + abs(np.random.randn()) * 0.0003)
        l = min(o, c) * (1 - abs(np.random.randn()) * 0.0003)
        v = float(np.random.randint(500, 3000))
        candles.append(
            Candle(
                symbol="SYNTH",
                timestamp=base_ts + timedelta(minutes=i),
                open=o,
                high=h,
                low=l,
                close=c,
                volume=v,
            )
        )
        price = c
        prev_ret = ret
    return candles


def candles_mt5(symbol: str, n: int) -> List[Candle]:
    from datetime import datetime, timezone
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

        candles: List[Candle] = []
        for r in rates:
            ts = datetime.fromtimestamp(int(r["time"]), tz=timezone.utc)
            candles.append(
                Candle(
                    symbol=symbol,
                    timestamp=ts,
                    open=float(r["open"]),
                    high=float(r["high"]),
                    low=float(r["low"]),
                    close=float(r["close"]),
                    volume=float(r["tick_volume"]),
                )
            )
        return candles
    finally:
        mt5.shutdown()


# ---------------------------------------------------------------------------
# Avaliacao
# ---------------------------------------------------------------------------

def evaluate_model(model, X_test, y_test) -> Dict[str, float]:
    if not X_test:
        return {"acc": 0.0, "baseline": 0.0, "edge_pp": 0.0, "n": 0.0}

    preds = model.predict(X_test, threshold=0.5)
    acc = sum(1 for p, t in zip(preds, y_test) if p == t) / len(y_test)
    baseline = max(sum(y_test) / len(y_test), 1 - sum(y_test) / len(y_test))
    edge_pp = (acc - baseline) * 100.0
    return {
        "acc": round(acc, 4),
        "baseline": round(baseline, 4),
        "edge_pp": round(edge_pp, 2),
        "n": float(len(y_test)),
    }


# ---------------------------------------------------------------------------
# Walk-forward
# ---------------------------------------------------------------------------

def run_walk_forward(
    X: List[List[float]],
    y: List[int],
    train_window: int,
    test_window: int,
    epochs: int,
    lr: float,
) -> List[Dict]:
    splitter = WalkForwardSplitter(
        train_window=train_window,
        test_window=test_window,
    )
    indices = list(range(len(X)))
    splits = splitter.split(indices)

    results: List[Dict] = []
    for i, sp in enumerate(splits):
        tr_slice = sp.train_data
        te_slice = sp.test_data

        X_tr_raw = [X[k] for k in tr_slice]
        y_tr = [y[k] for k in tr_slice]
        X_te_raw = [X[k] for k in te_slice]
        y_te = [y[k] for k in te_slice]

        if not X_tr_raw or not X_te_raw:
            continue

        means, stds = fit_scaler(X_tr_raw)
        X_tr = apply_scaler(X_tr_raw, means, stds)
        X_te = apply_scaler(X_te_raw, means, stds)

        model = LogisticRegressionModel(learning_rate=lr, epochs=epochs)
        model.fit(X_tr, y_tr)
        res = evaluate_model(model, X_te, y_te)
        res["fold"] = i
        results.append(res)

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Treino v3 - pipeline completo")
    parser.add_argument("--from-mt5", action="store_true")
    parser.add_argument("--symbol", default="WIN$")
    parser.add_argument("--n", type=int, default=5000)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.0)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--lr", type=float, default=0.3)
    parser.add_argument("--wf-train", type=int, default=500)
    parser.add_argument("--wf-test", type=int, default=100)
    parser.add_argument(
        "--feature-set",
        choices=["basic", "technical"],
        default="basic",
        help="Qual FeatureSet usar (basic v1 ou technical v1)",
    )
    parser.add_argument("--model-id", default=None,
                        help="Default: logistic_v3_<feature_set>")
    parser.add_argument("--model-version", default="v1")
    parser.add_argument("--registry-dir", default="models/registry")
    args = parser.parse_args()

    model_id = args.model_id or f"logistic_v3_{args.feature_set}"

    # 1. Carregar candles
    if args.from_mt5:
        print(f"Buscando {args.n} candles de {args.symbol} no MT5...")
        candles = candles_mt5(args.symbol, args.n)
    else:
        print(f"Gerando {args.n} candles sinteticos...")
        candles = candles_sinteticos(args.n)

    print(f"Candles: {len(candles)}")

    # 2. Selecionar feature set + metodo de geracao de records
    reg = FeatureSetRegistry()
    register_default_sets(reg)

    if args.feature_set == "technical":
        fs = reg.get("technical", "v1")
        indicator_engine = IndicatorEngine()
        records = records_from_candles_with_indicators(
            candles, fs, indicator_engine, min_history=30
        )
        print(f"FeatureSet: {fs.name} v{fs.version} ({len(fs.feature_keys)} features)")
        print(f"Records gerados (com indicadores): {len(records)}")
    else:
        fs = reg.get("basic", "v1")
        records = records_from_candles(candles, fs, min_history=6)
        print(f"FeatureSet: {fs.name} v{fs.version} ({len(fs.feature_keys)} features)")
        print(f"Records gerados: {len(records)}")

    # 3. Construir dataset
    dataset_version = (
        f"{fs.name}_{fs.version}_h{args.horizon}_t{args.threshold}_{len(records)}"
    )
    builder = DatasetBuilder(
        target_horizon=args.horizon,
        threshold=args.threshold,
        dataset_version=dataset_version,
    )
    ds = builder.build_binary_classification_dataset(
        records=records,
        feature_keys=fs.feature_keys,
        price_key="close",
    )
    summary = ds.summary()
    print(
        f"Dataset: {summary['n_samples']} amostras | "
        f"{summary['n_positives']} positivos "
        f"({100.0 * summary['positive_rate']:.1f}%) | "
        f"version={summary['dataset_version']}"
    )

    # 4. Walk-forward
    print(f"\nWalk-forward (train={args.wf_train}, test={args.wf_test})...")
    wf_results = run_walk_forward(
        ds.X,
        ds.y,
        train_window=args.wf_train,
        test_window=args.wf_test,
        epochs=args.epochs,
        lr=args.lr,
    )

    if not wf_results:
        raise SystemExit("Walk-forward nao gerou folds. Aumente --n ou reduza janelas.")

    print(f"\n{'Fold':>4} | {'Acc':>6} | {'Baseline':>8} | {'Edge pp':>8} | {'N':>6}")
    print("-" * 48)
    for r in wf_results:
        print(
            f"{r['fold']:>4} | {r['acc']:>6.4f} | {r['baseline']:>8.4f} | "
            f"{r['edge_pp']:>+8.2f} | {int(r['n']):>6}"
        )

    edges = [r["edge_pp"] for r in wf_results]
    mean_edge = sum(edges) / len(edges)
    pos_folds = sum(1 for e in edges if e > 0)
    print("-" * 48)
    print(f"Edge medio: {mean_edge:+.2f} p.p. | Folds positivos: {pos_folds}/{len(edges)}")

    # 5. Treino final no dataset inteiro
    print("\nTreinando modelo final no dataset completo...")
    means, stds = fit_scaler(ds.X)
    X_all = apply_scaler(ds.X, means, stds)
    final_model = LogisticRegressionModel(learning_rate=args.lr, epochs=args.epochs)
    final_model.fit(X_all, ds.y)

    # 6. Salvar via ModelRegistry
    metadata = ModelMetadata(
        model_id=model_id,
        model_version=args.model_version,
        dataset_version=ds.dataset_version,
        feature_version=f"{fs.name}_{fs.version}",
        feature_keys=list(fs.feature_keys),
        training_period=(
            str(candles[0].timestamp),
            str(candles[-1].timestamp),
        ),
        parameters={
            "lr": args.lr,
            "epochs": args.epochs,
            "horizon": args.horizon,
            "threshold": args.threshold,
            "wf_train": args.wf_train,
            "wf_test": args.wf_test,
            "feature_set": args.feature_set,
        },
        metrics={
            "mean_edge_pp": mean_edge,
            "positive_folds": float(pos_folds),
            "total_folds": float(len(edges)),
        },
        notes=f"Fonte: {'MT5:' + args.symbol if args.from_mt5 else 'sintetico'}",
    )

    registry = ModelRegistry(root_dir=args.registry_dir)
    entry = registry.save(final_model, metadata)

    # 7. Salvar scaling junto ao modelo
    import joblib
    joblib.dump(
        {"means": means, "stds": stds, "feature_keys": list(fs.feature_keys)},
        os.path.join(entry, "scaling.pkl"),
    )

    print(f"\nModelo salvo em: {entry}")
    print(f"  model.pkl")
    print(f"  scaling.pkl")
    print(f"  metadata.json")
    print(f"\nPara carregar em producao:")
    print(f"  from src.models.registry import ModelRegistry")
    print(f"  reg = ModelRegistry()")
    print(f"  model, meta = reg.load('{model_id}', '{args.model_version}')")


if __name__ == "__main__":
    main()