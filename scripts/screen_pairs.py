"""
Screener de pares cointegrados no MT5.

Coleta dados de N simbolos no mesmo timeframe, alinha por timestamp
(importante: cointegracao exige alinhamento temporal) e roda
CointegrationTester.test em todos os pares.

Uso:
    python scripts/screen_pairs.py
    python scripts/screen_pairs.py --symbols PETR4 VALE3 ITUB4 BBDC4
    python scripts/screen_pairs.py --timeframe M15 --min-corr 0.75
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


TIMEFRAME_MAP = {
    "M1":  "TIMEFRAME_M1",
    "M5":  "TIMEFRAME_M5",
    "M15": "TIMEFRAME_M15",
    "M30": "TIMEFRAME_M30",
    "H1":  "TIMEFRAME_H1",
    "H4":  "TIMEFRAME_H4",
    "D1":  "TIMEFRAME_D1",
}


from src.domain.models import Candle
from src.portfolio.cointegration import CointegrationResult, screen_pairs


def fetch_mt5_bars(
    symbols: List[str],
    n: int,
    timeframe: str = "M5",
) -> Dict[str, List[Candle]]:
    """Busca N candles de cada simbolo no MT5."""
    import MetaTrader5 as mt5

    if timeframe not in TIMEFRAME_MAP:
        raise ValueError(f"Timeframe invalido: {timeframe}")
    tf_const = getattr(mt5, TIMEFRAME_MAP[timeframe])

    if not mt5.initialize():
        raise RuntimeError(f"mt5.initialize falhou: {mt5.last_error()}")

    try:
        out: Dict[str, List[Candle]] = {}
        for sym in symbols:
            info = mt5.symbol_info(sym)
            if info is None:
                print(f"  {sym}: nao existe no broker")
                continue
            if not info.visible:
                mt5.symbol_select(sym, True)

            rates = mt5.copy_rates_from_pos(sym, tf_const, 0, n)
            if rates is None or len(rates) == 0:
                print(f"  {sym}: sem dados")
                continue

            out[sym] = [
                Candle(
                    symbol=sym,
                    timestamp=datetime.fromtimestamp(int(r["time"]), tz=timezone.utc),
                    open=float(r["open"]),
                    high=float(r["high"]),
                    low=float(r["low"]),
                    close=float(r["close"]),
                    volume=float(r["tick_volume"]),
                )
                for r in rates
            ]
        return out
    finally:
        mt5.shutdown()


def align_by_timestamp(
    candles_by_symbol: Dict[str, List[Candle]],
) -> Dict[str, List[float]]:
    """
    Alinha por interseccao de timestamps. Retorna {symbol: [closes]}.
    """
    if not candles_by_symbol:
        return {}

    # Conjuntos de timestamps
    ts_sets = {
        sym: set(c.timestamp for c in candles)
        for sym, candles in candles_by_symbol.items()
    }

    # Interseccao
    common = set.intersection(*ts_sets.values())
    if not common:
        return {}

    sorted_ts = sorted(common)
    # Index por symbol: ts -> close
    by_symbol_ts: Dict[str, Dict] = {}
    for sym, candles in candles_by_symbol.items():
        by_symbol_ts[sym] = {c.timestamp: c.close for c in candles}

    aligned: Dict[str, List[float]] = {}
    for sym in candles_by_symbol.keys():
        aligned[sym] = [by_symbol_ts[sym][ts] for ts in sorted_ts]

    return aligned


def main():
    parser = argparse.ArgumentParser(description="Screener de pares cointegrados no MT5")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=[
            "PETR4", "VALE3", "ITUB4", "BBDC4",
            "BBAS3", "ABEV3", "B3SA3", "ELET3",
        ],
        help="Simbolos a testar",
    )
    parser.add_argument(
        "--timeframe",
        choices=list(TIMEFRAME_MAP.keys()),
        default="M15",
    )
    parser.add_argument("--n", type=int, default=5000)
    parser.add_argument("--min-corr", type=float, default=0.7)
    parser.add_argument("--adf-threshold", type=float, default=0.05)
    parser.add_argument("--out-dir", default="models/benchmarks")
    args = parser.parse_args()

    print(f"Timeframe: {args.timeframe} | N: {args.n} | min_corr: {args.min_corr}")
    print(f"Simbolos: {args.symbols}")

    # 1. Fetch
    print("\nBuscando dados do MT5...")
    candles_by_symbol = fetch_mt5_bars(args.symbols, args.n, args.timeframe)

    if len(candles_by_symbol) < 2:
        raise SystemExit("Precisa de pelo menos 2 simbolos com dados")

    print(f"Simbolos com dados: {list(candles_by_symbol.keys())}")

    # 2. Align
    print("\nAlinhando por timestamp...")
    aligned = align_by_timestamp(candles_by_symbol)

    if not aligned:
        raise SystemExit("Sem timestamps em comum entre os simbolos")

    n_aligned = len(next(iter(aligned.values())))
    print(f"Observacoes alinhadas: {n_aligned}")

    if n_aligned < 100:
        raise SystemExit("Poucas observacoes alinhadas (min 100)")

    # 3. Screen
    print(f"\nTestando todos os pares (min_corr={args.min_corr}, adf_pvalue<{args.adf_threshold})...")
    results = screen_pairs(
        aligned,
        min_correlation=args.min_corr,
        adf_pvalue_threshold=args.adf_threshold,
        min_obs=100,
    )

    # 4. Report
    print("\n" + "=" * 78)
    print(f"PARES COINTEGRADOS: {len(results)}")
    print("=" * 78)
    if not results:
        print("Nenhum par passou no threshold.")
        print("Sugestoes:")
        print("  - Reduzir --min-corr (ex: 0.5)")
        print("  - Aumentar --adf-threshold (ex: 0.10)")
        print("  - Testar timeframe diferente (--timeframe M30 ou H1)")
        print("  - Testar outro conjunto de simbolos")
    else:
        print(f"{'Par':<20} | {'N':>5} | {'HR':>8} | {'ADF-p':>8} | {'HL':>7} | {'Resid std':>10}")
        print("-" * 78)
        for r in results:
            pair = f"{r.symbol_a}/{r.symbol_b}"
            hl = f"{r.half_life:.1f}" if r.half_life else "None"
            print(f"{pair:<20} | {r.n_obs:>5} | {r.hedge_ratio:>8.4f} | {r.adf_pvalue:>8.6f} | {hl:>7} | {r.residual_std:>10.4f}")
    print("=" * 78)

    # 5. Salvar
    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = os.path.join(args.out_dir, f"pairs_screen_{args.timeframe}_{ts}.json")

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