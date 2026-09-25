"""
Screener de pares cointegrados em cripto via Binance.

Reusa CointegrationTester (src/portfolio/cointegration.py) mas busca
dados da Binance em vez do MT5.

Uso:
    python scripts/screen_pairs_crypto.py
    python scripts/screen_pairs_crypto.py --symbols ETHUSDT SOLUSDT ADAUSDT DOTUSDT
    python scripts/screen_pairs_crypto.py --timeframe M15 --min-corr 0.7
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from src.adapters.binance_adapter import BinanceDataProvider
from src.domain.enums import Timeframe
from src.domain.models import Candle
from src.portfolio.cointegration import screen_pairs


TIMEFRAME_MAP = {
    "M1":  Timeframe.M1,
    "M5":  Timeframe.M5,
    "M15": Timeframe.M15,
    "H1":  Timeframe.H1,
    "D1":  Timeframe.D1,
}

TF_MINUTES = {
    "M1": 1, "M5": 5, "M15": 15, "H1": 60, "D1": 1440,
}


def fetch_prices(
    symbols: List[str],
    timeframe: str,
    n: int,
) -> Dict[str, List[Candle]]:
    """
    Busca N candles de cada simbolo usando JANELA DE TEMPO EXPLICITA.

    Importante: usar startTime/endTime garante que todos os simbolos
    tenham EXATAMENTE os mesmos timestamps. Usar apenas limit=N
    retorna as ultimas N barras de cada simbolo, que podem diferir
    se algum simbolo teve menos trades.
    """
    from datetime import timedelta

    tf = TIMEFRAME_MAP[timeframe]
    minutes_per_bar = TF_MINUTES[timeframe]
    # Janela com margem para garantir N barras (mesmo em simbolos com gap)
    window_minutes = n * minutes_per_bar * 2

    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=window_minutes)

    out: Dict[str, List[Candle]] = {}
    provider = BinanceDataProvider()
    try:
        for sym in symbols:
            try:
                # Pede uma janela maior para garantir N barras uteis
                bars = provider.fetch_candles(
                    sym.upper(), tf, start, end, limit=min(n, 1000)
                )
                if bars:
                    out[sym.upper()] = bars[-n:] if len(bars) > n else bars
                    print(f"  {sym.upper()}: {len(out[sym.upper()])} barras")
                else:
                    print(f"  {sym.upper()}: sem dados")
            except Exception as exc:
                print(f"  {sym.upper()}: erro - {exc}")
    finally:
        provider.close()
    return out


def align_by_timestamp(
    candles_by_symbol: Dict[str, List[Candle]],
) -> Dict[str, List[float]]:
    """Alinha por interseccao de timestamps."""
    if not candles_by_symbol:
        return {}

    ts_sets = {
        sym: set(c.timestamp for c in candles)
        for sym, candles in candles_by_symbol.items()
    }
    common = set.intersection(*ts_sets.values())
    if not common:
        return {}

    sorted_ts = sorted(common)
    by_sym_ts = {sym: {c.timestamp: c.close for c in candles}
                 for sym, candles in candles_by_symbol.items()}

    return {
        sym: [by_sym_ts[sym][ts] for ts in sorted_ts]
        for sym in candles_by_symbol.keys()
    }


def main():
    parser = argparse.ArgumentParser(description="Screener de pares cripto")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=[
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOTUSDT",
            "MATICUSDT", "LINKUSDT", "AVAXUSDT", "ATOMUSDT", "NEARUSDT",
        ],
        help="Simbolos Binance",
    )
    parser.add_argument(
        "--timeframe",
        choices=list(TIMEFRAME_MAP.keys()),
        default="M15",
    )
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--min-corr", type=float, default=0.7)
    parser.add_argument("--adf-threshold", type=float, default=0.05)
    parser.add_argument("--out-dir", default="models/benchmarks")
    args = parser.parse_args()

    print(f"Timeframe: {args.timeframe} | N: {args.n} | min_corr: {args.min_corr}")
    print(f"Symbols: {args.symbols}")

    print("\nBuscando dados da Binance...")
    candles_by_symbol = fetch_prices(args.symbols, args.timeframe, args.n)

    if len(candles_by_symbol) < 2:
        raise SystemExit("Precisa de pelo menos 2 simbolos com dados")

    print(f"\nSimbolos com dados: {list(candles_by_symbol.keys())}")

    print("\nAlinhando por timestamp...")
    aligned = align_by_timestamp(candles_by_symbol)
    if not aligned:
        raise SystemExit("Sem timestamps em comum")

    n_aligned = len(next(iter(aligned.values())))
    print(f"Observacoes alinhadas: {n_aligned}")

    if n_aligned < 100:
        raise SystemExit("Poucas observacoes alinhadas")

    print(f"\nTestando pares (min_corr={args.min_corr}, adf_pvalue<{args.adf_threshold})...")
    results = screen_pairs(
        aligned,
        min_correlation=args.min_corr,
        adf_pvalue_threshold=args.adf_threshold,
        min_obs=100,
    )

    print("\n" + "=" * 78)
    print(f"PARES COINTEGRADOS: {len(results)}")
    print("=" * 78)
    if not results:
        print("Nenhum par passou no threshold.")
    else:
        print(f"{'Par':<22} | {'N':>5} | {'HR':>8} | {'ADF-p':>8} | {'HL':>8} | {'Resid std':>10}")
        print("-" * 78)
        for r in results:
            pair = f"{r.symbol_a}/{r.symbol_b}"
            hl = f"{r.half_life:.1f}" if r.half_life else "None"
            print(f"{pair:<22} | {r.n_obs:>5} | {r.hedge_ratio:>8.4f} | {r.adf_pvalue:>8.6f} | {hl:>8} | {r.residual_std:>10.4f}")
    print("=" * 78)

    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = os.path.join(args.out_dir, f"pairs_crypto_{args.timeframe}_{ts}.json")
    output = {
        "timeframe": args.timeframe,
        "n_requested": args.n,
        "n_aligned": n_aligned,
        "min_correlation": args.min_corr,
        "adf_threshold": args.adf_threshold,
        "symbols": list(candles_by_symbol.keys()),
        "n_pairs_tested": len(candles_by_symbol) * (len(candles_by_symbol) - 1) // 2,
        "n_cointegrated": len(results),
        "results": [r.to_dict() for r in results],
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nResultado salvo em: {out_path}")


if __name__ == "__main__":
    main()