"""
RiskEngine - avalia Signal e gera Order ajustada ao risco.

Suporta dois sizers:
  - PositionSizer (default): risco fixo
  - DynamicPositionSizer: adaptativo por vol + confidence
"""
from typing import Optional

from src.domain.enums import OrderSide, OrderType, SignalType
from src.domain.models import Order, Signal
from src.risk.calculators import PositionSizer, SLTPCalculator
from src.risk.config import RiskConfig
from src.risk.manager import RiskManager


class RiskEngine:
    def __init__(
        self,
        config: Optional[RiskConfig] = None,
        sizer: Optional[object] = None,
    ):
        self.config = config or RiskConfig()
        self.manager = RiskManager(self.config)
        self.sltp_calc = SLTPCalculator(self.config)
        self.sizer = sizer if sizer is not None else PositionSizer()

    def _extract_confidence(self, signal: Signal) -> float:
        """Le confidence do Signal (tolerante a variantes)."""
        for attr in ("confidence", "strength"):
            v = getattr(signal, attr, None)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
        return 0.5

    def _extract_vol(self, signal: Signal) -> Optional[float]:
        """Le vol_at_entry do metadata se disponivel."""
        if not isinstance(signal.metadata, dict):
            return None
        for key in ("vol_at_entry", "current_vol", "realized_vol"):
            v = signal.metadata.get(key)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
        return None

    def generate_order(
        self,
        signal: Signal,
        current_price: float,
        account_balance: float,
    ) -> Optional[Order]:
        """Avalia sinal e gera ordem ajustada ao risco, ou rejeita retornando None."""
        if signal.direction == SignalType.NEUTRAL:
            return None

        if not self.manager.can_take_trade():
            return None

        # 1. SL/TP via ATR
        atr_val = None
        if isinstance(signal.metadata, dict):
            atr_val = signal.metadata.get("atr")

        stop_loss, take_profit = self.sltp_calc.calculate(
            direction=signal.direction,
            entry_price=current_price,
            atr=atr_val,
        )

        # 2. Quantity via sizer (chama compute_quantity quando disponivel)
        quantity = 0.0
        try:
            if hasattr(self.sizer, "compute_quantity"):
                quantity = self.sizer.compute_quantity(
                    balance=account_balance,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    signal_confidence=self._extract_confidence(signal),
                    current_vol=self._extract_vol(signal),
                    risk_pct=self.config.risk_per_trade_pct,
                )
            else:
                # Fallback para PositionSizer antigo (calculate_quantity)
                quantity = self.sizer.calculate_quantity(
                    balance=account_balance,
                    risk_pct=self.config.risk_per_trade_pct,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                )
        except TypeError:
            # compute_quantity nao aceitou alguns kwargs: chamada minima
            quantity = self.sizer.compute_quantity(
                balance=account_balance,
                entry_price=current_price,
                stop_loss=stop_loss,
            )

        if quantity <= 0:
            return None

        side = OrderSide.BUY if signal.direction == SignalType.BUY else OrderSide.SELL

        return Order(
            symbol=signal.symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )