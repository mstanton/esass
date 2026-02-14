"""
Decision point observation probe.

Captures explicit decision-making events and rationale.
"""

from typing import List, Optional

from esass.probes.base import FilteringProbe, ProbeContext
from esass.models import LogEntry, create_decision_event


class DecisionProbe(FilteringProbe):
    """
    Observes decision points in Claude's execution.

    Captures:
    - Tool selection decisions
    - Plan mode entry decisions
    - Approach selection (multiple valid paths)
    - User question decisions
    """

    def __init__(self, enabled: bool = True,
                 min_options: int = 1):
        """
        Initialize decision probe.

        Args:
            enabled: Whether probe is active
            min_options: Minimum number of options to qualify as decision
        """
        super().__init__(enabled)
        self.min_options = min_options

    def can_observe(self, event_type: str) -> bool:
        """Handle decision-related events"""
        return event_type in [
            'tool_selected',
            'approach_selected',
            'plan_mode_decision',
            'user_question_decision',
            'decision_made'
        ]

    def observe_filtered(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """Process decision events"""
        event_type = context.event_type

        if event_type == 'tool_selected':
            return self._on_tool_selected(context)
        elif event_type == 'approach_selected':
            return self._on_approach_selected(context)
        elif event_type == 'plan_mode_decision':
            return self._on_plan_mode_decision(context)
        elif event_type == 'user_question_decision':
            return self._on_user_question_decision(context)
        elif event_type == 'decision_made':
            return self._on_generic_decision(context)

        return None

    def _on_tool_selected(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """
        Handle tool selection decision.

        Example: Choosing Read vs Glob for file search
        """
        selected = context.event_data.get('selected_tool')
        alternatives = context.event_data.get('alternatives', [])
        rationale = context.event_data.get('rationale', '')

        if not selected:
            return None

        # Filter based on number of options
        if len(alternatives) < self.min_options:
            return None

        # Estimate confidence from rationale
        confidence = self._estimate_decision_confidence(rationale)

        entry = create_decision_event(
            decision=f'use_{selected}',
            confidence=confidence,
            options_considered=alternatives,
            rationale=rationale or f'Selected {selected} over alternatives',
            session_id=context.session_id or 'unknown',
            caused_by=context.current_parent,
            tags=['tool_selection', 'decision', selected.lower()]
        )

        return [entry]

    def _on_approach_selected(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """
        Handle approach/strategy selection.

        Example: Choosing incremental vs batch processing
        """
        selected = context.event_data.get('approach')
        alternatives = context.event_data.get('alternatives', [])
        rationale = context.event_data.get('rationale', '')
        context_info = context.event_data.get('context', {})

        if not selected:
            return None

        confidence = self._estimate_decision_confidence(rationale)

        # Extract task context
        task = context_info.get('task', 'unknown')

        entry = create_decision_event(
            decision=f'approach:{selected}',
            confidence=confidence,
            options_considered=alternatives,
            rationale=rationale or f'Selected {selected} approach',
            session_id=context.session_id or 'unknown',
            caused_by=context.current_parent,
            tags=['approach_selection', 'strategy', task]
        )

        return [entry]

    def _on_plan_mode_decision(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """
        Handle decision to enter/skip plan mode.

        This is a critical decision point showing task complexity assessment.
        """
        decision = context.event_data.get('decision')  # 'enter' or 'skip'
        rationale = context.event_data.get('rationale', '')
        task_complexity = context.event_data.get('task_complexity', 'unknown')

        if not decision:
            return None

        # Plan mode decisions are high-value
        confidence = 0.8  # These are typically deliberate

        entry = create_decision_event(
            decision=f'plan_mode_{decision}',
            confidence=confidence,
            options_considered=['enter_plan_mode', 'proceed_directly'],
            rationale=rationale or f'Task complexity: {task_complexity}',
            session_id=context.session_id or 'unknown',
            caused_by=context.current_parent,
            tags=['plan_mode', 'complexity_assessment', decision]
        )

        return [entry]

    def _on_user_question_decision(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """
        Handle decision to ask user for clarification.

        Indicates uncertainty or multiple valid paths.
        """
        question = context.event_data.get('question', '')
        options = context.event_data.get('options', [])
        trigger = context.event_data.get('trigger', 'uncertainty')

        if not question:
            return None

        entry = create_decision_event(
            decision='ask_user_question',
            confidence=0.0,  # Low confidence triggered the question
            options_considered=options,
            rationale=f'Triggered by: {trigger}. Question: {question[:100]}',
            session_id=context.session_id or 'unknown',
            caused_by=context.current_parent,
            tags=['user_question', 'uncertainty', trigger]
        )

        return [entry]

    def _on_generic_decision(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """
        Handle generic decision event.

        Used when decision type doesn't fit other categories.
        """
        decision = context.event_data.get('decision', '')
        options = context.event_data.get('options', [])
        rationale = context.event_data.get('rationale', '')
        confidence = context.event_data.get('confidence', 0.5)

        if not decision:
            return None

        entry = create_decision_event(
            decision=decision,
            confidence=confidence,
            options_considered=options,
            rationale=rationale,
            session_id=context.session_id or 'unknown',
            caused_by=context.current_parent,
            tags=['decision', 'generic']
        )

        return [entry]

    def _estimate_decision_confidence(self, rationale: str) -> float:
        """
        Estimate confidence from decision rationale.

        Args:
            rationale: Explanation for decision

        Returns:
            Confidence score 0.0-1.0
        """
        if not rationale:
            return 0.5

        rationale_lower = rationale.lower()

        # High confidence indicators
        high_confidence_terms = [
            'clearly', 'obviously', 'definitely', 'best',
            'optimal', 'superior', 'most appropriate'
        ]

        # Low confidence indicators
        low_confidence_terms = [
            'might', 'could', 'perhaps', 'maybe',
            'uncertain', 'not sure', 'both viable'
        ]

        high_count = sum(1 for term in high_confidence_terms if term in rationale_lower)
        low_count = sum(1 for term in low_confidence_terms if term in rationale_lower)

        base = 0.6  # Decisions are typically more confident than hypotheses

        if high_count > low_count:
            return min(0.9, base + (high_count * 0.1))
        elif low_count > high_count:
            return max(0.3, base - (low_count * 0.1))

        return base


class TradeoffAnalysisProbe(DecisionProbe):
    """
    Enhanced decision probe that captures tradeoff analysis.

    Identifies when decisions involve explicit tradeoff evaluation.
    """

    TRADEOFF_INDICATORS = [
        'tradeoff', 'trade-off', 'pros and cons',
        'advantage', 'disadvantage', 'benefit vs',
        'cost vs', 'performance vs', 'complexity vs'
    ]

    def observe_filtered(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """Extend observation to capture tradeoff analysis"""
        entries = super().observe_filtered(context)

        # Check if rationale contains tradeoff analysis
        rationale = context.event_data.get('rationale', '')
        if rationale and self._contains_tradeoff_analysis(rationale):
            tradeoff_entry = self._create_tradeoff_entry(rationale, context)
            if tradeoff_entry:
                if entries:
                    entries.append(tradeoff_entry)
                else:
                    entries = [tradeoff_entry]

        return entries

    def _contains_tradeoff_analysis(self, rationale: str) -> bool:
        """Check if rationale contains tradeoff discussion"""
        rationale_lower = rationale.lower()
        return any(indicator in rationale_lower for indicator in self.TRADEOFF_INDICATORS)

    def _create_tradeoff_entry(self, rationale: str, context: ProbeContext) -> Optional[LogEntry]:
        """
        Create reasoning entry documenting tradeoff analysis.

        Args:
            rationale: Decision rationale with tradeoff discussion
            context: Event context

        Returns:
            LogEntry for tradeoff analysis
        """
        return LogEntry.create(
            event_type='reasoning',
            event_data={
                'statement': 'Tradeoff analysis performed for decision',
                'confidence': 0.85,
                'evidence': [rationale[:200]],
                'analysis_type': 'tradeoff'
            },
            session_id=context.session_id or 'unknown',
            caused_by=context.current_parent,
            tags=['reasoning', 'tradeoff_analysis', 'decision_quality']
        )
