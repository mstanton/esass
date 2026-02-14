"""Bridge module: event routing from OpenClaw to ESASS."""

from .events import OpenClawEventType, OpenClawEvent
from .event_router import EventRouter
from .hooks import OpenClawESASSBridge, get_bridge, emit_event

__all__ = [
    "OpenClawEventType",
    "OpenClawEvent",
    "EventRouter",
    "OpenClawESASSBridge",
    "get_bridge",
    "emit_event",
]
