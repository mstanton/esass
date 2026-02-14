"""Loop phase enumeration."""

from enum import Enum


class LoopPhase(Enum):
    """Current phase of the recursive loop."""
    IDLE = "idle"
    OBSERVING = "observing"
    DETECTING = "detecting"
    GENERATING = "generating"
    PUBLISHING = "publishing"
    SYNCING = "syncing"
