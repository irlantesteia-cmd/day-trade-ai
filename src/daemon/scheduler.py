"""
Agendador de tarefas periodicas (sincrono, sem threads).

Design minimalista:
  - O daemon chama scheduler.tick(now) a cada iteracao do loop
  - Tarefas registradas com intervalo em segundos
  - Cada tarefa e uma callable sem argumentos
  - tick() executa apenas tarefas vencidas
  - Erros em uma tarefa nao impedem as demais

Sem dependencia de asyncio, threading ou cron. Simples e testavel.

Uso:
    sch = Scheduler()
    sch.every(30.0, "health_check", lambda: print("check"))
    sch.every(60.0, "snapshot", lambda: print("save"))
    while True:
        sch.tick()
        time.sleep(0.5)
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    name: str
    interval_sec: float
    func: Callable[[], None]
    last_run: Optional[float] = None
    last_error: Optional[str] = None
    run_count: int = 0
    error_count: int = 0


class Scheduler:
    """
    Agendador simples baseado em tempo monotônico.

    Nao usa datetime (evita problemas com NTP / fuso). Usa time.monotonic
    para ser resistente a mudancas de relogio do sistema.
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, ScheduledTask] = {}

    def every(
        self,
        interval_sec: float,
        name: str,
        func: Callable[[], None],
    ) -> None:
        """Registra (ou substitui) uma tarefa periodica."""
        if interval_sec <= 0:
            raise ValueError("interval_sec deve ser positivo")
        if not name:
            raise ValueError("name deve ser string nao vazia")
        if not callable(func):
            raise TypeError("func deve ser callable")

        self._tasks[name] = ScheduledTask(
            name=name,
            interval_sec=float(interval_sec),
            func=func,
        )

    def remove(self, name: str) -> None:
        """Remove uma tarefa. Silencioso se nao existir."""
        self._tasks.pop(name, None)

    def names(self) -> List[str]:
        return sorted(self._tasks.keys())

    def task(self, name: str) -> Optional[ScheduledTask]:
        return self._tasks.get(name)

    def due(self, now: Optional[float] = None) -> List[ScheduledTask]:
        """Retorna tarefas que devem rodar neste instante."""
        if now is None:
            now = time.monotonic()

        ready: List[ScheduledTask] = []
        for task in self._tasks.values():
            if task.last_run is None:
                ready.append(task)
            elif (now - task.last_run) >= task.interval_sec:
                ready.append(task)
        return ready

    def tick(self, now: Optional[float] = None) -> List[str]:
        """
        Executa tarefas vencidas. Retorna nomes das tarefas executadas.

        Excecoes em uma tarefa sao logadas e nao interrompem as demais.
        """
        if now is None:
            now = time.monotonic()

        executed: List[str] = []
        for task in self.due(now):
            try:
                task.func()
                task.last_error = None
            except Exception as exc:
                task.last_error = str(exc)
                task.error_count += 1
                logger.exception("Tarefa '%s' falhou: %s", task.name, exc)
            finally:
                task.last_run = now
                task.run_count += 1
                executed.append(task.name)

        return executed

    def reset(self) -> None:
        """Remove todas as tarefas e zera estado."""
        self._tasks.clear()