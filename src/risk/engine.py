from typing import Optional
from src.domain.enums import OrderSide, OrderType, SignalType
from src.domain.models import Order, Signal
from src.risk.calculators import PositionSizer, SLTPCalculator
from src.risk.config import RiskConfig
from src.risk.manager import RiskManager


class RiskEngine:
    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()
        self.manager = RiskManager(self.config)
        self.sltp_calc = SLTPCalculator(self.config)
        self.sizer = PositionSizer()

    def generate_order(
        self, signal: Signal, current_price: float, account_balance: float
    ) -> Optional[Order]:
        """Avalia sinal e gera ordem ajustada ao risco, ou rejeita e retorna None."""
        if signal.direction == SignalType.NEUTRAL:
            return None

        if not self.manager.can_take_trade():
            return None

        # Calcula SL e TP
        atr_val = signal.metadata.get("atr")
        stop_loss, take_profit = self.sltp_calc.calculate(
            direction=signal.direction, entry_price=current_price, atr=atr_val
        )

        # Calcula o lote
        quantity = self.sizer.calculate_quantity(
            balance=account_balance,
            risk_pct=self.config.risk_per_trade_pct,
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