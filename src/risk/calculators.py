from typing import Optional, Tuple
from src.domain.enums import SignalType
from src.risk.config import RiskConfig


class SLTPCalculator:
    def __init__(self, config: RiskConfig):
        self.config = config

    def calculate(
        self, direction: SignalType, entry_price: float, atr: Optional[float] = None
    ) -> Tuple[float, float]:
        """Calcula Stop Loss e Take Profit. Usa ATR se disponível, senão % fixo."""
        
        # Define a distância do stop (ATR multiplicador ou fixo %)
        if atr and atr > 0:
            sl_distance = atr * 1.5  # Exemplo: 1.5x ATR
        else:
            sl_distance = entry_price * (self.config.default_sl_pct / 100.0)

        tp_distance = sl_distance * self.config.reward_to_risk_ratio

        if direction == SignalType.BUY:
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
        else:  # SELL
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance

        return round(stop_loss, 4), round(take_profit, 4)


class PositionSizer:
    def calculate_quantity(
        self, balance: float, risk_pct: float, entry_price: float, stop_loss: float
    ) -> float:
        """Calcula a quantidade baseada no risco financeiro."""
        if entry_price == stop_loss:
            return 0.0
            
        risk_amount = balance * (risk_pct / 100.0)
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit == 0:
            return 0.0
            
        return round(risk_amount / risk_per_unit, 4)