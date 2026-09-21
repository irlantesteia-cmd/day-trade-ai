import math
import statistics
from typing import List
from pydantic import BaseModel


class PerformanceMetrics(BaseModel):
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0


def calculate_metrics(
    equity_curve: List[float], trade_pnls: List[float], initial_balance: float
) -> PerformanceMetrics:
    if not equity_curve or initial_balance <= 0:
        return PerformanceMetrics()

    total_trades = len(trade_pnls)
    winning_trades = sum(1 for pnl in trade_pnls if pnl > 0)
    losing_trades = sum(1 for pnl in trade_pnls if pnl < 0)
    win_rate = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0

    gross_profit = sum(pnl for pnl in trade_pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in trade_pnls if pnl < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)

    total_pnl = equity_curve[-1] - initial_balance
    total_pnl_pct = (total_pnl / initial_balance) * 100.0

    # Max Drawdown
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak * 100.0 if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    # Sharpe Ratio baseado na biblioteca padrão (math e statistics)
    returns = [
        (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
        for i in range(1, len(equity_curve))
        if equity_curve[i - 1] != 0
    ]

    if len(returns) > 1:
        mean_ret = statistics.mean(returns)
        stdev_ret = statistics.stdev(returns)
        sharpe_ratio = (mean_ret / stdev_ret * math.sqrt(252)) if stdev_ret > 0 else 0.0
    else:
        sharpe_ratio = 0.0

    return PerformanceMetrics(
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=round(win_rate, 2),
        profit_factor=round(profit_factor, 2),
        total_pnl=round(total_pnl, 2),
        total_pnl_pct=round(total_pnl_pct, 2),
        max_drawdown_pct=round(max_dd, 2),
        sharpe_ratio=round(sharpe_ratio, 2),
    )