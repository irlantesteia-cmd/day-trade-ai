"""
Walk-forward de cointegracao em pares cripto.

Split 70/30:
  - Treino: testa cointegracao, obtem hedge_ratio
  - Teste:  aplica hedge_ratio do treino, verifica se spread
            continua estacionario (ADF)

Se o spread quebra out-of-sample, o "achado" era falso positivo
por multiple testing.
"""
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from statsmodels.tsa.stattools import adfuller

from src.adapters.binance_adapter import BinanceDataProvider
from src.domain.enums import Timeframe
from src.portfolio.cointegration import CointegrationTester


PAIRS = [
    ("ADAUSDT", "LINKUSDT"),
    ("SOLUSDT", "LINKUSDT"),
    ("ETHUSDT", "LINKUSDT"),
    ("ETHUSDT", "SOLUSDT"),
    ("DOTUSDT", "MATICUSDT"),
    ("ADAUSDT", "AVAXUSDT"),
    ("ETHUSDT", "AVAXUSDT"),
    ("ETHUSDT", "ADAUSDT"),
    ("BTCUSDT", "SOLUSDT"),
    ("BTCUSDT", "ETHUSDT"),
]


def main():
    tester = CointegrationTester(adf_pvalue_threshold=0.05)
    provider = BinanceDataProvider()

    print(f"{'Par':<22} | {'p-train':>8} | {'p-test':>8} | {'HR-train':>10} | {'Mantem?':>8}")
    print("-" * 78)

    try:
        for sym_a, sym_b in PAIRS:
            try:
                bars_a = provider.fetch_latest_bars(sym_a, Timeframe.D1, n=1000)
                bars_b = provider.fetch_latest_bars(sym_b, Timeframe.D1, n=1000)

                ts_a = {c.timestamp: c.close for c in bars_a}
                ts_b = {c.timestamp: c.close for c in bars_b}
                common = sorted(set(ts_a.keys()) & set(ts_b.keys()))

                if len(common) < 200:
                    print(f"{sym_a[:4]}/{sym_b[:4]:<15} | sem dados (N={len(common)})")
                    continue

                prices_a = [ts_a[ts] for ts in common]
                prices_b = [ts_b[ts] for ts in common]

                split = int(len(prices_a) * 0.7)
                train_a, train_b = prices_a[:split], prices_b[:split]
                test_a, test_b = prices_a[split:], prices_b[split:]

                res_train = tester.test(train_a, train_b, sym_a, sym_b)

                spread_test = [
                    a - (res_train.intercept + res_train.hedge_ratio * b)
                    for a, b in zip(test_a, test_b)
                ]
                adf_test = adfuller(spread_test, autolag="AIC", result_object=False)
                p_test = float(adf_test[1])

                mantem = "SIM" if (res_train.is_cointegrated and p_test < 0.05) else "NAO"
                pair_label = f"{sym_a[:4]}/{sym_b[:4]}"
                print(
                    f"{pair_label:<22} | {res_train.adf_pvalue:>8.4f} | "
                    f"{p_test:>8.4f} | {res_train.hedge_ratio:>10.4f} | {mantem:>8}"
                )
            except Exception as exc:
                print(f"{sym_a}/{sym_b}: erro - {exc}")
    finally:
        provider.close()


if __name__ == "__main__":
    main()