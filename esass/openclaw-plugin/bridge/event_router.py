"""
Event router.

Dispatches OpenClawEvent objects to registered handler callbacks
based on event type. Decouples event producers from consumers.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List

from .events import OpenClawEvent, OpenClawEventType

logger = logging.getLogger(__name__)

# Handler signature: (event: OpenClawEvent) -> None
HandlerFn = Callable[[OpenClawEvent], Any]


class EventRouter:
    """Routes OpenClaw events to registered handler functions."""

    def __init__(self) -> None:
        self._handlers: Dict[OpenClawEventType, List[HandlerFn]] = defaultdict(list)

    def register(self, event_type: OpenClawEventType, handler: HandlerFn) -> None:
        """Register a handler for a specific event type."""
        self._handlers[event_type].append(handler)

    def unregister(self, event_type: OpenClawEventType, handler: HandlerFn) -> None:
        """Remove a previously registered handler."""
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def dispatch(self, event: OpenClawEvent) -> None:
        """
        Dispatch an event to all registered handlers for its type.
        Errors in individual handlers are logged but do not stop dispatch.
        """
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Handler %s failed for event %s",
                    handler.__name__ if hasattr(handler, "__name__") else handler,
                    event.event_type.value,
                )

    @property
    def registered_types(self) -> List[OpenClawEventType]:
        """Return event types that have at least one handler."""
        return [et for et, hs in self._handlers.items() if hs]
