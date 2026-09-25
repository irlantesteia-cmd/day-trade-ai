"""
DynamicPositionSizer - position sizing adaptativo.

Ajusta o tamanho da posicao baseado em:
  - Risco base (% do capital)
  - Confianca do sinal (mais confianca -> maior tamanho, capado)
  - Volatilidade atual (mais vol -> menor tamanho)
  - Regime (high vol -> reduz tamanho)

Diferente do PositionSizer simples (risco fixo), este adapta
continuamente ao contexto de mercado.

Uso:
    sizer = DynamicPositionSizer(
        base_risk_pct=1.0,
        vol_target_pct=0.5,
        confidence_scaling=True,
    )
    qty = sizer.compute_quantity(
        balance=10000,
        entry_price=130000,
        stop_loss=129500,
        signal_confidence=0.8,
        current_vol=0.001,
    )
"""
import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)


class DynamicPositionSizer:
    def __init__(
        self,
        base_risk_pct: float = 1.0,
        vol_target_pct: float = 0.5,
        min_size_factor: float = 0.25,
        max_size_factor: float = 2.0,
        confidence_scaling: bool = True,
    ):
        """
        Args:
            base_risk_pct: risco base por trade (% do capital)
            vol_target_pct: vol alvo (ex: 0.5 = 0.5% de variacao por barra)
            min_size_factor: tamanho minimo (fracao do base)
            max_size_factor: tamanho maximo (multiplo do base)
            confidence_scaling: se True, escala por confidence do sinal
        """
        if base_risk_pct <= 0:
            raise ValueError("base_risk_pct deve ser > 0")
        if vol_target_pct <= 0:
            raise ValueError("vol_target_pct deve ser > 0")
        if min_size_factor <= 0 or max_size_factor < min_size_factor:
            raise ValueError("min/max size factor invalidos")

        self.base_risk_pct = base_risk_pct
        self.vol_target_pct = vol_target_pct
        self.min_size_factor = min_size_factor
        self.max_size_factor = max_size_factor
        self.confidence_scaling = confidence_scaling

    def _vol_factor(self, current_vol: Optional[float]) -> float:
        """
        Fator de ajuste por volatilidade.

        Se vol = vol_target -> 1.0
        Se vol = 2x vol_target -> 0.5 (metade do tamanho)
        Se vol = 0.5x vol_target -> 1.5 (mais tamanho, ate cap)
        """
        if current_vol is None or current_vol <= 0:
            return 1.0

        target = self.vol_target_pct / 100.0  # ex: 0.5% -> 0.005
        if target <= 0:
            return 1.0

        ratio = target / current_vol
        return max(self.min_size_factor, min(self.max_size_factor, ratio))

    def _confidence_factor(self, confidence: float) -> float:
        """
        Fator de ajuste por confidence do sinal.

        Confidence 0.5 -> 1.0
        Confidence 0.9 -> 1.4 (cap 1.5)
        Confidence 0.6 -> 1.1
        """
        if not self.confidence_scaling:
            return 1.0
        c = max(0.0, min(1.0, float(confidence)))
        # Mapeia 0.5->1.0, 1.0->1.5
        factor = 1.0 + (c - 0.5) * 1.0
        return max(0.8, min(1.5, factor))

    def compute_quantity(
        self,
        balance: float,
        entry_price: float,
        stop_loss: float,
        signal_confidence: float = 0.7,
        current_vol: Optional[float] = None,
    ) -> float:
        """
        Calcula quantidade adaptativa.

        Retorna 0.0 se parametros invalidos.
        """
        if balance <= 0 or entry_price <= 0:
            return 0.0
        if entry_price == stop_loss:
            return 0.0

        # Risco monetario base
        risk_amount = balance * (self.base_risk_pct / 100.0)

        # Distancia ate o stop (por unidade)
        risk_per_unit = abs(entry_price - stop_loss)
        if risk_per_unit <= 0:
            return 0.0

        # Quantidade base (risco fixo)
        base_qty = risk_amount / risk_per_unit

        # Ajustes
        vol_f = self._vol_factor(current_vol)
        conf_f = self._confidence_factor(signal_confidence)

        adjusted_qty = base_qty * vol_f * conf_f

        # Sanity: nao pode ser zero nem infinita
        if not math.isfinite(adjusted_qty) or adjusted_qty <= 0:
            return 0.0

        return round(adjusted_qty, 4)