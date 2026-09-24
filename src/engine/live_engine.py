"""
LiveTradingEngine - orquestra strategy -> risk -> execution.

Suporta dois modos de operacao:

  1. LEGADO (risk_manager + execute_signal):
     - risk_manager.validate_signal(signal) -> bool
     - execution_engine.execute_signal(signal, bar)
     - Usado quando risk_engine=None

  2. NOVO (risk_engine + execute_order):
     - risk_engine.manager.update_state(...) sincronizado com estado real
     - risk_engine.generate_order(signal, price, balance) -> Order | None
     - execution_engine.execute_order(order, bar)
     - Usado quando risk_engine != None

O modo novo implementa o fluxo da secao 33 do framework:
    Signal -> Risk Check -> OrderIntent -> Execution -> Broker -> Order

Limitacao conhecida (ADR-015):
  Apenas `open_positions_count` e sincronizado. `daily_pnl_pct` permanece
  0.0 porque requer um DailyPnLTracker (subsistema dedicado).
"""
import time
from typing import Dict, Any, Optional

from src.domain.models import Order
from src.telemetry.collector import MetricsCollector
from src.telemetry.health import SystemHealthMonitor


class LiveTradingEngine:
    def __init__(
        self,
        strategy: Any,
        risk_manager: Any = None,
        execution_engine: Any = None,
        metrics_collector: Optional[MetricsCollector] = None,
        health_monitor: Optional[SystemHealthMonitor] = None,
        risk_engine: Any = None,
    ):
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.execution_engine = execution_engine
        self.risk_engine = risk_engine
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.health_monitor = health_monitor or SystemHealthMonitor(self.metrics_collector)
        self.is_running = False

    def start(self) -> None:
        self.is_running = True
        self.health_monitor.record_heartbeat()

    def stop(self) -> None:
        self.is_running = False

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _current_price(self, bar: Dict[str, Any]) -> float:
        return float(bar.get("close", 0.0))

    def _current_balance(self) -> float:
        """Extrai balance do execution_engine.portfolio se disponivel."""
        portfolio = getattr(self.execution_engine, "portfolio", None)
        if portfolio is None:
            return 10000.0
        for attr in ("equity", "balance", "cash"):
            val = getattr(portfolio, attr, None)
            if val is not None:
                try:
                    return float(val)
                except (TypeError, ValueError):
                    continue
        return 10000.0

    def _current_open_positions(self) -> int:
        """Conta posicoes abertas no portfolio do execution_engine."""
        portfolio = getattr(self.execution_engine, "portfolio", None)
        if portfolio is None:
            return 0
        positions = getattr(portfolio, "positions", None)
        if isinstance(positions, dict):
            return len(positions)
        return 0

    def _sync_risk_manager_state(self) -> None:
        """
        Sincroniza o RiskManager interno do RiskEngine com o estado real
        do portfolio. Chamado antes de generate_order.

        Notas (ver ADR-015):
          - open_positions_count e lido de execution_engine.portfolio.positions
          - daily_pnl_pct permanece 0.0 (DailyPnLTracker fica para milestone
            futuro)
        """
        if self.risk_engine is None:
            return
        manager = getattr(self.risk_engine, "manager", None)
        if manager is None or not hasattr(manager, "update_state"):
            return

        open_positions = self._current_open_positions()
        try:
            manager.update_state(
                daily_pnl_pct=0.0,
                open_positions_count=open_positions,
            )
        except Exception:
            # Nao deixar falha de sincronizacao derrubar o pipeline
            self.metrics_collector.increment_counter("total_errors", 1.0)

    # ------------------------------------------------------------------
    # Pipeline principal
    # ------------------------------------------------------------------

    def process_bar(self, bar: Dict[str, Any]) -> Optional[Order]:
        if not self.is_running:
            return None

        start_time = time.perf_counter()
        self.health_monitor.record_heartbeat()
        self.metrics_collector.increment_counter("bars_processed", 1.0)

        # 1. Geracao do Sinal
        signal = self.strategy.generate_signal(bar)
        if not signal:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            self.metrics_collector.record_latency("execution_time", duration_ms)
            return None

        self.metrics_collector.increment_counter("signals_generated", 1.0)

        # 2. Caminho NOVO: risk_engine gera Order
        if self.risk_engine is not None:
            return self._process_with_risk_engine(signal, bar, start_time)

        # 3. Caminho LEGADO: risk_manager booleano + execute_signal
        return self._process_legacy(signal, bar, start_time)

    def _process_with_risk_engine(
        self, signal: Any, bar: Dict[str, Any], start_time: float
    ) -> Optional[Order]:
        price = self._current_price(bar)
        balance = self._current_balance()

        # Sincroniza estado do RiskManager antes de gerar Order
        self._sync_risk_manager_state()

        try:
            order = self.risk_engine.generate_order(
                signal=signal,
                current_price=price,
                account_balance=balance,
            )
        except Exception:
            self.metrics_collector.increment_counter("total_errors", 1.0)
            raise

        if order is None:
            self.metrics_collector.increment_counter("signals_rejected_risk", 1.0)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            self.metrics_collector.record_latency("execution_time", duration_ms)
            return None

        executed = None
        try:
            if hasattr(self.execution_engine, "execute_order"):
                executed = self.execution_engine.execute_order(order, bar)
            else:
                # Fallback: broker direto
                executed = self.execution_engine.execute_signal(signal, bar)
            self.metrics_collector.increment_counter("orders_executed", 1.0)
        except Exception:
            self.metrics_collector.increment_counter("total_errors", 1.0)
            raise
        finally:
            self.metrics_collector.increment_counter("total_operations", 1.0)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            self.metrics_collector.record_latency("execution_time", duration_ms)

        return executed

    def _process_legacy(
        self, signal: Any, bar: Dict[str, Any], start_time: float
    ) -> Optional[Order]:
        is_approved = True
        if hasattr(self.risk_manager, "validate_signal"):
            is_approved = self.risk_manager.validate_signal(signal)

        if not is_approved:
            self.metrics_collector.increment_counter("signals_rejected_risk", 1.0)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            self.metrics_collector.record_latency("execution_time", duration_ms)
            return None

        order = None
        try:
            order = self.execution_engine.execute_signal(signal, bar)
            self.metrics_collector.increment_counter("orders_executed", 1.0)
        except Exception:
            self.metrics_collector.increment_counter("total_errors", 1.0)
            raise
        finally:
            self.metrics_collector.increment_counter("total_operations", 1.0)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            self.metrics_collector.record_latency("execution_time", duration_ms)

        return order