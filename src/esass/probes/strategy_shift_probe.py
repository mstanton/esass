"""
Strategy Shift Probe

Captures when Claude abandons one approach for another - high-value learning moments.
Tracks pivot points, sunk costs, and outcome comparisons.
"""

from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass
import re

from .base import FilteringProbe, ProbeContext, LogEntry


@dataclass
class StrategySession:
    """Tracks a strategic approach and potential shifts"""
    strategy_id: str
    start_time: datetime
    approach_type: str
    description: str
    actions_taken: int = 0
    shifted: bool = False
    shift_time: Optional[datetime] = None
    shift_trigger: Optional[str] = None
    new_approach: Optional[str] = None


class StrategyShiftProbe(FilteringProbe):
    """
    Tracks strategic pivots and approach changes.

    Captures:
    - Initial strategy articulation
    - Trigger for strategy shift
    - Sunk cost at shift point
    - New strategy adopted
    - Outcome comparison

    Events observed:
    - thinking_block: Strategy articulation and shift reasoning
    - plan_mode_entered: Planning shifts
    - tool_selected: Approach execution changes
    """

    # Strategy shift indicators in thinking
    SHIFT_PATTERNS = {
        'not_working': re.compile(r"\b(this (isn't|is not|won't) work|not working|doesn't work|failed)", re.I),
        'try_different': re.compile(r"\b(try (a )?different|try (an)?other|instead|alternatively)", re.I),
        'pivot': re.compile(r"\b(pivot|switch|change approach|change strategy|shift)", re.I),
        'abandon': re.compile(r"\b(abandon|give up on|scrap|drop|forget)", re.I),
        'simpler': re.compile(r"\b(simpler|easier|more straightforward|pragmatic|quick)", re.I),
        'more_robust': re.compile(r"\b(more robust|better|more elegant|cleaner)", re.I),
        'backtrack': re.compile(r"\b(back ?track|go back|start over|restart)", re.I)
    }

    # Approach type patterns
    APPROACH_PATTERNS = {
        'incremental': re.compile(r"\b(incremental|step.by.step|one at a time|gradual)", re.I),
        'batch': re.compile(r"\b(batch|all at once|bulk|mass)", re.I),
        'exploratory': re.compile(r"\b(explore|investigate|search|look for)", re.I),
        'targeted': re.compile(r"\b(target|specific|direct|focused)", re.I),
        'elegant': re.compile(r"\b(elegant|clean|beautiful|optimal)", re.I),
        'pragmatic': re.compile(r"\b(pragmatic|practical|quick|simple|works)", re.I),
        'defensive': re.compile(r"\b(defensive|safe|cautious|careful)", re.I),
        'aggressive': re.compile(r"\b(aggressive|bold|risky)", re.I)
    }

    def __init__(self, enabled: bool = True, max_strategy_duration_seconds: int = 600):
        super().__init__(enabled)
        self.max_strategy_duration_seconds = max_strategy_duration_seconds
        self._current_strategy: Optional[StrategySession] = None
        self._strategy_history: List[StrategySession] = []

    def can_observe(self, event_type: str) -> bool:
        """Observe strategy-related events"""
        return event_type in [
            'thinking_block',
            'plan_mode_entered',
            'tool_selected',
            'approach_selected'
        ]

    def observe_filtered(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """Track strategy shifts"""
        event_type = context.event_type
        data = context.event_data

        entries = []

        # Detect strategy articulation
        if event_type == 'thinking_block':
            content = data.get('content', '')

            # Check for new strategy
            approach = self._detect_approach(content)
            if approach and not self._current_strategy:
                # New strategy started
                self._start_new_strategy(approach, content, context.timestamp, context.session_id)
                entry = self._create_strategy_start_entry(context)
                if entry:
                    entries.append(entry)

            # Check for strategy shift
            elif self._current_strategy:
                shift_trigger = self._detect_shift_trigger(content)
                if shift_trigger:
                    # Strategy shift detected
                    new_approach = self._detect_approach(content)
                    shift_entry = self._record_shift(
                        shift_trigger,
                        new_approach,
                        content,
                        context
                    )
                    if shift_entry:
                        entries.append(shift_entry)

        # Track approach selection
        elif event_type == 'approach_selected':
            approach = data.get('approach', '')
            if approach:
                self._start_new_strategy(approach, approach, context.timestamp, context.session_id)
                entry = self._create_strategy_start_entry(context)
                if entry:
                    entries.append(entry)

        # Track plan mode as potential strategy shift
        elif event_type == 'plan_mode_entered':
            if self._current_strategy:
                # Entering plan mode mid-execution suggests pivot
                shift_entry = self._record_shift(
                    'plan_mode_entry',
                    'planning',
                    'Entered plan mode to reconsider approach',
                    context
                )
                if shift_entry:
                    entries.append(shift_entry)

        # Track action counts
        if self._current_strategy and event_type in ['tool_selected', 'thinking_block']:
            self._current_strategy.actions_taken += 1

        return entries if entries else None

    def _start_new_strategy(self, approach: str, description: str, timestamp: datetime, session_id: str):
        """Start tracking a new strategy"""
        # End current strategy if exists
        if self._current_strategy and not self._current_strategy.shifted:
            self._strategy_history.append(self._current_strategy)

        # Start new strategy
        strategy_id = f"strategy-{session_id}-{timestamp.timestamp()}"
        self._current_strategy = StrategySession(
            strategy_id=strategy_id,
            start_time=timestamp,
            approach_type=approach,
            description=description[:200]  # Limit description length
        )

    def _create_strategy_start_entry(self, context: ProbeContext) -> Optional[LogEntry]:
        """Create log entry for strategy start"""
        if not self._current_strategy:
            return None

        return LogEntry(
            event_id=f"{self._current_strategy.strategy_id}-start",
            timestamp=context.timestamp,
            event_type="strategy_shift",
            event_data={
                'strategy_id': self._current_strategy.strategy_id,
                'approach': self._current_strategy.approach_type,
                'description': self._current_strategy.description,
                'phase': 'strategy_start'
            },
            session_id=context.session_id,
            tags=['strategy', 'start', self._current_strategy.approach_type]
        )

    def _record_shift(
        self,
        trigger: str,
        new_approach: Optional[str],
        description: str,
        context: ProbeContext
    ) -> Optional[LogEntry]:
        """Record a strategy shift"""
        if not self._current_strategy:
            return None

        # Calculate sunk cost
        duration = (context.timestamp - self._current_strategy.start_time).total_seconds()
        sunk_actions = self._current_strategy.actions_taken

        # Mark current strategy as shifted
        self._current_strategy.shifted = True
        self._current_strategy.shift_time = context.timestamp
        self._current_strategy.shift_trigger = trigger
        self._current_strategy.new_approach = new_approach

        # Create shift entry
        entry = LogEntry(
            event_id=f"{self._current_strategy.strategy_id}-shift",
            timestamp=context.timestamp,
            event_type="strategy_shift",
            event_data={
                'strategy_id': self._current_strategy.strategy_id,
                'old_approach': self._current_strategy.approach_type,
                'new_approach': new_approach or 'unspecified',
                'shift_trigger': trigger,
                'phase': 'strategy_shift',
                'sunk_cost': {
                    'duration_seconds': duration,
                    'actions_taken': sunk_actions
                },
                'reason': description[:200]
            },
            session_id=context.session_id,
            tags=['strategy', 'shift', trigger, self._current_strategy.approach_type],
            caused_by=f"{self._current_strategy.strategy_id}-start"
        )

        # Move to history
        self._strategy_history.append(self._current_strategy)

        # Start new strategy if specified
        if new_approach:
            self._start_new_strategy(new_approach, description, context.timestamp, context.session_id)

        return entry

    def _detect_approach(self, content: str) -> Optional[str]:
        """Detect approach type from content"""
        for approach, pattern in self.APPROACH_PATTERNS.items():
            if pattern.search(content):
                return approach
        return None

    def _detect_shift_trigger(self, content: str) -> Optional[str]:
        """Detect shift trigger from content"""
        for trigger, pattern in self.SHIFT_PATTERNS.items():
            if pattern.search(content):
                return trigger
        return None

    def get_shift_stats(self) -> Dict:
        """Get strategy shift statistics"""
        if not self._strategy_history:
            return {
                'total_strategies': 0,
                'shifts': 0,
                'shift_rate': 0.0,
                'avg_duration_before_shift': 0.0,
                'common_triggers': {},
                'approach_transitions': {}
            }

        total = len(self._strategy_history)
        shifts = sum(1 for s in self._strategy_history if s.shifted)

        # Average duration before shift
        shift_durations = [
            (s.shift_time - s.start_time).total_seconds()
            for s in self._strategy_history
            if s.shifted and s.shift_time
        ]
        avg_duration = sum(shift_durations) / len(shift_durations) if shift_durations else 0.0

        # Trigger frequency
        triggers = {}
        for session in self._strategy_history:
            if session.shift_trigger:
                triggers[session.shift_trigger] = triggers.get(session.shift_trigger, 0) + 1

        # Approach transitions
        transitions = {}
        for session in self._strategy_history:
            if session.shifted and session.new_approach:
                transition_key = f"{session.approach_type} → {session.new_approach}"
                transitions[transition_key] = transitions.get(transition_key, 0) + 1

        return {
            'total_strategies': total,
            'shifts': shifts,
            'shift_rate': shifts / total if total > 0 else 0.0,
            'avg_duration_before_shift': avg_duration,
            'common_triggers': triggers,
            'approach_transitions': transitions
        }
