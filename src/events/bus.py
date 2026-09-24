"""
Event Bus sincrono.

Padrao: publish/subscribe com handlers registrados por EventType.
Segue o estilo do AlertManager (lista de handlers, try/except por handler),
mas tipado por EventType.

Design:
  - Sincrono: publish executa todos os handlers na hora (mesma thread)
  - Substituivel: handlers sao chamados na ordem de registro
  - Tolerante a falhas: excecao em um handler nao impede os demais
  - Rastreavel: opcionalmente mantem historico de eventos

NAO e thread-safe por design. Se concorrencia for necessaria no futuro,
envolver com Lock.
"""
import logging
from collections import defaultdict
from typing import Callable, Dict, List, Optional

from src.events.base import Event, EventType

logger = logging.getLogger(__name__)


EventHandler = Callable[[Event], None]


class EventBus:
    """
    Barramento de eventos sincrono.

    Uso:
        bus = EventBus()
        bus.subscribe(EventType.SIGNAL_GENERATED, minha_funcao)
        bus.publish(Event(event_type=EventType.SIGNAL_GENERATED, payload={...}))
    """

    def __init__(self, keep_history: bool = False, max_history: int = 1000):
        self._handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._wildcard_handlers: List[EventHandler] = []
        self._keep_history = keep_history
        self._max_history = max_history
        self._history: List[Event] = []

    # ------------------------------------------------------------------
    # Inscricao
    # ------------------------------------------------------------------

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Registra handler para um tipo especifico de evento."""
        if event_type not in EventType:
            raise ValueError(f"EventType invalido: {event_type}")
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Registra handler que recebe TODOS os eventos."""
        self._wildcard_handlers.append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Remove um handler especifico. Silencioso se nao existir."""
        handlers = self._handlers.get(event_type)
        if handlers and handler in handlers:
            handlers.remove(handler)

    def clear(self) -> None:
        """Remove todos os handlers e historico."""
        self._handlers.clear()
        self._wildcard_handlers.clear()
        self._history.clear()

    # ------------------------------------------------------------------
    # Publicacao
    # ------------------------------------------------------------------

    def publish(self, event: Event) -> None:
        """
        Publica um evento. Chama handlers especificos e wildcard.

        Excecoes em handlers sao logadas e engolidas (nao interrompem
        os demais handlers).
        """
        if not isinstance(event, Event):
            raise TypeError(f"publish espera Event, recebeu {type(event).__name__}")

        if self._keep_history:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        all_handlers = list(self._handlers.get(event.event_type, []))
        all_handlers.extend(self._wildcard_handlers)

        for handler in all_handlers:
            try:
                handler(event)
            except Exception as exc:
                logger.exception(
                    "Handler %s falhou ao processar evento %s: %s",
                    getattr(handler, "__name__", repr(handler)),
                    event.event_type.value,
                    exc,
                )

    # ------------------------------------------------------------------
    # Introspeccao
    # ------------------------------------------------------------------

    def handlers_count(self, event_type: Optional[EventType] = None) -> int:
        """Conta handlers registrados para um tipo, ou total se None."""
        if event_type is None:
            total = sum(len(h) for h in self._handlers.values())
            total += len(self._wildcard_handlers)
            return total
        return len(self._handlers.get(event_type, [])) + len(self._wildcard_handlers)

    def get_history(self) -> List[Event]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()