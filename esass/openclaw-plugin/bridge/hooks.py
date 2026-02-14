"""
OpenClaw ↔ ESASS Bridge (rewritten).

Captures events from OpenClaw's agent loop, forwards to ESASS probes,
and integrates with donation display and usage tracing.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from .events import OpenClawEvent, OpenClawEventType
from .event_router import EventRouter

logger = logging.getLogger(__name__)


class OpenClawESASSBridge:
    """
    Bridges OpenClaw events to ESASS observation system, with donation
    notice emission and usage-tracing hooks.
    """

    def __init__(
        self,
        data_dir: str = "./data/esass",
        enable_feedback: bool = True,
        sample_rate: float = 1.0,
        donation_config: Optional[Any] = None,
        usage_tracker: Optional[Any] = None,
    ):
        self.data_dir = data_dir
        self.enable_feedback = enable_feedback
        self.sample_rate = sample_rate

        # ESASS system (lazy init to avoid hard import failures)
        self.registry: Optional[Any] = None
        self.pipeline: Optional[Any] = None
        self.config: Optional[Any] = None
        self._esass_initialised = False

        # Event router
        self.router = EventRouter()
        self._register_default_handlers()

        # Track active sessions and pending tools
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._pending_tools: Dict[str, Dict[str, Any]] = {}

        # Skill activation tracking for feedback loop
        self._skill_activations: Dict[str, list] = {}

        # Optional donation + tracing integrations
        self._donation_config = donation_config
        self._usage_tracker = usage_tracker

    # ---- Lazy ESASS init ----

    def _ensure_esass(self) -> None:
        """Initialise ESASS subsystem on first use."""
        if self._esass_initialised:
            return
        try:
            from esass.probes.config import initialize_system
            self.registry, self.pipeline, self.config = initialize_system()
            self._esass_initialised = True
        except Exception:
            logger.warning("ESASS probes not available; bridge running in passthrough mode")
            self._esass_initialised = True  # don't retry

    # ---- Handler registration ----

    def _register_default_handlers(self) -> None:
        self.router.register(OpenClawEventType.SESSION_START, self._handle_session_start)
        self.router.register(OpenClawEventType.SESSION_END, self._handle_session_end)
        self.router.register(OpenClawEventType.THINKING_BLOCK, self._handle_thinking)
        self.router.register(OpenClawEventType.TOOL_CALL_START, self._handle_tool_start)
        self.router.register(OpenClawEventType.TOOL_CALL_COMPLETE, self._handle_tool_complete)
        self.router.register(OpenClawEventType.TOOL_CALL_ERROR, self._handle_tool_error)
        self.router.register(OpenClawEventType.SKILL_ACTIVATED, self._handle_skill_activated)
        self.router.register(OpenClawEventType.SKILL_COMPLETED, self._handle_skill_completed)
        self.router.register(OpenClawEventType.APPROACH_SELECTED, self._handle_decision)

    # ---- Public API ----

    def on_event(self, event: OpenClawEvent) -> None:
        """Main event handler – routes via the EventRouter (sync)."""
        self._ensure_esass()
        self.router.dispatch(event)

    async def on_event_async(self, event: OpenClawEvent) -> None:
        """Async wrapper for compatibility with async callers."""
        self.on_event(event)

    # ---- Internal handlers ----

    def _handle_session_start(self, event: OpenClawEvent) -> None:
        self._sessions[event.session_id] = {
            "start_time": event.timestamp,
            "channel": event.channel,
            "user_id": event.user_id,
            "agent_id": event.agent_id,
            "events": [],
        }

    def _handle_session_end(self, event: OpenClawEvent) -> None:
        self._sessions.pop(event.session_id, None)

    @staticmethod
    def _ctx_dict(event: OpenClawEvent, extra: Optional[dict] = None) -> dict:
        """Build a plain-dict context for registry.notify()."""
        ctx = {"session_id": event.session_id}
        if event.timestamp:
            ctx["timestamp"] = event.timestamp.isoformat() if hasattr(event.timestamp, "isoformat") else str(event.timestamp)
        if extra:
            ctx.update(extra)
        return ctx

    def _handle_thinking(self, event: OpenClawEvent) -> None:
        if not self.registry:
            return
        self.registry.notify(
            event_type="thinking_block",
            event_data={
                "content": event.data.get("content", ""),
                "thinking_type": event.data.get("type", "general"),
            },
            context=self._ctx_dict(event, {
                "channel": event.channel,
                "user_id": event.user_id,
                "correlation_id": event.correlation_id,
            }),
        )

    def _handle_tool_start(self, event: OpenClawEvent) -> None:
        tool_name = event.data.get("tool_name", "unknown")
        parameters = event.data.get("parameters", {})
        call_id = event.data.get("call_id", str(event.timestamp.timestamp()))

        if self.registry:
            tool_data = {"call_id": call_id, "tool_name": tool_name, "parameters": parameters}
            ctx = self._ctx_dict(event, {"channel": event.channel, "correlation_id": event.correlation_id})
            self._pending_tools[call_id] = {
                "tool_name": tool_name,
                "start_time": event.timestamp,
                "context": ctx,
            }
            self.registry.notify(event_type="tool_call_start", event_data=tool_data, context=ctx)

    def _handle_tool_complete(self, event: OpenClawEvent) -> None:
        call_id = event.data.get("call_id")
        if not call_id or call_id not in self._pending_tools or not self.registry:
            return
        pending = self._pending_tools.pop(call_id)
        self.registry.notify(
            event_type="tool_call_complete",
            event_data={
                "call_id": call_id,
                "tool_name": pending["tool_name"],
                "result": event.data.get("result"),
                "success": event.data.get("success", True),
                "duration_ms": (event.timestamp - pending["start_time"]).total_seconds() * 1000,
            },
            context=pending["context"],
        )

    def _handle_tool_error(self, event: OpenClawEvent) -> None:
        call_id = event.data.get("call_id")
        if not call_id or call_id not in self._pending_tools or not self.registry:
            return
        pending = self._pending_tools.pop(call_id)
        self.registry.notify(
            event_type="tool_call_error",
            event_data={
                "call_id": call_id,
                "tool_name": pending["tool_name"],
                "error_type": event.data.get("error_type", "unknown"),
                "error_message": event.data.get("error_message", ""),
            },
            context=pending["context"],
        )

    def _handle_skill_activated(self, event: OpenClawEvent) -> None:
        skill_name = event.data.get("skill_name")
        skill_id = event.data.get("skill_id", "")
        if not skill_name:
            return

        # Track activation
        if skill_name not in self._skill_activations:
            self._skill_activations[skill_name] = []
        self._skill_activations[skill_name].append({
            "session_id": event.session_id,
            "timestamp": event.timestamp,
            "trigger": event.data.get("trigger"),
            "context": event.data.get("context"),
        })

        # Forward to ESASS probes
        if self.registry:
            probe_data = {"decision": f"skill:{skill_name}", "trigger": event.data.get("trigger"), "is_skill": True}
            self.registry.notify(event_type="tool_selected", event_data=probe_data, context=self._ctx_dict(event))

        # Usage tracing
        if self._usage_tracker:
            self._usage_tracker.record_activation(
                skill_id=skill_id,
                skill_name=skill_name,
                session_id=event.session_id,
                user_id=event.user_id or "",
                agent_id=event.agent_id or "",
                trigger_context=str(event.data.get("trigger", "")),
            )

        # Funding notice (non-blocking, informational)
        if self._donation_config and self._donation_config.enabled and self._donation_config.show_on_activation:
            from openclaw_plugin.donation.display import DonationDisplay
            display = DonationDisplay(self._donation_config)
            msg = display.render_activation_message(skill_name)
            if msg:
                logger.info(msg)
            # Emit funding_notice event so listeners can pick it up
            notice_event = OpenClawEvent(
                event_type=OpenClawEventType.FUNDING_NOTICE,
                timestamp=datetime.utcnow(),
                session_id=event.session_id,
                data=display.render_for_agent(skill_name),
            )
            self.router.dispatch(notice_event)

    def _handle_skill_completed(self, event: OpenClawEvent) -> None:
        skill_name = event.data.get("skill_name")
        skill_id = event.data.get("skill_id", "")
        success = event.data.get("success", True)

        # Update in-memory activation record
        if skill_name in self._skill_activations:
            for activation in reversed(self._skill_activations[skill_name]):
                if activation["session_id"] == event.session_id:
                    activation["outcome"] = "success" if success else "failure"
                    activation["completed_at"] = event.timestamp
                    break

        # Usage tracing
        if self._usage_tracker:
            duration_ms = event.data.get("duration_ms", 0.0)
            self._usage_tracker.record_completion(
                skill_id=skill_id,
                skill_name=skill_name or "",
                session_id=event.session_id,
                success=success,
                duration_ms=duration_ms,
                error_type=event.data.get("error_type"),
                user_id=event.user_id or "",
                agent_id=event.agent_id or "",
            )

    def _handle_decision(self, event: OpenClawEvent) -> None:
        if not self.registry:
            return
        dec_data = {
            "decision": event.data.get("approach"),
            "options": event.data.get("alternatives", []),
            "rationale": event.data.get("rationale", ""),
        }
        self.registry.notify(event_type="tool_selected", event_data=dec_data, context=self._ctx_dict(event))

    # ---- Feedback ----

    def get_skill_feedback(self, skill_name: str) -> Dict[str, Any]:
        if skill_name not in self._skill_activations:
            return {"activations": 0, "success_rate": 0.0}
        activations = self._skill_activations[skill_name]
        completed = [a for a in activations if "outcome" in a]
        successes = [a for a in completed if a["outcome"] == "success"]
        return {
            "activations": len(activations),
            "completions": len(completed),
            "successes": len(successes),
            "success_rate": len(successes) / len(completed) if completed else 0.0,
        }

    # ---- Lifecycle ----

    def flush(self) -> None:
        if self.registry:
            self.registry.flush()
        if self.pipeline:
            self.pipeline.flush()

    def shutdown(self) -> None:
        self.flush()
        if self.pipeline:
            self.pipeline.shutdown()


# Singleton
_bridge_instance: Optional[OpenClawESASSBridge] = None


def get_bridge(**kwargs: Any) -> OpenClawESASSBridge:
    """Get or create the bridge singleton."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = OpenClawESASSBridge(
            data_dir=os.environ.get("ESASS_DATA_DIR", "./data/esass"),
            sample_rate=float(os.environ.get("ESASS_SAMPLE_RATE", "1.0")),
            **kwargs,
        )
    return _bridge_instance


def emit_event(event_type: str, session_id: str, data: dict, **kwargs: Any) -> None:
    """Emit an event to ESASS from OpenClaw (sync version)."""
    bridge = get_bridge()
    event = OpenClawEvent(
        event_type=OpenClawEventType(event_type),
        timestamp=datetime.utcnow(),
        session_id=session_id,
        data=data,
        **kwargs,
    )
    bridge.on_event(event)
