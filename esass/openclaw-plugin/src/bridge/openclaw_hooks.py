"""
OpenClaw Event Hooks for ESASS Integration

Captures events from OpenClaw's agent loop and forwards them to ESASS probes.
"""

import json
import asyncio
from datetime import datetime
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
import os

# ESASS imports
from esass.probes.config import initialize_system
from esass.probes.registry import GlobalRegistry


class OpenClawEventType(Enum):
    """Event types emitted by OpenClaw agent loop"""
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


@dataclass
class OpenClawEvent:
    """Structured event from OpenClaw"""
    event_type: OpenClawEventType
    timestamp: datetime
    session_id: str
    data: dict = field(default_factory=dict)
    channel: Optional[str] = None  # whatsapp, telegram, etc.
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    correlation_id: Optional[str] = None  # For event causality


class OpenClawESASSBridge:
    """
    Bridges OpenClaw events to ESASS observation system.

    This is the primary integration point that hooks into OpenClaw's
    agent loop and translates events for ESASS pattern detection.
    """

    def __init__(
        self,
        data_dir: str = "./data/esass",
        enable_feedback: bool = True,
        sample_rate: float = 1.0
    ):
        self.data_dir = data_dir
        self.enable_feedback = enable_feedback
        self.sample_rate = sample_rate

        # Initialize ESASS system
        self.registry, self.pipeline, self.config = initialize_system(
            data_dir=data_dir,
            sample_rate=sample_rate
        )

        # Track active sessions
        self._sessions: dict[str, dict] = {}
        self._pending_tools: dict[str, dict] = {}

        # Skill usage tracking for feedback loop
        self._skill_activations: dict[str, list] = {}

    async def on_event(self, event: OpenClawEvent) -> None:
        """
        Main event handler - routes OpenClaw events to appropriate ESASS probes.
        """
        handlers = {
            OpenClawEventType.SESSION_START: self._handle_session_start,
            OpenClawEventType.SESSION_END: self._handle_session_end,
            OpenClawEventType.THINKING_BLOCK: self._handle_thinking,
            OpenClawEventType.TOOL_CALL_START: self._handle_tool_start,
            OpenClawEventType.TOOL_CALL_COMPLETE: self._handle_tool_complete,
            OpenClawEventType.TOOL_CALL_ERROR: self._handle_tool_error,
            OpenClawEventType.SKILL_ACTIVATED: self._handle_skill_activated,
            OpenClawEventType.SKILL_COMPLETED: self._handle_skill_completed,
            OpenClawEventType.APPROACH_SELECTED: self._handle_decision,
        }

        handler = handlers.get(event.event_type)
        if handler:
            await handler(event)

    async def _handle_session_start(self, event: OpenClawEvent) -> None:
        """Track new session"""
        self._sessions[event.session_id] = {
            "start_time": event.timestamp,
            "channel": event.channel,
            "user_id": event.user_id,
            "agent_id": event.agent_id,
            "events": []
        }

    async def _handle_session_end(self, event: OpenClawEvent) -> None:
        """Finalize session and flush events"""
        if event.session_id in self._sessions:
            session = self._sessions.pop(event.session_id)
            # Session data is already logged via probes

    async def _handle_thinking(self, event: OpenClawEvent) -> None:
        """Forward thinking blocks to ReasoningProbe"""
        from esass.probes.base import ProbeContext

        context = ProbeContext(
            session_id=event.session_id,
            timestamp=event.timestamp,
            metadata={
                "channel": event.channel,
                "user_id": event.user_id,
                "correlation_id": event.correlation_id
            }
        )

        self.registry.notify(
            event_type="thinking_block",
            data={
                "content": event.data.get("content", ""),
                "thinking_type": event.data.get("type", "general")
            },
            context=context
        )

    async def _handle_tool_start(self, event: OpenClawEvent) -> None:
        """Forward tool execution start to ToolCallProbe"""
        from esass.probes.base import ProbeContext

        tool_name = event.data.get("tool_name", "unknown")
        parameters = event.data.get("parameters", {})
        call_id = event.data.get("call_id", str(event.timestamp.timestamp()))

        context = ProbeContext(
            session_id=event.session_id,
            timestamp=event.timestamp,
            metadata={
                "channel": event.channel,
                "correlation_id": event.correlation_id
            }
        )

        # Store for completion matching
        self._pending_tools[call_id] = {
            "tool_name": tool_name,
            "start_time": event.timestamp,
            "context": context
        }

        self.registry.notify(
            event_type="tool_call_start",
            data={
                "call_id": call_id,
                "tool_name": tool_name,
                "parameters": parameters
            },
            context=context
        )

    async def _handle_tool_complete(self, event: OpenClawEvent) -> None:
        """Forward tool completion to ToolCallProbe"""
        call_id = event.data.get("call_id")

        if call_id and call_id in self._pending_tools:
            pending = self._pending_tools.pop(call_id)

            self.registry.notify(
                event_type="tool_call_complete",
                data={
                    "call_id": call_id,
                    "tool_name": pending["tool_name"],
                    "result": event.data.get("result"),
                    "success": event.data.get("success", True),
                    "duration_ms": (
                        event.timestamp - pending["start_time"]
                    ).total_seconds() * 1000
                },
                context=pending["context"]
            )

    async def _handle_tool_error(self, event: OpenClawEvent) -> None:
        """Forward tool errors to ToolCallProbe"""
        call_id = event.data.get("call_id")

        if call_id and call_id in self._pending_tools:
            pending = self._pending_tools.pop(call_id)

            self.registry.notify(
                event_type="tool_call_error",
                data={
                    "call_id": call_id,
                    "tool_name": pending["tool_name"],
                    "error_type": event.data.get("error_type", "unknown"),
                    "error_message": event.data.get("error_message", "")
                },
                context=pending["context"]
            )

    async def _handle_skill_activated(self, event: OpenClawEvent) -> None:
        """Track skill activation for feedback loop"""
        skill_name = event.data.get("skill_name")

        if skill_name:
            if skill_name not in self._skill_activations:
                self._skill_activations[skill_name] = []

            self._skill_activations[skill_name].append({
                "session_id": event.session_id,
                "timestamp": event.timestamp,
                "trigger": event.data.get("trigger"),
                "context": event.data.get("context")
            })

            # Emit as decision event
            from esass.probes.base import ProbeContext
            context = ProbeContext(
                session_id=event.session_id,
                timestamp=event.timestamp
            )

            self.registry.notify(
                event_type="tool_selected",
                data={
                    "decision": f"skill:{skill_name}",
                    "trigger": event.data.get("trigger"),
                    "is_skill": True
                },
                context=context
            )

    async def _handle_skill_completed(self, event: OpenClawEvent) -> None:
        """Track skill completion for feedback"""
        skill_name = event.data.get("skill_name")
        success = event.data.get("success", True)

        # Update activation record with outcome
        if skill_name in self._skill_activations:
            activations = self._skill_activations[skill_name]
            for activation in reversed(activations):
                if activation["session_id"] == event.session_id:
                    activation["outcome"] = "success" if success else "failure"
                    activation["completed_at"] = event.timestamp
                    break

    async def _handle_decision(self, event: OpenClawEvent) -> None:
        """Forward decision points to DecisionProbe"""
        from esass.probes.base import ProbeContext

        context = ProbeContext(
            session_id=event.session_id,
            timestamp=event.timestamp
        )

        self.registry.notify(
            event_type="tool_selected",
            data={
                "decision": event.data.get("approach"),
                "options": event.data.get("alternatives", []),
                "rationale": event.data.get("rationale", "")
            },
            context=context
        )

    def get_skill_feedback(self, skill_name: str) -> dict:
        """Get feedback metrics for a skill"""
        if skill_name not in self._skill_activations:
            return {"activations": 0, "success_rate": 0.0}

        activations = self._skill_activations[skill_name]
        completed = [a for a in activations if "outcome" in a]
        successes = [a for a in completed if a["outcome"] == "success"]

        return {
            "activations": len(activations),
            "completions": len(completed),
            "successes": len(successes),
            "success_rate": len(successes) / len(completed) if completed else 0.0
        }

    def flush(self) -> None:
        """Flush all pending events"""
        self.registry.flush()
        self.pipeline.flush()

    def shutdown(self) -> None:
        """Graceful shutdown"""
        self.flush()
        self.pipeline.shutdown()


# Singleton bridge instance
_bridge_instance: Optional[OpenClawESASSBridge] = None


def get_bridge() -> OpenClawESASSBridge:
    """Get or create the bridge singleton"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = OpenClawESASSBridge(
            data_dir=os.environ.get("ESASS_DATA_DIR", "./data/esass"),
            sample_rate=float(os.environ.get("ESASS_SAMPLE_RATE", "1.0"))
        )
    return _bridge_instance


# Convenience functions for OpenClaw integration
async def emit_event(event_type: str, session_id: str, data: dict, **kwargs) -> None:
    """Emit an event to ESASS from OpenClaw"""
    bridge = get_bridge()
    event = OpenClawEvent(
        event_type=OpenClawEventType(event_type),
        timestamp=datetime.utcnow(),
        session_id=session_id,
        data=data,
        **kwargs
    )
    await bridge.on_event(event)
