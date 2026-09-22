import math
from typing import List, Dict, Any


class PerformanceReporter:
    """
    Calcula metricas de desempenho quantitativo (Sharpe, Profit Factor, Drawdown, Expectancy)
    a partir do historico de trades do TradeAuditor.
    """

    def generate_report(self, trade_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not trade_history:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "total_pnl": 0.0,
                "expectancy": 0.0,
            }

        pnls = [float(t.get("pnl", 0.0)) for t in trade_history]
        total_trades = len(pnls)
        wins = [p for p in pnls if p > 0]
        losses = [abs(p) for p in pnls if p < 0]

        total_pnl = sum(pnls)
        win_count = len(wins)
        win_rate = win_count / total_trades if total_trades > 0 else 0.0

        gross_profit = sum(wins)
        gross_loss = sum(losses)
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)

        avg_win = gross_profit / win_count if win_count > 0 else 0.0
        loss_count = len(losses)
        avg_loss = gross_loss / loss_count if loss_count > 0 else 0.0
        loss_rate = 1.0 - win_rate
        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)

        peak = 0.0
        cumulative = 0.0
        max_dd = 0.0

        for pnl in pnls:
            cumulative += pnl
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd

        sharpe = 0.0
        if total_trades > 1:
            mean_pnl = total_pnl / total_trades
            variance = sum((p - mean_pnl) ** 2 for p in pnls) / (total_trades - 1)
            std_dev = math.sqrt(variance)
            if std_dev > 0:
                sharpe = (mean_pnl / std_dev) * math.sqrt(252)

        return {
            "total_trades": total_trades,
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4),
            "sharpe_ratio": round(sharpe, 4),
            "max_drawdown": round(max_dd, 2),
            "total_pnl": round(total_pnl, 2),
            "expectancy": round(expectancy, 2),
        }