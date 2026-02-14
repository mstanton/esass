"""MCP Event Logger for Dashboard Integration.

Writes MCP execution events to JSONL files in the shared ESASS data directory,
allowing the dashboard to poll and display them alongside tool usage events.
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _get_data_dir() -> Path:
    """Get the ESASS data directory."""
    return Path(
        os.environ.get("ESASS_DATA_DIR", str(Path.home() / ".esass" / "data"))
    )


def _generate_event_id() -> str:
    """Generate a short unique event ID."""
    now = datetime.now().isoformat()
    return hashlib.md5(f"mcp_{now}_{id(now)}".encode()).hexdigest()[:16]


class MCPEventLogger:
    """Logs MCP execution events to JSONL for dashboard consumption.

    Events are written to logs/mcp_events_{YYYYMMDD}.jsonl in the ESASS
    data directory. The dashboard reads these with incremental f.seek()
    polling, identical to how it reads tool usage logs.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or _get_data_dir()
        self.log_dir = self.data_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_event_file(self) -> Path:
        """Get today's MCP event file."""
        today = datetime.now().strftime("%Y%m%d")
        return self.log_dir / f"mcp_events_{today}.jsonl"

    def _append_event(self, event: dict) -> None:
        """Append an event to the daily JSONL file."""
        try:
            event_file = self._get_event_file()
            with open(event_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, default=str) + "\n")
        except Exception as e:
            logger.debug(f"Failed to write MCP event: {e}")

    def log_execution(
        self,
        skill_name: str,
        tier_requested: str,
        tier_used: str,
        fallback_used: bool,
        success: bool,
        tokens_used: int,
        latency_ms: float,
        cost_actual: float,
        cost_if_claude: float,
        savings: float,
        routing_reason: str,
        error: Optional[str] = None,
    ) -> None:
        """Log a skill execution event."""
        event = {
            "event_id": _generate_event_id(),
            "timestamp": datetime.now().isoformat(),
            "event_type": "mcp_execution",
            "event_data": {
                "skill_name": skill_name,
                "tier_requested": tier_requested,
                "tier_used": tier_used,
                "fallback_used": fallback_used,
                "success": success,
                "tokens_used": tokens_used,
                "latency_ms": round(latency_ms, 1),
                "cost_actual": round(cost_actual, 6),
                "cost_if_claude": round(cost_if_claude, 6),
                "savings": round(savings, 6),
                "routing_reason": routing_reason,
                "error": error,
            },
        }
        self._append_event(event)

    def log_circuit_breaker_change(
        self,
        name: str,
        old_state: str,
        new_state: str,
        reason: str,
    ) -> None:
        """Log a circuit breaker state change."""
        event = {
            "event_id": _generate_event_id(),
            "timestamp": datetime.now().isoformat(),
            "event_type": "mcp_circuit_breaker",
            "event_data": {
                "name": name,
                "old_state": old_state,
                "new_state": new_state,
                "reason": reason,
            },
        }
        self._append_event(event)

    def log_tier_override(
        self,
        skill_name: str,
        old_tier: str,
        new_tier: str,
        reason: str,
    ) -> None:
        """Log an adaptive routing tier override."""
        event = {
            "event_id": _generate_event_id(),
            "timestamp": datetime.now().isoformat(),
            "event_type": "mcp_tier_override",
            "event_data": {
                "skill_name": skill_name,
                "old_tier": old_tier,
                "new_tier": new_tier,
                "reason": reason,
            },
        }
        self._append_event(event)


# Singleton
_event_logger: Optional[MCPEventLogger] = None


def get_event_logger() -> MCPEventLogger:
    """Get the singleton event logger instance."""
    global _event_logger
    if _event_logger is None:
        _event_logger = MCPEventLogger()
    return _event_logger


def reset_event_logger() -> None:
    """Reset the singleton (for testing)."""
    global _event_logger
    _event_logger = None
