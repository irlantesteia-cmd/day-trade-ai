from typing import Dict, Any, List, Optional
import time


class TradeAuditor:
    """
    Agente Auditor responsavel por registrar historico de ordens/trades,
    analisar erros de execucao (slippage, drawdowns) e preparar dados
    para o loop de re-treinamento do modelo.
    """

    def __init__(self):
        self.trade_history: List[Dict[str, Any]] = []

    def record_trade(
        self,
        order: Any,
        features_snapshot: Dict[str, Any],
        expected_price: float,
        pnl: float = 0.0,
    ) -> Dict[str, Any]:
        """Registra uma operacao com snapshot do mercado e metricas de desempenho."""
        executed_price = getattr(order, "price", expected_price)
        slippage = executed_price - expected_price

        trade_record = {
            "symbol": getattr(order, "symbol", "UNKNOWN"),
            "direction": str(getattr(order, "direction", "N/A")),
            "status": str(getattr(order, "status", "N/A")),
            "expected_price": expected_price,
            "executed_price": executed_price,
            "slippage": slippage,
            "pnl": pnl,
            "features": features_snapshot,
            "timestamp": time.time(),
        }
        self.trade_history.append(trade_record)
        return trade_record

    def get_performance_summary(self) -> Dict[str, Any]:
        """Gera um resumo do desempenho das operacoes auditadas."""
        if not self.trade_history:
            return {"total_trades": 0, "win_rate": 0.0, "avg_slippage": 0.0, "total_pnl": 0.0}

        total = len(self.trade_history)
        wins = sum(1 for t in self.trade_history if t["pnl"] > 0)
        total_pnl = sum(t["pnl"] for t in self.trade_history)
        avg_slippage = sum(t["slippage"] for t in self.trade_history) / total

        return {
            "total_trades": total,
            "win_rate": wins / total,
            "avg_slippage": avg_slippage,
            "total_pnl": total_pnl,
        }