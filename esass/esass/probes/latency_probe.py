"""
Latency Probe

Tracks tool execution times by measuring delta between tool_call_start
and tool_call_complete events. (ENHANCEMENT.md Phase 2.1)
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from esass.probes.base import FilteringProbe, ProbeContext, LogEntry


@dataclass
class ToolLatencyStats:
    """Statistics for a single tool's latency."""
    tool_name: str
    call_count: int = 0
    total_ms: float = 0.0
    min_ms: float = float('inf')
    max_ms: float = 0.0
    last_latency_ms: float = 0.0

    @property
    def avg_ms(self) -> float:
        """Average latency in milliseconds."""
        return self.total_ms / self.call_count if self.call_count > 0 else 0.0

    def record(self, latency_ms: float) -> None:
        """Record a new latency measurement."""
        self.call_count += 1
        self.total_ms += latency_ms
        self.min_ms = min(self.min_ms, latency_ms)
        self.max_ms = max(self.max_ms, latency_ms)
        self.last_latency_ms = latency_ms

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "tool_name": self.tool_name,
            "call_count": self.call_count,
            "avg_ms": round(self.avg_ms, 2),
            "min_ms": round(self.min_ms, 2) if self.min_ms != float('inf') else 0.0,
            "max_ms": round(self.max_ms, 2),
            "last_latency_ms": round(self.last_latency_ms, 2),
        }


class LatencyProbe(FilteringProbe):
    """
    Monitors tool execution latency.

    Tracks:
    - Per-tool average response times
    - Min/max latency per tool
    - Total call counts
    - Latency anomalies (>2x average)

    Events observed:
    - tool_call_start: Records start timestamp
    - tool_call_complete: Calculates latency delta
    """

    # Latency thresholds (milliseconds)
    SLOW_THRESHOLD_MS = 5000  # 5 seconds
    ANOMALY_MULTIPLIER = 2.0  # Flag if >2x average

    def __init__(self, enabled: bool = True, **kwargs):
        super().__init__(enabled=enabled, **kwargs)

        # Track pending tool calls: call_id -> (tool_name, start_time)
        self._pending_calls: Dict[str, tuple] = {}

        # Latency statistics per tool
        self._tool_stats: Dict[str, ToolLatencyStats] = defaultdict(
            lambda: ToolLatencyStats(tool_name="unknown")
        )

        # Recent latency history for trend analysis
        self._recent_latencies: List[tuple] = []  # (timestamp, tool, latency_ms)
        self._max_history = 100

    def can_observe(self, event_type: str) -> bool:
        return event_type in ["tool_call_start", "tool_call_complete"]

    def observe_filtered(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        event_type = context.event_type
        data = context.event_data

        if event_type == "tool_call_start":
            return self._handle_start(context, data)
        elif event_type == "tool_call_complete":
            return self._handle_complete(context, data)

        return None

    def _handle_start(self, context: ProbeContext, data: dict) -> Optional[List[LogEntry]]:
        """Record start of a tool call."""
        # Use call_id from data, or generate from tool name + timestamp
        call_id = data.get("call_id") or data.get("event_id") or f"{data.get('tool_name', 'unknown')}_{id(context)}"
        tool_name = data.get("tool_name", "unknown")

        self._pending_calls[call_id] = (tool_name, time.time())

        # No log entry for starts - just tracking
        return None

    def _handle_complete(self, context: ProbeContext, data: dict) -> Optional[List[LogEntry]]:
        """Calculate latency on tool completion."""
        call_id = data.get("call_id") or data.get("parent_event_id")

        if not call_id or call_id not in self._pending_calls:
            # Can't correlate - try tool name matching
            return None

        tool_name, start_time = self._pending_calls.pop(call_id)
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000

        # Update statistics
        if tool_name not in self._tool_stats:
            self._tool_stats[tool_name] = ToolLatencyStats(tool_name=tool_name)
        self._tool_stats[tool_name].record(latency_ms)

        # Add to history
        self._recent_latencies.append((end_time, tool_name, latency_ms))
        if len(self._recent_latencies) > self._max_history:
            self._recent_latencies.pop(0)

        # Check for anomalies
        entries = []
        is_slow = latency_ms > self.SLOW_THRESHOLD_MS
        avg = self._tool_stats[tool_name].avg_ms
        is_anomaly = avg > 0 and latency_ms > (avg * self.ANOMALY_MULTIPLIER)

        # Create latency event
        entry = LogEntry.create(
            event_type="tool_latency",
            event_data={
                "tool_name": tool_name,
                "latency_ms": round(latency_ms, 2),
                "avg_ms": round(avg, 2),
                "is_slow": is_slow,
                "is_anomaly": is_anomaly,
                "call_count": self._tool_stats[tool_name].call_count,
            },
            session_id=context.session_id,
            caused_by=call_id,
            tags=["latency", tool_name] + (["slow"] if is_slow else []) + (["anomaly"] if is_anomaly else []),
        )
        entries.append(entry)

        # Create alert if slow
        if is_slow:
            alert = LogEntry.create(
                event_type="reliability_alert",
                event_data={
                    "alert_type": "slow_tool",
                    "tool_name": tool_name,
                    "latency_ms": round(latency_ms, 2),
                    "threshold_ms": self.SLOW_THRESHOLD_MS,
                    "message": f"{tool_name} took {latency_ms:.0f}ms (threshold: {self.SLOW_THRESHOLD_MS}ms)",
                },
                session_id=context.session_id,
                caused_by=entry.event_id,
                tags=["alert", "latency", "slow_tool"],
            )
            entries.append(alert)

        return entries

    def get_stats(self) -> Dict[str, dict]:
        """Get latency statistics for all tools."""
        return {
            name: stats.to_dict()
            for name, stats in self._tool_stats.items()
        }

    def get_average_latency(self, tool_name: Optional[str] = None) -> float:
        """
        Get average latency.

        Args:
            tool_name: Specific tool or None for overall average

        Returns:
            Average latency in milliseconds
        """
        if tool_name and tool_name in self._tool_stats:
            return self._tool_stats[tool_name].avg_ms

        # Overall average
        total_ms = sum(s.total_ms for s in self._tool_stats.values())
        total_calls = sum(s.call_count for s in self._tool_stats.values())
        return total_ms / total_calls if total_calls > 0 else 0.0

    def get_slowest_tools(self, limit: int = 5) -> List[dict]:
        """Get tools ranked by average latency."""
        sorted_stats = sorted(
            self._tool_stats.values(),
            key=lambda s: s.avg_ms,
            reverse=True
        )
        return [s.to_dict() for s in sorted_stats[:limit]]

    def cleanup_stale(self, max_age_seconds: float = 300) -> int:
        """Remove stale pending calls older than max_age."""
        now = time.time()
        stale_ids = [
            call_id for call_id, (_, start_time) in self._pending_calls.items()
            if now - start_time > max_age_seconds
        ]
        for call_id in stale_ids:
            del self._pending_calls[call_id]
        return len(stale_ids)
