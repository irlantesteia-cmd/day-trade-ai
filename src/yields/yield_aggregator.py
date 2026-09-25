"""
Yield Aggregator - consolida yields de multiplas fontes.

Fontes:
  - Binance staking/earn (ETH, SOL, USDT, USDC, BNB)
  - DeFi lending (Aave v3, Compound v3, Morpho)
  - Funding rate arb (calculado separadamente)

Objetivo: comparar yields estruturalmente disponiveis com risk-free
(CDI, T-bills) para decidir alocacao.

Uso:
    with YieldAggregator() as agg:
        all_yields = agg.all_yields()
        best = agg.best_by_asset("USDC")
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.adapters.binance_staking_adapter import BinanceStakingAdapter
from src.adapters.defi_lending_adapter import DefiLendingAdapter

logger = logging.getLogger(__name__)


# Referencia risk-free (Q3 2026)
RISK_FREE = {
    "cdi_brl": {
        "name": "CDI Brasil",
        "apy_pct": 11.5,
        "currency": "BRL",
        "notes": "taxa basica brasileira",
    },
    "tbill_usd": {
        "name": "US T-Bill 3M",
        "apy_pct": 4.8,
        "currency": "USD",
        "notes": "treasury 3 meses",
    },
    "usdc_native": {
        "name": "USDC nativo (Circle)",
        "apy_pct": 0.0,
        "currency": "USD",
        "notes": "stablecoin sem yield",
    },
}


@dataclass
class YieldOpportunity:
    """Uma fonte de yield."""

    asset: str
    source: str
    category: str  # staking, lending, funding, real_yield
    apy_pct: float
    currency: str
    lockup_days: int = 0
    risk_level: str = "medium"  # low, medium, high
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset": self.asset,
            "source": self.source,
            "category": self.category,
            "apy_pct": self.apy_pct,
            "currency": self.currency,
            "lockup_days": self.lockup_days,
            "risk_level": self.risk_level,
            "notes": self.notes,
        }


class YieldAggregator:
    """Agrega yields de staking + lending + funding."""

    def __init__(self):
        self.staking = BinanceStakingAdapter()
        self.lending = DefiLendingAdapter()

    def close(self) -> None:
        self.staking.close()
        self.lending.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    # ------------------------------------------------------------------
    # Coleta
    # ------------------------------------------------------------------

    def staking_yields(self) -> List[YieldOpportunity]:
        out: List[YieldOpportunity] = []
        for asset in self.staking.list_supported_assets():
            info = self.staking.get_staking_info(asset)
            apy = info.get("apy_pct")
            if apy is None:
                continue
            out.append(YieldOpportunity(
                asset=asset,
                source=info["source"],
                category="staking" if info["type"] == "native_staking" else "earn",
                apy_pct=apy,
                currency=asset if asset in ("USDT", "USDC") else "USD",
                lockup_days=info.get("lockup_days", 0),
                risk_level="medium" if asset not in ("USDT", "USDC") else "low",
                notes=info.get("notes", ""),
            ))
        return out

    def lending_yields(self) -> List[YieldOpportunity]:
        out: List[YieldOpportunity] = []
        for protocol, asset in [
            (p, a) for p in self.lending.list_protocols()
            for a in self.lending.list_assets()
        ]:
            info = self.lending.get_lending_rate(asset, protocol)
            apy = info.get("supply_apy_pct")
            if apy is None:
                continue
            out.append(YieldOpportunity(
                asset=asset,
                source=f"defi_{info['protocol']}",
                category="lending",
                apy_pct=apy,
                currency="USD",
                lockup_days=0,
                risk_level="medium",  # smart contract risk
                notes=f"util {info.get('utilization_pct', 0)}% | chain {info.get('chain', '?')}",
            ))
        return out

    def funding_yields(self) -> List[YieldOpportunity]:
        """
        Yields de funding arb (valores consolidados do M28-29).

        Nao re-calcula aqui (faria chamadas HTTP adicionais). Usa os
        valores de referencia do ADR-032.
        """
        # Mediana base do backtest estendido
        return [
            YieldOpportunity(
                asset="BTCUSDT", source="binance_funding_arb",
                category="funding", apy_pct=1.52, currency="USD",
                lockup_days=0, risk_level="medium",
                notes="cash-and-carry, cenario base",
            ),
            YieldOpportunity(
                asset="LINKUSDT", source="binance_funding_arb",
                category="funding", apy_pct=2.17, currency="USD",
                lockup_days=0, risk_level="medium",
                notes="cash-and-carry, cenario base",
            ),
            YieldOpportunity(
                asset="DOGEUSDT", source="binance_funding_arb",
                category="funding", apy_pct=1.90, currency="USD",
                lockup_days=0, risk_level="medium",
                notes="cash-and-carry, cenario base",
            ),
        ]

    # ------------------------------------------------------------------
    # Analise
    # ------------------------------------------------------------------

    def all_yields(self) -> List[YieldOpportunity]:
        out = []
        out.extend(self.staking_yields())
        out.extend(self.lending_yields())
        out.extend(self.funding_yields())
        # Ordena por APY desc
        out.sort(key=lambda o: o.apy_pct, reverse=True)
        return out

    def best_by_asset(self, asset: str) -> Optional[YieldOpportunity]:
        asset_up = asset.upper()
        candidates = [o for o in self.all_yields() if o.asset == asset_up]
        if not candidates:
            return None
        return max(candidates, key=lambda o: o.apy_pct)

    def compare_to_risk_free(self) -> List[Dict[str, Any]]:
        """Compara cada yield ao risk-free apropriado."""
        comparison = []
        for opp in self.all_yields():
            if opp.currency == "BRL":
                rf = RISK_FREE["cdi_brl"]["apy_pct"]
                rf_name = RISK_FREE["cdi_brl"]["name"]
            else:
                rf = RISK_FREE["tbill_usd"]["apy_pct"]
                rf_name = RISK_FREE["tbill_usd"]["name"]
            spread = opp.apy_pct - rf
            comparison.append({
                "asset": opp.asset,
                "source": opp.source,
                "category": opp.category,
                "apy_pct": opp.apy_pct,
                "risk_free_pct": rf,
                "risk_free_name": rf_name,
                "spread_pct": round(spread, 2),
                "beats_risk_free": spread > 0,
            })
        return comparison

    def summary(self) -> Dict[str, Any]:
        all_y = self.all_yields()
        comp = self.compare_to_risk_free()
        beats = sum(1 for c in comp if c["beats_risk_free"])
        return {
            "n_opportunities": len(all_y),
            "n_beats_risk_free": beats,
            "best_overall": all_y[0].to_dict() if all_y else None,
            "yields": [o.to_dict() for o in all_y],
            "risk_free": RISK_FREE,
        }