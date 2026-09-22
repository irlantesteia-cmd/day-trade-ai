"""
Alocação de capital por Risk Parity.
Cada ativo recebe peso inversamente proporcional à sua volatilidade recente,
normalizado para que a soma dos riscos contribuídos seja igual.
"""
from typing import Dict, List
import numpy as np
import logging

logger = logging.getLogger(__name__)


class RiskParityAllocator:
    """
    Alocador Risk Parity simples (inverse-volatility).
    Para implementação institucional completa, considerar 'riskfolio-lib'[reference:2].
    """

    def __init__(self, target_vol: float = 0.15, max_weight: float = 0.25,
                 min_weight: float = 0.02):
        self.target_vol = target_vol
        self.max_weight = max_weight
        self.min_weight = min_weight

    def compute_weights(self, returns_by_symbol: Dict[str, List[float]]) -> Dict[str, float]:
        """
        Returns: pesos que somam 1.0, inversamente proporcionais à vol realizada.
        """
        vols = {}
        for sym, rets in returns_by_symbol.items():
            if len(rets) < 20:
                vols[sym] = 1.0  # default neutro
                continue
            arr = np.array(rets[-60:])  # janela de 60 barras
            vols[sym] = float(np.std(arr)) or 1e-6

        inv_vols = {sym: 1.0 / v for sym, v in vols.items()}
        total = sum(inv_vols.values())
        weights = {sym: iv / total for sym, iv in inv_vols.items()}

        # Aplica caps
        weights = self._apply_caps(weights)
        return weights

    def _apply_caps(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Aplica min/max e renormaliza."""
        capped = {}
        for sym, w in weights.items():
            capped[sym] = max(self.min_weight, min(self.max_weight, w))
        total = sum(capped.values())
        if total == 0:
            n = len(capped) or 1
            return {sym: 1.0 / n for sym in capped}
        return {sym: w / total for sym, w in capped.items()}

    def compute_position_sizes(self, weights: Dict[str, float],
                               equity: float,
                               prices: Dict[str, float]) -> Dict[str, float]:
        """
        Converte pesos em contratos/ações por símbolo.
        """
        sizes = {}
        for sym, w in weights.items():
            price = prices.get(sym, 0.0)
            if price <= 0:
                sizes[sym] = 0.0
                continue
            notional = equity * w
            sizes[sym] = notional / price
        return sizes