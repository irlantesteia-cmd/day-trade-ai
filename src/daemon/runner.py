"""
DaemonRunner - loop resiliente para operacao 24/7.

Caracteristicas:
  - Loop principal chama tick_fn() repetidamente
  - Se tick_fn levanta, tenta reconnect_fn com backoff exponencial
  - Graceful shutdown via SIGINT/SIGTERM (request_shutdown)
  - Scheduler opcional para tarefas periodicas (health, snapshot)
  - StateStore opcional para persistir stats e heartbeat
  - Injetavel: sleep_fn e max_iterations permitem testar sem dormir

Nao cria threads. Toda a execucao e sincrona. Isso torna o
comportamento previsivel e o shutdown deterministico.
"""
import logging
import signal
import time
from typing import Callable, Optional

from src.daemon.scheduler import Scheduler
from src.daemon.state import StateStore

logger = logging.getLogger(__name__)


TickFn = Callable[[], None]
ReconnectFn = Callable[[], bool]


class DaemonRunner:
    def __init__(
        self,
        tick_fn: TickFn,
        reconnect_fn: Optional[ReconnectFn] = None,
        state_store: Optional[StateStore] = None,
        scheduler: Optional[Scheduler] = None,
        poll_interval_sec: float = 2.0,
        reconnect_backoff_sec: float = 5.0,
        max_reconnect_backoff_sec: float = 60.0,
        snapshot_interval_sec: float = 60.0,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        if poll_interval_sec <= 0:
            raise ValueError("poll_interval_sec deve ser positivo")
        if reconnect_backoff_sec <= 0:
            raise ValueError("reconnect_backoff_sec deve ser positivo")
        if max_reconnect_backoff_sec < reconnect_backoff_sec:
            raise ValueError("max_reconnect_backoff_sec < reconnect_backoff_sec")

        self.tick_fn = tick_fn
        self.reconnect_fn = reconnect_fn
        self.state_store = state_store
        self.scheduler = scheduler
        self.poll_interval_sec = float(poll_interval_sec)
        self.reconnect_backoff_sec = float(reconnect_backoff_sec)
        self.max_reconnect_backoff_sec = float(max_reconnect_backoff_sec)
        self.snapshot_interval_sec = float(snapshot_interval_sec)
        self.sleep_fn = sleep_fn

        self._shutdown_requested = False
        self._stats = {
            "iterations": 0,
            "ticks_ok": 0,
            "ticks_failed": 0,
            "reconnects_ok": 0,
            "reconnects_failed": 0,
        }

    # ------------------------------------------------------------------
    # Controle de shutdown
    # ------------------------------------------------------------------

    def request_shutdown(self) -> None:
        self._shutdown_requested = True

    def is_shutdown_requested(self) -> bool:
        return self._shutdown_requested

    def stats(self) -> dict:
        return dict(self._stats)

    def _install_signal_handlers(self) -> None:
        """Instala SIGINT/SIGTERM. Silencioso se nao estiver na main thread."""
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except (ValueError, OSError, AttributeError):
            # Nao esta na thread principal (testes) ou SO nao suporta
            pass

    def _signal_handler(self, signum, frame) -> None:
        logger.info("Sinal %s recebido, shutdown solicitado", signum)
        self.request_shutdown()

    # ------------------------------------------------------------------
    # Setup de tarefas periodicas
    # ------------------------------------------------------------------

    def _register_default_tasks(self) -> None:
        if self.scheduler is None:
            return

        if self.state_store is not None:
            self.scheduler.every(
                self.snapshot_interval_sec,
                "heartbeat",
                lambda: self.state_store.save_heartbeat("daemon_loop"),
            )
            self.scheduler.every(
                self.snapshot_interval_sec,
                "snapshot",
                self._snapshot_stats,
            )

    def _snapshot_stats(self) -> None:
        if self.state_store is not None:
            self.state_store.set("daemon_stats", self.stats())

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------

    def _safe_reconnect(self, current_backoff: float) -> float:
        """
        Tenta reconnect. Retorna o novo backoff a usar na proxima falha.

        - Se reconectou: retorna reconnect_backoff_sec (reset)
        - Se falhou: dorme current_backoff, retorna min(2x, max)
        """
        if self.reconnect_fn is None:
            self.sleep_fn(current_backoff)
            return min(current_backoff * 2.0, self.max_reconnect_backoff_sec)

        try:
            ok = self.reconnect_fn()
        except Exception as exc:
            logger.exception("reconnect_fn levantou: %s", exc)
            ok = False

        if ok:
            self._stats["reconnects_ok"] += 1
            logger.info("Reconexao bem-sucedida, resetando backoff")
            return self.reconnect_backoff_sec

        self._stats["reconnects_failed"] += 1
        logger.warning("Reconexao falhou, backoff=%.1fs", current_backoff)
        self.sleep_fn(current_backoff)
        return min(current_backoff * 2.0, self.max_reconnect_backoff_sec)

    def run(self, max_iterations: Optional[int] = None) -> dict:
        """
        Executa o loop principal.

        Args:
            max_iterations: se fornecido, para apos N iteracoes (util em testes)

        Returns:
            dict com estatisticas finais
        """
        self._install_signal_handlers()
        self._register_default_tasks()
        logger.info("DaemonRunner iniciado (poll=%.1fs)", self.poll_interval_sec)

        backoff = self.reconnect_backoff_sec

        while not self._shutdown_requested:
            if max_iterations is not None and self._stats["iterations"] >= max_iterations:
                break

            self._stats["iterations"] += 1

            # 1. Executa o tick
            try:
                self.tick_fn()
                self._stats["ticks_ok"] += 1
                backoff = self.reconnect_backoff_sec  # sucesso reseta backoff
            except Exception as exc:
                self._stats["ticks_failed"] += 1
                logger.exception("tick_fn falhou: %s", exc)
                backoff = self._safe_reconnect(backoff)

            # 2. Tick do scheduler
            if self.scheduler is not None:
                try:
                    self.scheduler.tick()
                except Exception:
                    logger.exception("scheduler.tick falhou")

            # 3. Sleep controlado
            if not self._shutdown_requested:
                self.sleep_fn(self.poll_interval_sec)

        # Persiste stats finais
        if self.state_store is not None:
            try:
                self._snapshot_stats()
                self.state_store.save_kill_switch("STOPPED", "daemon shutdown")
            except Exception:
                logger.exception("Falha ao persistir stats finais")

        logger.info("DaemonRunner finalizado. Stats: %s", self._stats)
        return self.stats()