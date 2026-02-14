"""
Scope Expansion Probe

Detects when tasks grow beyond initial understanding - "this is more complicated than I thought" moments.
Tracks complexity surprises, unexpected dependencies, and scope creep.
"""

from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass
import re

from .base import FilteringProbe, ProbeContext, LogEntry


@dataclass
class ScopeSession:
    """Tracks task scope and expansions"""
    session_id: str
    initial_estimate: Optional[str] = None
    initial_time: Optional[datetime] = None
    expansions: List[Dict] = None
    files_accessed: int = 0
    tools_used: int = 0
    complexity_level: str = 'unknown'

    def __post_init__(self):
        if self.expansions is None:
            self.expansions = []


class ScopeExpansionProbe(FilteringProbe):
    """
    Tracks task scope expansion.

    Captures:
    - Initial complexity estimates
    - Unexpected dependency discoveries
    - Scope creep indicators
    - Complexity surprises
    - "More complicated than expected" moments

    Events observed:
    - thinking_block: Scope awareness and expansion signals
    - tool_call_start: Complexity indicators from tool usage
    """

    # Scope expansion signals
    EXPANSION_PATTERNS = {
        'more_complex': {
            'pattern': re.compile(
                r"\b(more (complex|complicated)|harder|trickier|turns out|actually)\b",
                re.I
            ),
            'severity': 'moderate',
            'type': 'complexity_increase'
        },
        'unexpected_dependency': {
            'pattern': re.compile(
                r"\b(also need|depends on|requires|first need to|before|prerequisite)\b",
                re.I
            ),
            'severity': 'moderate',
            'type': 'dependency_discovered'
        },
        'scope_creep': {
            'pattern': re.compile(
                r"\b(in addition|also|furthermore|additionally|as well|not just)\b",
                re.I
            ),
            'severity': 'low',
            'type': 'scope_addition'
        },
        'major_discovery': {
            'pattern': re.compile(
                r"\b(actually|wait|oh|realize|didn't know|wasn't aware|missed)\b",
                re.I
            ),
            'severity': 'high',
            'type': 'assumption_violated'
        }
    }

    # Initial estimate patterns
    ESTIMATE_PATTERNS = {
        'simple': re.compile(r"\b(simple|easy|straightforward|quick|trivial)\b", re.I),
        'moderate': re.compile(r"\b(moderate|medium|reasonable|standard)\b", re.I),
        'complex': re.compile(r"\b(complex|complicated|difficult|challenging|involved)\b", re.I)
    }

    # Complexity indicators from actions
    COMPLEXITY_THRESHOLDS = {
        'files_accessed': 5,  # More than 5 files suggests complexity
        'tools_used': 10,     # More than 10 tool calls suggests complexity
        'duration_minutes': 15  # More than 15 minutes suggests complexity
    }

    def __init__(self, enabled: bool = True):
        super().__init__(enabled)
        self._scope_sessions: Dict[str, ScopeSession] = {}

    def can_observe(self, event_type: str) -> bool:
        """Observe thinking and tool usage for scope signals"""
        return event_type in ['thinking_block', 'tool_call_start']

    def observe_filtered(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """Detect scope expansion"""
        session_id = context.session_id
        event_type = context.event_type

        # Initialize session tracking if needed
        if session_id not in self._scope_sessions:
            self._scope_sessions[session_id] = ScopeSession(session_id=session_id)

        session = self._scope_sessions[session_id]

        entries = []

        if event_type == 'thinking_block':
            content = context.event_data.get('content', '')

            # Check for initial estimate (if not already set)
            if not session.initial_estimate:
                estimate = self._detect_initial_estimate(content)
                if estimate:
                    session.initial_estimate = estimate
                    session.initial_time = context.timestamp
                    session.complexity_level = estimate

                    entry = LogEntry(
                        event_id=f"scope-estimate-{session_id}",
                        timestamp=context.timestamp,
                        event_type="scope_expansion",
                        event_data={
                            'phase': 'initial_estimate',
                            'estimated_complexity': estimate,
                            'statement': content[:200]
                        },
                        session_id=session_id,
                        tags=['scope', 'estimate', estimate]
                    )
                    entries.append(entry)

            # Check for expansion signals
            expansion_type, severity = self._detect_expansion(content)
            if expansion_type:
                expansion = {
                    'timestamp': context.timestamp,
                    'type': expansion_type,
                    'severity': severity,
                    'trigger': content[:200]
                }
                session.expansions.append(expansion)

                # Calculate expansion magnitude if we have initial estimate
                magnitude = 'unknown'
                if session.initial_estimate:
                    magnitude = self._calculate_magnitude(session)

                entry = LogEntry(
                    event_id=f"scope-expansion-{session_id}-{len(session.expansions)}",
                    timestamp=context.timestamp,
                    event_type="scope_expansion",
                    event_data={
                        'phase': 'expansion_detected',
                        'expansion_type': expansion_type,
                        'severity': severity,
                        'magnitude': magnitude,
                        'initial_estimate': session.initial_estimate,
                        'expansion_count': len(session.expansions),
                        'trigger': content[:200]
                    },
                    session_id=session_id,
                    tags=['scope', 'expansion', expansion_type, severity],
                    caused_by=f"scope-estimate-{session_id}" if session.initial_estimate else None
                )
                entries.append(entry)

        elif event_type == 'tool_call_start':
            # Track tool usage as complexity indicator
            session.tools_used += 1

            # Track file access
            tool_name = context.event_data.get('tool_name', '')
            if tool_name in ['Read', 'Write', 'Edit', 'Glob', 'Grep']:
                session.files_accessed += 1

            # Check if crossing complexity thresholds
            if (session.files_accessed == self.COMPLEXITY_THRESHOLDS['files_accessed'] or
                session.tools_used == self.COMPLEXITY_THRESHOLDS['tools_used']):

                # Implicit expansion through action count
                expansion = {
                    'timestamp': context.timestamp,
                    'type': 'action_complexity',
                    'severity': 'moderate',
                    'trigger': f"Tool usage threshold crossed: {session.tools_used} tools, {session.files_accessed} files"
                }
                session.expansions.append(expansion)

                entry = LogEntry(
                    event_id=f"scope-implicit-{session_id}-{len(session.expansions)}",
                    timestamp=context.timestamp,
                    event_type="scope_expansion",
                    event_data={
                        'phase': 'implicit_expansion',
                        'expansion_type': 'action_complexity',
                        'files_accessed': session.files_accessed,
                        'tools_used': session.tools_used,
                        'expansion_count': len(session.expansions)
                    },
                    session_id=session_id,
                    tags=['scope', 'expansion', 'implicit', 'actions']
                )
                entries.append(entry)

        return entries if entries else None

    def _detect_initial_estimate(self, content: str) -> Optional[str]:
        """Detect initial complexity estimate"""
        for level, pattern in self.ESTIMATE_PATTERNS.items():
            if pattern.search(content):
                return level
        return None

    def _detect_expansion(self, content: str) -> tuple[Optional[str], Optional[str]]:
        """Detect scope expansion signals"""
        for expansion_category, info in self.EXPANSION_PATTERNS.items():
            if info['pattern'].search(content):
                return info['type'], info['severity']
        return None, None

    def _calculate_magnitude(self, session: ScopeSession) -> str:
        """Calculate expansion magnitude"""
        if not session.initial_estimate or not session.expansions:
            return 'unknown'

        expansion_count = len(session.expansions)
        high_severity = sum(1 for e in session.expansions if e['severity'] == 'high')

        # Simple heuristic
        if high_severity >= 2 or expansion_count >= 5:
            return 'major'
        elif high_severity >= 1 or expansion_count >= 3:
            return 'moderate'
        elif expansion_count >= 1:
            return 'minor'

        return 'none'

    def get_scope_stats(self) -> Dict:
        """Get scope expansion statistics"""
        if not self._scope_sessions:
            return {
                'total_sessions': 0,
                'sessions_with_expansions': 0,
                'expansion_rate': 0.0,
                'avg_expansions_per_session': 0.0,
                'common_expansion_types': {}
            }

        total = len(self._scope_sessions)
        with_expansions = sum(1 for s in self._scope_sessions.values() if s.expansions)

        # Count total expansions
        all_expansions = []
        for session in self._scope_sessions.values():
            all_expansions.extend(session.expansions)

        avg_expansions = len(all_expansions) / total if total > 0 else 0.0

        # Count expansion types
        expansion_types = {}
        for expansion in all_expansions:
            exp_type = expansion['type']
            expansion_types[exp_type] = expansion_types.get(exp_type, 0) + 1

        return {
            'total_sessions': total,
            'sessions_with_expansions': with_expansions,
            'expansion_rate': with_expansions / total if total > 0 else 0.0,
            'avg_expansions_per_session': avg_expansions,
            'total_expansions': len(all_expansions),
            'common_expansion_types': expansion_types
        }
