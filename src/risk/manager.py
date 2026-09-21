from src.risk.config import RiskConfig


class RiskManager:
    def __init__(self, config: RiskConfig):
        self.config = config
        self.daily_pnl_pct: float = 0.0
        self.open_positions_count: int = 0

    def update_state(self, daily_pnl_pct: float, open_positions_count: int):
        self.daily_pnl_pct = daily_pnl_pct
        self.open_positions_count = open_positions_count

    def can_take_trade(self) -> bool:
        if self.daily_pnl_pct <= -self.config.max_daily_drawdown_pct:
            return False
        
        if self.open_positions_count >= self.config.max_open_positions:
            return False
            
        return True