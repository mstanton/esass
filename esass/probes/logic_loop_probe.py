"""
Logic Loop Detection Probe

Detects semantic anomalies where an agent repeatedly performs the same action
with no variation, indicating a potential logic loop. (ENHANCEMENT.md Phase 2.2)
"""

import hashlib
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from esass.probes.base import FilteringProbe, ProbeContext, LogEntry


@dataclass
class ActionSignature:
    """Represents a unique action for loop detection."""
    tool_name: str
    target: str  # File path, command, or other target
    action_hash: str  # Hash of parameters for comparison

    @classmethod
    def from_event(cls, tool_name: str, parameters: dict) -> "ActionSignature":
        """Create signature from tool call data."""
        # Extract meaningful target
        target = ""
        if "file_path" in parameters:
            target = parameters["file_path"]
        elif "command" in parameters:
            target = parameters["command"]
        elif "pattern" in parameters:
            target = parameters["pattern"]
        elif "url" in parameters:
            target = parameters["url"]

        # Create hash of full parameters
        param_str = str(sorted(parameters.items()))
        action_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]

        return cls(tool_name=tool_name, target=target, action_hash=action_hash)

    def __hash__(self):
        return hash((self.tool_name, self.target, self.action_hash))

    def __eq__(self, other):
        if not isinstance(other, ActionSignature):
            return False
        return (self.tool_name == other.tool_name and
                self.target == other.target and
                self.action_hash == other.action_hash)


class LogicLoopProbe(FilteringProbe):
    """
    Detects self-correction loops and repetitive agent behavior.

    Loop Types:
    - EXACT_REPEAT: Same tool + parameters repeated >N times
    - TOGGLE_LOOP: Alternating between two states (edit/undo pattern)
    - FAILURE_LOOP: Same failing command repeated without modification
    - OSCILLATION: Cycling between N states repeatedly

    Triggers LOGIC_LOOP reliability alert when detected.
    """

    # Detection thresholds
    EXACT_REPEAT_THRESHOLD = 3  # Same action 3+ times
    TOGGLE_THRESHOLD = 4  # A-B-A-B pattern 4+ times
    FAILURE_THRESHOLD = 2  # Same failing action 2+ times
    WINDOW_SIZE = 20  # Actions to consider for pattern detection

    def __init__(self, enabled: bool = True, **kwargs):
        super().__init__(enabled=enabled, **kwargs)

        # Recent action history per session
        self._action_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.WINDOW_SIZE)
        )

        # Track failures per signature
        self._failure_counts: Dict[str, Dict[ActionSignature, int]] = defaultdict(
            lambda: defaultdict(int)
        )

        # Active loops (to avoid duplicate alerts)
        self._active_loops: Dict[str, set] = defaultdict(set)

    def can_observe(self, event_type: str) -> bool:
        return event_type in ["tool_call_start", "tool_call_complete", "error"]

    def observe_filtered(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        event_type = context.event_type
        data = context.event_data
        session_id = context.session_id

        entries = []

        if event_type == "tool_call_start":
            tool_name = data.get("tool_name", "")
            parameters = data.get("parameters", {})

            if tool_name and parameters:
                signature = ActionSignature.from_event(tool_name, parameters)
                self._action_history[session_id].append(signature)

                # Check for loops
                loop_result = self._detect_loop(session_id, signature)
                if loop_result:
                    loop_type, details = loop_result
                    entries.extend(self._create_alert(context, loop_type, details, signature))

        elif event_type == "error" or (event_type == "tool_call_complete" and not data.get("success", True)):
            # Track failures
            tool_name = data.get("tool_name", "")
            parameters = data.get("parameters", {})

            if tool_name:
                signature = ActionSignature.from_event(tool_name, parameters)
                self._failure_counts[session_id][signature] += 1

                # Check for failure loop
                if self._failure_counts[session_id][signature] >= self.FAILURE_THRESHOLD:
                    loop_key = f"failure:{signature.action_hash}"
                    if loop_key not in self._active_loops[session_id]:
                        self._active_loops[session_id].add(loop_key)
                        entries.extend(self._create_alert(
                            context, "FAILURE_LOOP",
                            {"repeat_count": self._failure_counts[session_id][signature]},
                            signature
                        ))

        return entries if entries else None

    def _detect_loop(self, session_id: str, current: ActionSignature) -> Optional[Tuple[str, dict]]:
        """
        Detect loop patterns in action history.

        Returns:
            Tuple of (loop_type, details) or None
        """
        history = list(self._action_history[session_id])
        if len(history) < 3:
            return None

        # Check for exact repeats
        repeat_count = 0
        for action in reversed(history):
            if action == current:
                repeat_count += 1
            else:
                break

        if repeat_count >= self.EXACT_REPEAT_THRESHOLD:
            loop_key = f"exact:{current.action_hash}"
            if loop_key not in self._active_loops[session_id]:
                self._active_loops[session_id].add(loop_key)
                return ("EXACT_REPEAT", {"repeat_count": repeat_count})

        # Check for toggle pattern (A-B-A-B)
        if len(history) >= 4:
            toggle_result = self._detect_toggle(history)
            if toggle_result:
                loop_key = f"toggle:{toggle_result['pattern_hash']}"
                if loop_key not in self._active_loops[session_id]:
                    self._active_loops[session_id].add(loop_key)
                    return ("TOGGLE_LOOP", toggle_result)

        # Check for oscillation (A-B-C-A-B-C)
        if len(history) >= 6:
            oscillation_result = self._detect_oscillation(history)
            if oscillation_result:
                loop_key = f"oscillate:{oscillation_result['pattern_hash']}"
                if loop_key not in self._active_loops[session_id]:
                    self._active_loops[session_id].add(loop_key)
                    return ("OSCILLATION", oscillation_result)

        return None

    def _detect_toggle(self, history: list) -> Optional[dict]:
        """Detect A-B-A-B toggle pattern."""
        if len(history) < 4:
            return None

        # Check last 4+ elements for toggle
        recent = history[-8:]  # Look at up to 8 recent actions

        # Need at least 2 distinct actions
        unique = list(set(recent[-4:]))
        if len(unique) != 2:
            return None

        # Check for alternating pattern
        a, b = unique
        toggle_count = 0
        expected = recent[-1]

        for action in reversed(recent):
            if action == expected:
                toggle_count += 1
                expected = b if expected == a else a
            else:
                break

        if toggle_count >= self.TOGGLE_THRESHOLD:
            return {
                "toggle_count": toggle_count,
                "action_a": f"{a.tool_name}:{a.target[:30]}",
                "action_b": f"{b.tool_name}:{b.target[:30]}",
                "pattern_hash": hashlib.md5(f"{a.action_hash}{b.action_hash}".encode()).hexdigest()[:8],
            }

        return None

    def _detect_oscillation(self, history: list) -> Optional[dict]:
        """Detect cyclic patterns (A-B-C-A-B-C)."""
        if len(history) < 6:
            return None

        # Try pattern lengths 3-5
        for pattern_len in range(3, 6):
            if len(history) < pattern_len * 2:
                continue

            pattern = history[-pattern_len:]
            cycle_count = 1

            # Check how many times pattern repeats
            for i in range(2, len(history) // pattern_len + 1):
                start = -(i * pattern_len)
                end = start + pattern_len
                if end == 0:
                    end = None
                segment = history[start:end]

                if len(segment) == pattern_len and all(
                    segment[j] == pattern[j] for j in range(pattern_len)
                ):
                    cycle_count += 1
                else:
                    break

            if cycle_count >= 2:
                pattern_desc = " -> ".join(f"{a.tool_name}" for a in pattern)
                pattern_hash = hashlib.md5(
                    "".join(a.action_hash for a in pattern).encode()
                ).hexdigest()[:8]

                return {
                    "cycle_count": cycle_count,
                    "pattern_length": pattern_len,
                    "pattern": pattern_desc,
                    "pattern_hash": pattern_hash,
                }

        return None

    def _create_alert(self, context: ProbeContext, loop_type: str,
                     details: dict, signature: ActionSignature) -> List[LogEntry]:
        """Create alert entries for detected loop."""
        entries = []

        # Observation entry
        obs_entry = LogEntry.create(
            event_type="logic_loop_detected",
            event_data={
                "loop_type": loop_type,
                "tool_name": signature.tool_name,
                "target": signature.target[:100],
                "action_hash": signature.action_hash,
                **details,
            },
            session_id=context.session_id,
            tags=["logic_loop", loop_type.lower(), signature.tool_name],
        )
        entries.append(obs_entry)

        # Alert entry
        message = self._format_alert_message(loop_type, signature, details)
        alert_entry = LogEntry.create(
            event_type="reliability_alert",
            event_data={
                "alert_type": "LOGIC_LOOP",
                "loop_type": loop_type,
                "severity": "warning",
                "message": message,
                "tool_name": signature.tool_name,
                "target": signature.target[:100],
                **details,
            },
            session_id=context.session_id,
            caused_by=obs_entry.event_id,
            tags=["alert", "logic_loop", loop_type.lower()],
        )
        entries.append(alert_entry)

        return entries

    def _format_alert_message(self, loop_type: str, signature: ActionSignature,
                             details: dict) -> str:
        """Format human-readable alert message."""
        if loop_type == "EXACT_REPEAT":
            return (f"Repeated {signature.tool_name} {details['repeat_count']}x "
                   f"on '{signature.target[:40]}' with identical parameters")

        if loop_type == "TOGGLE_LOOP":
            return (f"Toggle loop detected: alternating between "
                   f"{details['action_a']} and {details['action_b']} "
                   f"({details['toggle_count']} toggles)")

        if loop_type == "FAILURE_LOOP":
            return (f"Failure loop: {signature.tool_name} failing repeatedly "
                   f"({details['repeat_count']}x) on '{signature.target[:40]}'")

        if loop_type == "OSCILLATION":
            return (f"Oscillation detected: {details['pattern']} "
                   f"repeating {details['cycle_count']}x")

        return f"Logic loop detected: {loop_type}"

    def reset_session(self, session_id: str) -> None:
        """Clear tracking state for a session."""
        if session_id in self._action_history:
            del self._action_history[session_id]
        if session_id in self._failure_counts:
            del self._failure_counts[session_id]
        if session_id in self._active_loops:
            del self._active_loops[session_id]

    def get_session_stats(self, session_id: str) -> dict:
        """Get loop detection stats for a session."""
        return {
            "history_length": len(self._action_history.get(session_id, [])),
            "failure_count": sum(self._failure_counts.get(session_id, {}).values()),
            "active_loops": len(self._active_loops.get(session_id, set())),
        }
