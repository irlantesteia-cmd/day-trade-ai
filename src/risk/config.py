from pydantic import BaseModel


class RiskConfig(BaseModel):
    max_daily_drawdown_pct: float = 5.0  # Limite máximo de perda diária (%)
    max_open_positions: int = 3          # Máximo de posições simultâneas
    risk_per_trade_pct: float = 1.0      # Risco financeiro por trade (%)
    reward_to_risk_ratio: float = 2.0    # Relação Risco/Retorno padrão
    default_sl_pct: float = 1.0          # Stop loss % padrão caso não haja ATR