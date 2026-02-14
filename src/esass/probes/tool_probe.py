"""
Tool call observation probe.

Captures tool invocations, parameters, results, and outcomes.
"""

from typing import Dict, List, Optional

from esass.probes.base import FilteringProbe, ProbeContext, TagExtractor
from esass.models import LogEntry, create_tool_usage_event


class ToolCallProbe(FilteringProbe):
    """
    Observes tool call lifecycle: start → complete/error.

    Tracks:
    - Tool invocations (Read, Write, Bash, Grep, etc.)
    - Parameters and context
    - Success/failure outcomes
    - Execution timing
    - Causality relationships
    """

    # Tool calls that should be observed
    OBSERVED_TOOLS = {
        'Read', 'Write', 'Edit', 'Bash', 'Grep', 'Glob',
        'Task', 'AskUserQuestion', 'EnterPlanMode', 'WebFetch', 'WebSearch'
    }

    def __init__(self, enabled: bool = True,
                 observe_tools: Optional[List[str]] = None):
        """
        Initialize tool call probe.

        Args:
            enabled: Whether probe is active
            observe_tools: Specific tools to observe (None = all)
        """
        super().__init__(enabled)
        self.observe_tools = observe_tools or list(self.OBSERVED_TOOLS)
        self.pending_calls: Dict[str, dict] = {}  # Track incomplete calls

    def can_observe(self, event_type: str) -> bool:
        """Handle tool_call_start, tool_call_complete, tool_call_error"""
        return event_type in [
            'tool_call_start',
            'tool_call_complete',
            'tool_call_error'
        ]

    def observe_filtered(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """Process tool call events"""
        event_type = context.event_type
        event_data = context.event_data

        if event_type == 'tool_call_start':
            return self._on_tool_start(context)
        elif event_type == 'tool_call_complete':
            return self._on_tool_complete(context)
        elif event_type == 'tool_call_error':
            return self._on_tool_error(context)

        return None

    def _on_tool_start(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """
        Handle tool call start event.

        Creates a tool_usage event with 'pending' outcome.
        """
        tool_name = context.event_data.get('tool_name')
        if not tool_name or tool_name not in self.observe_tools:
            return None

        parameters = context.event_data.get('parameters', {})
        call_id = context.event_data.get('call_id')

        # Extract semantic tags
        tags = TagExtractor.extract_from_tool(tool_name, parameters)

        # Create log entry
        entry = create_tool_usage_event(
            tool_name=tool_name,
            parameters=self._sanitize_parameters(parameters),
            outcome_assessment='pending',
            session_id=context.session_id or 'unknown',
            caused_by=context.current_parent,
            tags=tags
        )

        # Track for completion
        if call_id:
            self.pending_calls[call_id] = {
                'event_id': entry.event_id,
                'tool_name': tool_name,
                'start_time': context.timestamp
            }

        return [entry]

    def _on_tool_complete(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """
        Handle tool call completion.

        Updates the pending entry with success outcome and timing.
        """
        call_id = context.event_data.get('call_id')
        result = context.event_data.get('result')

        if not call_id or call_id not in self.pending_calls:
            # Completion without start - create standalone entry
            return self._create_standalone_completion(context, success=True)

        pending = self.pending_calls.pop(call_id)
        duration = (context.timestamp - pending['start_time']).total_seconds()

        # Create outcome event
        outcome_entry = LogEntry.create(
            event_type='outcome',
            event_data={
                'tool_name': pending['tool_name'],
                'success': True,
                'duration_seconds': duration,
                'result_summary': self._summarize_result(result)
            },
            session_id=context.session_id or 'unknown',
            caused_by=pending['event_id'],
            tags=['outcome', 'success', pending['tool_name'].lower()]
        )

        return [outcome_entry]

    def _on_tool_error(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """
        Handle tool call error.

        Creates an error event linked to the original tool call.
        """
        call_id = context.event_data.get('call_id')
        error = context.event_data.get('error', 'Unknown error')

        if call_id and call_id in self.pending_calls:
            pending = self.pending_calls.pop(call_id)
            caused_by = pending['event_id']
            tool_name = pending['tool_name']
        else:
            # Error without tracked start
            caused_by = context.current_parent
            tool_name = context.event_data.get('tool_name', 'unknown')

        # Create error event
        error_entry = LogEntry.create(
            event_type='error',
            event_data={
                'tool_name': tool_name,
                'error_message': str(error),
                'error_type': type(error).__name__ if isinstance(error, Exception) else 'unknown'
            },
            session_id=context.session_id or 'unknown',
            caused_by=caused_by,
            tags=['error', 'tool_error', tool_name.lower()]
        )

        return [error_entry]

    def _create_standalone_completion(self, context: ProbeContext,
                                     success: bool) -> List[LogEntry]:
        """
        Create completion event without matching start.

        Used when we observe a completion but missed the start.
        """
        tool_name = context.event_data.get('tool_name', 'unknown')
        result = context.event_data.get('result')

        entry = LogEntry.create(
            event_type='outcome',
            event_data={
                'tool_name': tool_name,
                'success': success,
                'result_summary': self._summarize_result(result) if success else None,
                'standalone': True  # Flag that we missed the start
            },
            session_id=context.session_id or 'unknown',
            caused_by=context.current_parent,
            tags=['outcome', 'success' if success else 'failure', tool_name.lower()]
        )

        return [entry]

    def _sanitize_parameters(self, parameters: Dict) -> Dict:
        """
        Remove sensitive data from parameters before logging.

        Args:
            parameters: Raw tool parameters

        Returns:
            Sanitized parameters safe to log
        """
        sanitized = parameters.copy()

        # Remove or redact sensitive fields
        sensitive_keys = ['password', 'token', 'api_key', 'secret', 'credential']
        for key in list(sanitized.keys()):
            if any(s in key.lower() for s in sensitive_keys):
                sanitized[key] = '[REDACTED]'

        # Truncate large values
        for key, value in sanitized.items():
            if isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:1000] + '... [truncated]'

        return sanitized

    def _summarize_result(self, result) -> str:
        """
        Create a brief summary of tool result.

        Args:
            result: Tool return value

        Returns:
            Human-readable summary
        """
        if result is None:
            return 'null'

        # Handle different result types
        if isinstance(result, bool):
            return 'true' if result else 'false'

        if isinstance(result, (int, float)):
            return str(result)

        if isinstance(result, str):
            # Truncate long strings
            if len(result) > 200:
                return result[:200] + '...'
            return result

        if isinstance(result, (list, tuple)):
            return f'{len(result)} items'

        if isinstance(result, dict):
            keys = list(result.keys())[:5]
            return f'dict with keys: {", ".join(keys)}'

        # Generic fallback
        return f'{type(result).__name__}'


class ToolSequenceDetector(ToolCallProbe):
    """
    Enhanced tool probe that detects common tool sequences.

    Identifies patterns like:
    - Read → Edit → Write (file modification)
    - Grep → Read (search → examine)
    - Bash git status → Bash git add → Bash git commit (git workflow)
    """

    def __init__(self, enabled: bool = True,
                 sequence_window_size: int = 5):
        """
        Initialize sequence detector.

        Args:
            enabled: Whether probe is active
            sequence_window_size: How many recent tools to track for patterns
        """
        super().__init__(enabled)
        self.sequence_window_size = sequence_window_size
        self.recent_tools: List[str] = []

    def observe_filtered(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """Extend observation to detect sequences"""
        entries = super().observe_filtered(context)

        # Track tool sequence
        if context.event_type == 'tool_call_start':
            tool_name = context.event_data.get('tool_name')
            if tool_name:
                self.recent_tools.append(tool_name)
                if len(self.recent_tools) > self.sequence_window_size:
                    self.recent_tools.pop(0)

                # Detect known sequences
                sequence_entry = self._detect_sequence(context)
                if sequence_entry and entries:
                    entries.append(sequence_entry)

        return entries

    def _detect_sequence(self, context: ProbeContext) -> Optional[LogEntry]:
        """
        Detect if recent tools form a known pattern.

        Returns:
            LogEntry describing the detected sequence, or None
        """
        if len(self.recent_tools) < 2:
            return None

        recent = self.recent_tools[-3:]  # Last 3 tools

        # File modification pattern
        if recent == ['Read', 'Edit', 'Write']:
            return LogEntry.create(
                event_type='reasoning',
                event_data={
                    'statement': 'File modification workflow detected',
                    'confidence': 0.9,
                    'evidence': ['Read→Edit→Write sequence']
                },
                session_id=context.session_id or 'unknown',
                tags=['pattern', 'file_modification', 'workflow']
            )

        # Search and examine pattern
        if recent[-2:] == ['Grep', 'Read'] or recent[-2:] == ['Glob', 'Read']:
            return LogEntry.create(
                event_type='reasoning',
                event_data={
                    'statement': 'Search and examine pattern detected',
                    'confidence': 0.85,
                    'evidence': [f'{recent[-2]}→Read sequence']
                },
                session_id=context.session_id or 'unknown',
                tags=['pattern', 'code_exploration', 'search']
            )

        return None
