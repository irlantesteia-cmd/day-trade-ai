from typing import Dict, List, Optional
from pydantic import BaseModel

from src.backtest.metrics import PerformanceMetrics
from src.data.engine import DataEngine
from src.domain.models import Candle, Order, Signal
from src.execution.executor import ExecutionEngine
from src.features.engine import FeatureEngine
from src.indicators.engine import IndicatorEngine
from src.risk.engine import RiskEngine
from src.strategies.engine import StrategyEngine


class PipelineRunResult(BaseModel):
    candles_processed: int
    signals_generated: List[Signal]
    orders_executed: List[Order]
    metrics: Optional[PerformanceMetrics] = None


class TradingPipeline:
    def __init__(
        self,
        initial_balance: float = 10000.0,
        risk_engine: Optional[RiskEngine] = None,
    ):
        self.data_engine = DataEngine()
        self.indicator_engine = IndicatorEngine()
        self.feature_engine = FeatureEngine()
        self.strategy_engine = StrategyEngine()
        self.risk_engine = risk_engine or RiskEngine()
        self.execution_engine = ExecutionEngine(initial_balance=initial_balance)

    def process_candle_series(
        self, candles: List[Candle], strategy_name: str = "moving_average"
    ) -> PipelineRunResult:
        """Processa uma série de candles através de toda a esteira do sistema."""
        if not candles:
            raise ValueError("A lista de candles não pode estar vazia.")

        signals_generated: List[Signal] = []
        orders_executed: List[Order] = []

        # 1. Registrar candles na engine de dados
        self.data_engine.add_candles(candles)

        # 2. Processar a esteira candle a candle
        for i in range(1, len(candles) + 1):
            window = candles[:i]
            current_candle = window[-1]

            # A. Calcular Indicadores Tecnicos
            indicators = self.indicator_engine.compute_all(window)

            # B. Calcular Features
            features = self.feature_engine.compute_features(window, indicators)

            # C. Avaliar Estratégia e Gerar Sinal
            signal = self.strategy_engine.evaluate_strategy(
                strategy_name=strategy_name,
                candles=window,
                indicator_results=indicators,
                feature_results=features,
            )

            if signal.direction.value != "NEUTRAL":
                signals_generated.append(signal)

            # D. Filtrar pelo Risco e Gerar Ordem
            order = self.risk_engine.generate_order(
                signal=signal,
                current_price=current_candle.close,
                account_balance=self.execution_engine.portfolio.equity,
            )

            # E. Executar no Paper Broker
            if order:
                executed = self.execution_engine.process_order(
                    order, current_price=current_candle.close
                )
                if executed:
                    orders_executed.append(executed)

        return PipelineRunResult(
            candles_processed=len(candles),
            signals_generated=signals_generated,
            orders_executed=orders_executed,
        )