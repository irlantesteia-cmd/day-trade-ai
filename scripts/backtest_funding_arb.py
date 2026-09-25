"""
Backtest de funding rate arbitrage (cash-and-carry).

Modela a estrategia:
  - SHORT perp + LONG spot (delta-neutro)
  - Coleta funding a cada 8h (se positivo)
  - Paga funding se negativo
  - Custos de entrada (perp + spot) e saida
  - Rebalanceamento periodico

Nao modela:
  - Liquidacao (assume capital suficiente)
  - Margin calls
  - Risco de exchange

Uso:
    python scripts/backtest_funding_arb.py
    python scripts/backtest_funding_arb.py --symbol BTCUSDT --days 90
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.adapters.binance_futures_adapter import BinanceFuturesAdapter


# Taxas tipicas Binance (taker)
SPOT_FEE = 0.0004       # 0.04% (taker em spot BTC)
FUTURES_FEE = 0.0004    # 0.04% (taker em futuros)
# Roundtrip total (abrir + fechar 2 pernas)
ROUNDTRIP_COST = 2 * (SPOT_FEE + FUTURES_FEE)  # ~0.16%


def backtest_symbol(
    symbol: str,
    lookback_days: int = 30,
    capital: float = 10000.0,
) -> Dict[str, Any]:
    """
    Simula cash-and-carry sobre o historico de funding.

    Assume:
      - Capital alocado: 50% long spot + 50% short perp (com margem)
      - Posicao dimensionada para capital `capital`
      - Cada funding recebido/pago sobre o notional total
    """
    with BinanceFuturesAdapter() as fa:
        history = fa.get_funding_history(symbol, limit=1000)
        if not history:
            return {"symbol": symbol, "error": "sem dados"}

        # Filtra ultimos N dias
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        history = [h for h in history if h["funding_time"] >= cutoff]

        if len(history) < 10:
            return {"symbol": symbol, "error": "poucas obs"}

        # Simulacao
        # Custo unico na abertura
        capital_after_cost = capital * (1 - ROUNDTRIP_COST)

        # Coleta funding
        funding_events = []
        equity = capital_after_cost

        for h in history:
            rate = h["funding_rate"]
            # Short perp recebe quando rate > 0
            # Notional exposto = capital (aproximacao)
            pnl = rate * capital_after_cost
            equity += pnl
            funding_events.append({
                "time": h["funding_time"].isoformat(),
                "rate_pct": rate * 100,
                "pnl_rs": pnl,
                "equity": equity,
            })

        # Custo de saida
        equity_final = equity * (1 - ROUNDTRIP_COST)

        # Metricas
        n = len(history)
        rates = [h["funding_rate"] for h in history]
        mean_rate = sum(rates) / n

        total_pnl = equity_final - capital
        total_pnl_pct = total_pnl / capital * 100
        annualized = (1 + total_pnl / capital) ** (365 / lookback_days) - 1
        annualized_pct = annualized * 100

        # Drawdown no equity curve de funding
        peak = capital
        max_dd = 0.0
        for e in funding_events:
            if e["equity"] > peak:
                peak = e["equity"]
            dd = (peak - e["equity"]) / peak
            max_dd = max(max_dd, dd)

        # % de funding negativos (quando short perp paga)
        n_neg = sum(1 for r in rates if r < 0)

        return {
            "symbol": symbol,
            "lookback_days": lookback_days,
            "n_funding_events": n,
            "mean_rate_pct": round(mean_rate * 100, 6),
            "pct_negative": round(n_neg / n * 100, 2),
            "capital_initial": capital,
            "capital_final": round(equity_final, 2),
            "total_pnl_rs": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 4),
            "annualized_pct": round(annualized_pct, 2),
            "max_drawdown_pct": round(max_dd * 100, 4),
            "roundtrip_cost_pct": round(ROUNDTRIP_COST * 100, 4),
        }


def main():
    parser = argparse.ArgumentParser(description="Backtest funding arb")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["BTCUSDT", "ETHUSDT", "LINKUSDT", "DOGEUSDT", "LTCUSDT"],
    )
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--capital", type=float, default=10000.0)
    parser.add_argument("--out-dir", default="models/benchmarks")
    args = parser.parse_args()

    print(f"Backtest cash-and-carry | lookback {args.days}d | capital ${args.capital}")
    print(f"Roundtrip cost modelado: {ROUNDTRIP_COST*100:.4f}%")
    print()

    header = (
        f"{'Symbol':<12} | {'N events':>8} | {'% neg':>6} | "
        f"{'PnL R$':>9} | {'PnL %':>8} | {'Anual %':>9} | {'Max DD %':>9}"
    )
    print(header)
    print("-" * len(header))

    results = []
    for sym in args.symbols:
        try:
            r = backtest_symbol(sym, lookback_days=args.days, capital=args.capital)
            if "error" in r:
                print(f"{sym:<12} | erro: {r['error']}")
                continue
            results.append(r)
            print(
                f"{sym:<12} | {r['n_funding_events']:>8} | "
                f"{r['pct_negative']:>5.1f}% | "
                f"{r['total_pnl_rs']:>+8.2f} | "
                f"{r['total_pnl_pct']:>+7.4f}% | "
                f"{r['annualized_pct']:>+8.2f}% | "
                f"{r['max_drawdown_pct']:>8.4f}%"
            )
        except Exception as exc:
            print(f"{sym:<12} | erro: {exc}")

    print()

    # Diagnosticos
    profitable = [r for r in results if r["annualized_pct"] > 0]
    print(f"Simbolos com edge liquido positivo: {len(profitable)}/{len(results)}")

    if profitable:
        best = max(profitable, key=lambda r: r["annualized_pct"])
        print(f"Melhor: {best['symbol']} -> {best['annualized_pct']:+.2f}% anualizado (com custos)")

    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = os.path.join(args.out_dir, f"backtest_funding_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "lookback_days": args.days,
            "capital": args.capital,
            "roundtrip_cost_pct": ROUNDTRIP_COST * 100,
            "results": results,
        }, f, indent=2, default=str)
    print(f"\nResultado salvo em: {out_path}")


if __name__ == "__main__":
    main()