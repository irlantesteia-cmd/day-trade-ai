"""
Backtest estendido de funding rate arbitrage.

Testa 30 perps liquidos (nao apenas os 5 handpicked), com 3 cenarios
de custo, e modela ROI sobre capital efetivo (spot + margem).

Cenarios de custo (roundtrip, ambas as pernas):
  - OTIMISTA:  0.10% (VIP fees + limit orders)
  - BASE:      0.16% (taker padrao em ambas)
  - PESSIMISTA: 0.30% (taker + slippage + spread)

Capital efetivo:
  Estrategia exige 50% em spot + 50% em margem no perp.
  ROI_reportado = ROI_notional * (capital_alocado / capital_total)
  Como 100% do capital esta alocado (50% spot + 50% margem),
  o ROI_sobre_notional ja e o retorno sobre capital.

  Aproximacao anterior (100% notional) era otimista.

Uso:
    python scripts/backtest_funding_extended.py
    python scripts/backtest_funding_extended.py --days 180
    python scripts/backtest_funding_extended.py --max-symbols 30
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.adapters.binance_futures_adapter import BinanceFuturesAdapter


# Cenarios de custo roundtrip (abertura + fechamento das 2 pernas)
COST_SCENARIOS = {
    "otimista":  0.0010,  # 0.10%
    "base":      0.0016,  # 0.16%
    "pessimista": 0.0030, # 0.30%
}


# Universo: 30 perps liquidos (top volume), excluindo problemáticos
DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "LTCUSDT", "TRXUSDT", "ATOMUSDT", "NEARUSDT", "APTUSDT",
    "ARBUSDT", "OPUSDT", "INJUSDT", "SUIUSDT", "TIAUSDT",
    "FILUSDT", "ETCUSDT", "HBARUSDT", "ICPUSDT", "UNIUSDT",
    "AAVEUSDT", "MKRUSDT", "CRVUSDT", "SNXUSDT", "COMPUSDT",
]


def backtest_symbol_all_scenarios(
    symbol: str,
    lookback_days: int,
    capital: float = 10000.0,
) -> Dict[str, Any]:
    """
    Roda o cash-and-carry para o simbolo e retorna metricas para
    os 3 cenarios de custo.
    """
    with BinanceFuturesAdapter() as fa:
        history = fa.get_funding_history(symbol, limit=1000)
        if not history:
            return {"symbol": symbol, "error": "sem dados"}

        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        history = [h for h in history if h["funding_time"] >= cutoff]

        if len(history) < 30:
            return {"symbol": symbol, "error": f"poucas obs ({len(history)})"}

        rates = [h["funding_rate"] for h in history]
        n = len(rates)
        sum_rates = sum(rates)
        mean_rate = sum_rates / n
        pct_neg = sum(1 for r in rates if r < 0) / n

        # Equity sem custos
        # Notional = capital / 2 (spot) + margem = capital / 2 (perp)
        # Posicao perp = capital / 2 como notional hedgeado
        # (na pratica notional no perp = metade do capital)
        notional_perp = capital / 2.0

        # PnL bruto = sum(rates) * notional_perp
        pnl_gross = sum_rates * notional_perp

        # Aplica cada cenario de custo
        scenarios: Dict[str, Any] = {}
        for name, cost in COST_SCENARIOS.items():
            pnl_net = pnl_gross - (capital * cost)
            equity_final = capital + pnl_net
            pnl_pct = pnl_net / capital * 100
            # Anualizado (compose)
            if lookback_days > 0 and equity_final > 0:
                annualized = ((equity_final / capital) ** (365 / lookback_days) - 1) * 100
            else:
                annualized = 0.0

            scenarios[name] = {
                "cost_pct": cost * 100,
                "pnl_rs": round(pnl_net, 2),
                "pnl_pct": round(pnl_pct, 4),
                "annualized_pct": round(annualized, 2),
            }

        return {
            "symbol": symbol,
            "lookback_days": lookback_days,
            "n_events": n,
            "mean_rate_pct": round(mean_rate * 100, 6),
            "pct_negative": round(pct_neg * 100, 2),
            "sum_rates_pct": round(sum_rates * 100, 4),
            "notional_perp": notional_perp,
            "scenarios": scenarios,
        }


def main():
    parser = argparse.ArgumentParser(description="Backtest funding estendido")
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--capital", type=float, default=10000.0)
    parser.add_argument("--out-dir", default="models/benchmarks")
    args = parser.parse_args()

    print(f"Backtest estendido | lookback {args.days}d | {len(args.symbols)} simbolos")
    print(f"Capital: ${args.capital}")
    print(f"Cenarios de custo: {list(COST_SCENARIOS.keys())}")
    print()

    # Header
    header = (
        f"{'Symbol':<12} | {'N':>4} | {'% neg':>6} | "
        f"{'Otim %':>8} | {'Base %':>8} | {'Pess %':>8}"
    )
    print(header)
    print("-" * len(header))

    all_results: List[Dict[str, Any]] = []

    for sym in args.symbols:
        try:
            r = backtest_symbol_all_scenarios(
                sym, lookback_days=args.days, capital=args.capital
            )
            if "error" in r:
                print(f"{sym:<12} | {r['error']}")
                continue
            all_results.append(r)
            s = r["scenarios"]
            print(
                f"{sym:<12} | {r['n_events']:>4} | "
                f"{r['pct_negative']:>5.1f}% | "
                f"{s['otimista']['annualized_pct']:>+7.2f}% | "
                f"{s['base']['annualized_pct']:>+7.2f}% | "
                f"{s['pessimista']['annualized_pct']:>+7.2f}%"
            )
        except Exception as exc:
            print(f"{sym:<12} | erro: {exc}")

    print()

    # Sumario por cenario
    if all_results:
        print("=" * 60)
        print("SUMARIO POR CENARIO")
        print("=" * 60)

        for scenario_name in COST_SCENARIOS.keys():
            positives = [
                r for r in all_results
                if r["scenarios"][scenario_name]["annualized_pct"] > 0
            ]
            negatives = len(all_results) - len(positives)
            mean_annual = sum(
                r["scenarios"][scenario_name]["annualized_pct"]
                for r in all_results
            ) / len(all_results)

            print(
                f"  {scenario_name:<12}: "
                f"{len(positives)}/{len(all_results)} positivos | "
                f"media {mean_annual:+.2f}% anual"
            )

        # Mediana por cenario (mais robusto que media)
        print()
        print("Medianas:")
        for scenario_name in COST_SCENARIOS.keys():
            annuals = sorted(
                r["scenarios"][scenario_name]["annualized_pct"]
                for r in all_results
            )
            median = annuals[len(annuals) // 2]
            print(f"  {scenario_name:<12}: {median:+.2f}% anual")

    # Salvar
    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = os.path.join(args.out_dir, f"funding_extended_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "lookback_days": args.days,
            "capital": args.capital,
            "cost_scenarios": COST_SCENARIOS,
            "n_symbols": len(all_results),
            "results": all_results,
        }, f, indent=2, default=str)
    print(f"\nResultado salvo em: {out_path}")


if __name__ == "__main__":
    main()