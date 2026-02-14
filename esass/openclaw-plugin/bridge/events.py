"""
OpenClaw event types and structured event dataclass.

Extracted from the original openclaw_hooks.py for better modularity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class OpenClawEventType(Enum):
    """Event types emitted by OpenClaw agent loop."""
    # Agent lifecycle
    SESSION_START = "session_start"
    SESSION_END = "session_end"

    # Message flow
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"

    # Agent reasoning
    THINKING_START = "thinking_start"
    THINKING_BLOCK = "thinking_block"
    THINKING_END = "thinking_end"

    # Tool execution
    TOOL_SELECTED = "tool_selected"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_COMPLETE = "tool_call_complete"
    TOOL_CALL_ERROR = "tool_call_error"

    # Skill usage
    SKILL_ACTIVATED = "skill_activated"
    SKILL_COMPLETED = "skill_completed"
    SKILL_FAILED = "skill_failed"

    # Decision points
    APPROACH_SELECTED = "approach_selected"
    PLAN_MODE_ENTERED = "plan_mode_entered"

    # Donation (informational)
    FUNDING_NOTICE = "funding_notice"


@dataclass
class OpenClawEvent:
    """Structured event from OpenClaw."""
    event_type: OpenClawEventType
    timestamp: datetime
    session_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    channel: Optional[str] = None
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    correlation_id: Optional[str] = None
