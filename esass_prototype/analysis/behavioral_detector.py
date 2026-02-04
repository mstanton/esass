"""
Behavioral pattern detector for decision tendencies and tool preferences.

Identifies recurring behavioral patterns across sessions:
- Tool choice biases (preferred tools for given contexts)
- Decision confidence distributions (cautious vs. bold tendencies)
- Error recovery strategies (retry, pivot, escalate)
- Session workflow styles (exploration-first vs. execution-first)

Implements §5.1.4 of specification (simplified, stdlib-only).
"""

from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from esass_prototype.models import LogEntry, PatternDefinition, PatternType


class BehavioralPatternDetector:
    """
    Detect behavioral patterns: recurring tendencies in how tasks are approached.

    Unlike temporal patterns (event sequences) or semantic patterns (topic clusters),
    behavioral patterns capture *style* — e.g., "always checks status before commit",
    "high confidence in git decisions", "recovers from errors by retrying".
    """

    def __init__(
        self,
        min_support: int = 5,
        min_confidence: float = 0.6,
        min_stability_days: int = 3,
        min_sessions: int = 3,
        bias_threshold: float = 0.6,
    ):
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_stability_days = min_stability_days
        self.min_sessions = min_sessions
        self.bias_threshold = bias_threshold

    def detect_patterns(self, logs: List[LogEntry]) -> List[PatternDefinition]:
        """
        Find behavioral patterns in log data.

        Args:
            logs: List of log entries to analyze

        Returns:
            List of detected PatternDefinition objects
        """
        if not logs:
            return []

        sessions = self._group_by_session(logs)
        if len(sessions) < self.min_sessions:
            return []

        patterns = []

        # Detect different behavioral pattern types
        patterns.extend(self._detect_tool_preferences(logs, sessions))
        patterns.extend(self._detect_confidence_profiles(logs, sessions))
        patterns.extend(self._detect_error_recovery_styles(logs, sessions))
        patterns.extend(self._detect_workflow_styles(logs, sessions))

        # Sort by support
        patterns.sort(key=lambda p: p.support, reverse=True)
        return patterns

    # ── Tool preference detection ──────────────────────────────────────

    def _detect_tool_preferences(
        self,
        logs: List[LogEntry],
        sessions: Dict[str, List[LogEntry]],
    ) -> List[PatternDefinition]:
        """Detect consistent tool choice preferences across sessions."""
        patterns = []

        # Count tool usage across sessions
        session_tool_counts = {}
        for sid, entries in sessions.items():
            tools = Counter()
            for e in entries:
                if e.event_type == 'tool_usage':
                    tool_name = e.event_data.get('tool_name', 'unknown')
                    tools[tool_name] += 1
            if tools:
                session_tool_counts[sid] = tools

        if not session_tool_counts:
            return patterns

        # Find tools that appear in a high fraction of sessions
        all_tools = Counter()
        for tools in session_tool_counts.values():
            for tool, count in tools.items():
                all_tools[tool] += count

        total_sessions = len(session_tool_counts)

        for tool, total_count in all_tools.items():
            sessions_with_tool = sum(
                1 for tc in session_tool_counts.values() if tool in tc
            )
            session_ratio = sessions_with_tool / total_sessions

            if session_ratio >= self.bias_threshold and total_count >= self.min_support:
                pattern = self._build_tool_preference_pattern(
                    tool, total_count, sessions_with_tool, total_sessions,
                    logs, sessions,
                )
                if pattern:
                    patterns.append(pattern)

        return patterns

    def _build_tool_preference_pattern(
        self,
        tool_name: str,
        total_count: int,
        sessions_with_tool: int,
        total_sessions: int,
        logs: List[LogEntry],
        sessions: Dict[str, List[LogEntry]],
    ) -> Optional[PatternDefinition]:
        """Build a PatternDefinition for a tool preference."""
        confidence = sessions_with_tool / total_sessions

        # Get exemplar entries
        exemplars = []
        for e in logs:
            if (e.event_type == 'tool_usage'
                    and e.event_data.get('tool_name') == tool_name):
                exemplars.append(e)
                if len(exemplars) >= 5:
                    break

        stability_days = self._calculate_stability(exemplars)

        skill_candidate = (
            total_count >= self.min_support
            and confidence >= self.min_confidence
            and stability_days >= self.min_stability_days
        )

        first_seen, last_seen = self._get_date_range(exemplars)

        return PatternDefinition(
            pattern_type=PatternType.BEHAVIORAL.value,
            support=total_count,
            confidence=round(confidence, 4),
            stability_days=stability_days,
            description=(
                f"Tool preference: {tool_name} used in "
                f"{sessions_with_tool}/{total_sessions} sessions "
                f"({total_count} total uses)"
            ),
            sequence=[f"tool_usage:{tool_name}"],
            exemplar_ids=[e.event_id for e in exemplars[:5]],
            skill_candidate=skill_candidate,
            tags=['behavioral', 'tool_preference', tool_name],
            first_seen=first_seen,
            last_seen=last_seen,
        )

    # ── Confidence profile detection ───────────────────────────────────

    def _detect_confidence_profiles(
        self,
        logs: List[LogEntry],
        sessions: Dict[str, List[LogEntry]],
    ) -> List[PatternDefinition]:
        """Detect consistent confidence tendencies (cautious vs. bold)."""
        patterns = []

        # Collect confidence values per event type across sessions
        type_confidences = defaultdict(list)
        type_entries = defaultdict(list)

        for entry in logs:
            conf = entry.event_data.get('confidence')
            if conf is not None and isinstance(conf, (int, float)):
                type_confidences[entry.event_type].append(float(conf))
                type_entries[entry.event_type].append(entry)

        for event_type, confidences in type_confidences.items():
            if len(confidences) < self.min_support:
                continue

            mean_conf = sum(confidences) / len(confidences)
            entries = type_entries[event_type]

            # Detect "consistently high confidence" or "consistently low confidence"
            if mean_conf >= 0.7:
                profile = "high_confidence"
                description = (
                    f"High confidence tendency in {event_type} events "
                    f"(mean={mean_conf:.2f}, n={len(confidences)})"
                )
            elif mean_conf <= 0.4:
                profile = "low_confidence"
                description = (
                    f"Cautious/exploratory tendency in {event_type} events "
                    f"(mean={mean_conf:.2f}, n={len(confidences)})"
                )
            else:
                # Moderate confidence — check variance
                variance = sum((c - mean_conf) ** 2 for c in confidences) / len(confidences)
                if variance < 0.03:
                    profile = "stable_confidence"
                    description = (
                        f"Stable confidence in {event_type} events "
                        f"(mean={mean_conf:.2f}, var={variance:.3f}, n={len(confidences)})"
                    )
                else:
                    continue  # Too variable, not a clear pattern

            # Calculate cross-session presence
            session_ids = set(e.session_id for e in entries)
            session_ratio = len(session_ids) / len(sessions)

            if session_ratio < self.bias_threshold:
                continue

            stability_days = self._calculate_stability(entries)
            first_seen, last_seen = self._get_date_range(entries)

            skill_candidate = (
                len(confidences) >= self.min_support
                and session_ratio >= self.min_confidence
                and stability_days >= self.min_stability_days
            )

            patterns.append(PatternDefinition(
                pattern_type=PatternType.BEHAVIORAL.value,
                support=len(confidences),
                confidence=round(session_ratio, 4),
                stability_days=stability_days,
                description=description,
                sequence=[f"{event_type}:confidence_{profile}"],
                exemplar_ids=[e.event_id for e in entries[:5]],
                skill_candidate=skill_candidate,
                tags=['behavioral', 'confidence_profile', profile, event_type],
                first_seen=first_seen,
                last_seen=last_seen,
            ))

        return patterns

    # ── Error recovery style detection ─────────────────────────────────

    def _detect_error_recovery_styles(
        self,
        logs: List[LogEntry],
        sessions: Dict[str, List[LogEntry]],
    ) -> List[PatternDefinition]:
        """Detect patterns in how errors are recovered from."""
        patterns = []

        # For each session, find error events and what follows
        recovery_strategies = Counter()
        recovery_entries = defaultdict(list)

        for sid, entries in sessions.items():
            sorted_entries = sorted(entries, key=lambda e: e.timestamp)
            for i, entry in enumerate(sorted_entries):
                if entry.event_type in ('error', 'error_recovery'):
                    # What happens next?
                    if i + 1 < len(sorted_entries):
                        next_entry = sorted_entries[i + 1]
                        strategy = self._classify_recovery(entry, next_entry)
                        recovery_strategies[strategy] += 1
                        recovery_entries[strategy].append(entry)

        for strategy, count in recovery_strategies.items():
            if count < self.min_support:
                continue

            entries = recovery_entries[strategy]
            session_ids = set(e.session_id for e in entries)
            # Confidence: what fraction of error recoveries use this strategy
            total_recoveries = sum(recovery_strategies.values())
            confidence = count / total_recoveries if total_recoveries > 0 else 0

            if confidence < self.min_confidence:
                continue

            stability_days = self._calculate_stability(entries)
            first_seen, last_seen = self._get_date_range(entries)

            skill_candidate = (
                count >= self.min_support
                and confidence >= self.min_confidence
                and stability_days >= self.min_stability_days
            )

            patterns.append(PatternDefinition(
                pattern_type=PatternType.BEHAVIORAL.value,
                support=count,
                confidence=round(confidence, 4),
                stability_days=stability_days,
                description=(
                    f"Error recovery style: {strategy} "
                    f"({count}/{total_recoveries} recoveries, "
                    f"{len(session_ids)} sessions)"
                ),
                sequence=[f"error:{strategy}"],
                exemplar_ids=[e.event_id for e in entries[:5]],
                skill_candidate=skill_candidate,
                tags=['behavioral', 'error_recovery', strategy],
                first_seen=first_seen,
                last_seen=last_seen,
            ))

        return patterns

    def _classify_recovery(self, error_entry: LogEntry, next_entry: LogEntry) -> str:
        """Classify the recovery strategy based on what follows an error."""
        next_type = next_entry.event_type

        if next_type == 'tool_usage':
            # Check if same tool was retried
            error_tool = error_entry.event_data.get('tool_name', '')
            next_tool = next_entry.event_data.get('tool_name', '')
            if error_tool and error_tool == next_tool:
                return 'retry_same_tool'
            return 'pivot_to_different_tool'
        elif next_type == 'reasoning':
            return 'analyze_then_act'
        elif next_type == 'decision':
            return 'immediate_decision'
        elif next_type == 'strategy_shift':
            return 'strategy_change'
        else:
            return 'other'

    # ── Workflow style detection ────────────────────────────────────────

    def _detect_workflow_styles(
        self,
        logs: List[LogEntry],
        sessions: Dict[str, List[LogEntry]],
    ) -> List[PatternDefinition]:
        """Detect consistent session workflow styles."""
        patterns = []

        # Classify each session's opening pattern
        opening_styles = Counter()
        style_entries = defaultdict(list)

        for sid, entries in sessions.items():
            sorted_entries = sorted(entries, key=lambda e: e.timestamp)
            if len(sorted_entries) < 2:
                continue

            # Classify by first 3 event types
            opening = tuple(e.event_type for e in sorted_entries[:3])
            style = self._classify_workflow_style(opening)
            opening_styles[style] += 1
            style_entries[style].extend(sorted_entries[:3])

        total_sessions = len(sessions)
        for style, count in opening_styles.items():
            if count < self.min_support:
                continue

            confidence = count / total_sessions
            if confidence < self.min_confidence:
                continue

            entries = style_entries[style]
            stability_days = self._calculate_stability(entries)
            first_seen, last_seen = self._get_date_range(entries)

            skill_candidate = (
                count >= self.min_support
                and confidence >= self.min_confidence
                and stability_days >= self.min_stability_days
            )

            patterns.append(PatternDefinition(
                pattern_type=PatternType.BEHAVIORAL.value,
                support=count,
                confidence=round(confidence, 4),
                stability_days=stability_days,
                description=(
                    f"Workflow style: {style} "
                    f"({count}/{total_sessions} sessions)"
                ),
                sequence=[f"workflow:{style}"],
                exemplar_ids=[e.event_id for e in entries[:5]],
                skill_candidate=skill_candidate,
                tags=['behavioral', 'workflow_style', style],
                first_seen=first_seen,
                last_seen=last_seen,
            ))

        return patterns

    def _classify_workflow_style(self, opening: Tuple[str, ...]) -> str:
        """Classify a session opening sequence into a workflow style."""
        if not opening:
            return 'empty'

        first = opening[0]

        if first == 'reasoning':
            if len(opening) > 1 and opening[1] == 'reasoning':
                return 'deep_analysis_first'
            return 'analyze_first'
        elif first == 'tool_usage':
            return 'execution_first'
        elif first == 'decision':
            return 'decide_first'
        elif first == 'error':
            return 'error_driven'
        else:
            return 'other'

    # ── Shared helpers ─────────────────────────────────────────────────

    def _group_by_session(self, logs: List[LogEntry]) -> Dict[str, List[LogEntry]]:
        """Group log entries by session_id."""
        sessions = defaultdict(list)
        for entry in logs:
            if entry.session_id:
                sessions[entry.session_id].append(entry)
        return dict(sessions)

    def _calculate_stability(self, entries: List[LogEntry]) -> int:
        """Calculate span in days from first to last entry."""
        dates = set()
        for e in entries:
            try:
                dates.add(datetime.fromisoformat(e.timestamp).date())
            except (ValueError, TypeError):
                pass
        if len(dates) < 1:
            return 0
        return (max(dates) - min(dates)).days + 1

    def _get_date_range(self, entries: List[LogEntry]) -> Tuple[str, str]:
        """Get first and last seen timestamps."""
        if not entries:
            now = datetime.utcnow().isoformat()
            return now, now
        timestamps = sorted(e.timestamp for e in entries)
        return timestamps[0], timestamps[-1]
