"""
Reliability Probe

Tracks tool success rates, consecutive failures, and error patterns to detect systemic issues.
"""

from collections import deque, defaultdict
from typing import Dict, List, Optional, Any
from datetime import datetime

from esass.probes.base import FilteringProbe, ProbeContext, LogEntry


class ReliabilityProbe(FilteringProbe):
    """
    Monitors tool reliability over time.

    Tracks:
    - Success/Failure rates per tool
    - Consecutive failure streaks
    - Error type distribution
    """

    def __init__(
        self, enabled: bool = True, window_size: int = 50, alert_threshold: int = 3
    ):
        """
        Args:
            enabled: Whether probe is active
            window_size: Number of recent calls to keep for stats
            alert_threshold: Consecutive failures before alerting
        """
        super().__init__(enabled)
        self.window_size = window_size
        self.alert_threshold = alert_threshold

        # Structure: {tool_name: deque([True, False, ...], maxlen=window_size)}
        self._history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))

        # Structure: {tool_name: count}
        self._consecutive_failures: Dict[str, int] = defaultdict(int)

        # Structure: {tool_name: {error_type: count}}
        self._error_counts: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

    def can_observe(self, event_type: str) -> bool:
        return event_type in ["tool_call_complete", "tool_call_error"]

    def observe_filtered(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        tool_name = context.event_data.get("tool_name")
        if not tool_name:
            return None

        success = context.event_data.get("success", False)
        error = context.event_data.get("error")

        # Update rolling history
        self._history[tool_name].append(success)

        entries = []

        if success:
            # Reset streaks
            self._consecutive_failures[tool_name] = 0
        else:
            # increment failure streak
            self._consecutive_failures[tool_name] += 1

            # Track error type
            error_type = str(error) if error else "Unknown"
            # Simple normalization of error strings to avoid infinite buckets
            error_key = error_type.split(":")[0] if ":" in error_type else error_type
            self._error_counts[tool_name][error_key] += 1

            # Check for alert condition
            if self._consecutive_failures[tool_name] >= self.alert_threshold:
                alert_entry = LogEntry.create(
                    event_type="reliability_alert",
                    event_data={
                        "tool_name": tool_name,
                        "alert_type": "consecutive_failures",
                        "count": self._consecutive_failures[tool_name],
                        "threshold": self.alert_threshold,
                        "recent_errors": dict(self._error_counts[tool_name]),
                    },
                    session_id=context.session_id,
                    tags=["alert", "reliability", "failure_streak"],
                )
                entries.append(alert_entry)

        return entries if entries else None

    def get_tool_stats(self, tool_name: str) -> Dict[str, Any]:
        """Return statistics for a specific tool"""
        history = list(self._history[tool_name])
        total = len(history)
        if total == 0:
            return {"total_calls": 0, "success_rate": 0.0, "failure_count": 0}

        success_count = sum(1 for x in history if x)
        return {
            "total_calls": total,
            "success_rate": success_count / total,
            "failure_count": total - success_count,
            "current_streak": self._consecutive_failures[tool_name],
            "errors": dict(self._error_counts[tool_name]),
        }
