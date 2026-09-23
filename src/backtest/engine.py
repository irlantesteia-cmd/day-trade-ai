from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from src.domain.models import Candle
from src.execution.engine import ExecutionEngine
from src.risk.engine import RiskEngine
from src.backtest.metrics import PerformanceMetrics, calculate_metrics


class BacktestResult(BaseModel):
    initial_balance: float
    final_balance: float
    equity_curve: List[float]
    metrics: PerformanceMetrics


class BacktestEngine:
    def __init__(
        self,
        strategy: Any,
        risk_engine: Optional[RiskEngine] = None,
        initial_balance: float = 10000.0,
    ):
        self.strategy = strategy
        self.risk_engine = risk_engine or RiskEngine()
        self.execution_engine = ExecutionEngine(initial_balance=initial_balance)
        self.initial_balance = initial_balance

    def run(
        self,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
        feature_results: Optional[Dict[str, Any]] = None,
    ) -> BacktestResult:
        if not candles:
            raise ValueError("A lista de candles não pode estar vazia.")

        equity_curve: List[float] = [self.initial_balance]
        trade_pnls: List[float] = []
        last_cash = self.initial_balance

        # Processamento sequencial estilo time-series
        for i in range(1, len(candles) + 1):
            window = candles[:i]
            current_candle = window[-1]

            # 1. Atualizar PnL das posições abertas
            self.execution_engine.portfolio.update_positions_pnl(
                {current_candle.symbol: current_candle.close}
            )

            # 2. Avaliar Sinal da Estratégia
            signal = self.strategy.evaluate(
                candles=window,
                indicator_results=indicator_results,
                feature_results=feature_results,
            )

            # 3. Gerar Ordem via Risk Engine
            order = self.risk_engine.generate_order(
                signal=signal,
                current_price=current_candle.close,
                account_balance=self.execution_engine.portfolio.equity,
            )

            # 4. Executar Ordem se gerada
            if order:
                self.execution_engine.process_order(order, current_price=current_candle.close)

            # Registrar evolução do caixa e trades encerrados
            current_cash = self.execution_engine.portfolio.cash
            if current_cash != last_cash:
                trade_pnls.append(current_cash - last_cash)
                last_cash = current_cash

            equity_curve.append(self.execution_engine.portfolio.equity)

        metrics = calculate_metrics(equity_curve, trade_pnls, self.initial_balance)

        return BacktestResult(
            initial_balance=self.initial_balance,
            final_balance=self.execution_engine.portfolio.equity,
            equity_curve=equity_curve,
            metrics=metrics,
        )