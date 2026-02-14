"""
Error Recovery Probe

Tracks error recovery patterns - how errors are resolved, not just that they occurred.
Captures recovery strategies, time to resolution, and effectiveness patterns.
"""

from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass
import re

from .base import FilteringProbe, ProbeContext, LogEntry


@dataclass
class ErrorRecoverySession:
    """Tracks an error and its recovery process"""
    error_id: str
    error_type: str
    error_message: str
    error_time: datetime
    recovery_actions: List[Dict] = None
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    recovery_strategy: Optional[str] = None

    def __post_init__(self):
        if self.recovery_actions is None:
            self.recovery_actions = []


class ErrorRecoveryProbe(FilteringProbe):
    """
    Tracks error recovery patterns.

    Captures:
    - Recovery strategies (read docs, search code, backtrack, ask user)
    - Time to recovery
    - Success rates by strategy type
    - Error category → recovery mapping

    Events observed:
    - tool_call_error: Initial error detection
    - tool_call_start/complete: Recovery actions
    - thinking_block: Recovery reasoning
    """

    # Recovery strategy patterns
    STRATEGY_PATTERNS = {
        'read_docs': re.compile(r'\b(read|check|consult|look at|view)\s+(docs?|documentation|readme|guide)', re.I),
        'search_code': re.compile(r'\b(search|grep|find|look for)\s+(code|file|function|class|implementation)', re.I),
        'backtrack': re.compile(r'\b(revert|undo|go back|rollback|restore|previous)', re.I),
        'ask_user': re.compile(r'\b(ask|clarify|confirm|check with|user)', re.I),
        'try_alternative': re.compile(r'\b(try|attempt)\s+(different|alternative|another|other)', re.I),
        'debug_inspect': re.compile(r'\b(debug|inspect|examine|investigate|check)', re.I),
        'fix_typo': re.compile(r'\b(typo|misspell|spelling|syntax error)', re.I),
        'add_missing': re.compile(r'\b(missing|add|include|import)', re.I)
    }

    # Error category patterns
    ERROR_CATEGORIES = {
        'file_not_found': re.compile(r'\b(file not found|no such file|cannot find|missing file)', re.I),
        'permission_denied': re.compile(r'\b(permission denied|access denied|unauthorized)', re.I),
        'syntax_error': re.compile(r'\b(syntax error|parse error|invalid syntax)', re.I),
        'type_error': re.compile(r'\b(type error|wrong type|incompatible type)', re.I),
        'import_error': re.compile(r'\b(import error|module not found|cannot import)', re.I),
        'network_error': re.compile(r'\b(network|connection|timeout|unreachable)', re.I),
        'command_failed': re.compile(r'\b(command failed|execution failed|exit code)', re.I)
    }

    def __init__(self, enabled: bool = True, max_recovery_window_seconds: int = 300):
        super().__init__(enabled)
        self.max_recovery_window_seconds = max_recovery_window_seconds
        self._active_errors: Dict[str, ErrorRecoverySession] = {}
        self._completed_recoveries: List[ErrorRecoverySession] = []

    def can_observe(self, event_type: str) -> bool:
        """Observe error events and potential recovery actions"""
        return event_type in [
            'tool_call_error',
            'tool_call_start',
            'tool_call_complete',
            'thinking_block'
        ]

    def observe_filtered(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """Track error recovery patterns"""
        event_type = context.event_type

        if event_type == 'tool_call_error':
            return self._handle_error(context)
        elif event_type in ['tool_call_start', 'tool_call_complete', 'thinking_block']:
            return self._handle_recovery_action(context)

        return None

    def _handle_error(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """Track new error occurrence"""
        data = context.event_data
        error_type = data.get('error_type', 'unknown')
        error_message = data.get('error_message', '')
        call_id = data.get('call_id', f"error-{context.timestamp.timestamp()}")

        # Categorize error
        error_category = self._categorize_error(error_message)

        # Create error recovery session
        session = ErrorRecoverySession(
            error_id=call_id,
            error_type=error_category or error_type,
            error_message=error_message,
            error_time=context.timestamp
        )

        self._active_errors[call_id] = session

        # Create log entry
        entry = LogEntry(
            event_id=f"error-recovery-start-{call_id}",
            timestamp=context.timestamp,
            event_type="error_recovery",
            event_data={
                'error_id': call_id,
                'error_type': session.error_type,
                'error_message': error_message,
                'category': error_category,
                'recovery_phase': 'detected'
            },
            session_id=context.session_id,
            tags=['error', 'recovery', 'start', error_category or 'uncategorized']
        )

        return [entry]

    def _handle_recovery_action(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """Track recovery actions following errors"""
        if not self._active_errors:
            return None

        entries = []

        # Check all active errors for potential recovery actions
        for error_id, session in list(self._active_errors.items()):
            # Check if action is within recovery window
            time_since_error = (context.timestamp - session.error_time).total_seconds()
            if time_since_error > self.max_recovery_window_seconds:
                # Timeout - mark as unresolved
                self._complete_recovery(error_id, success=False)
                continue

            # Detect recovery strategy from action
            strategy = self._detect_recovery_strategy(context)
            if strategy:
                session.recovery_actions.append({
                    'timestamp': context.timestamp,
                    'strategy': strategy,
                    'event_type': context.event_type,
                    'data': context.event_data
                })

                # Update primary strategy if not set
                if not session.recovery_strategy:
                    session.recovery_strategy = strategy

                # Check for resolution indicators
                if self._is_resolution_indicator(context, session):
                    session.resolved = True
                    session.resolution_time = context.timestamp

                    # Create resolution entry
                    time_to_recovery = (session.resolution_time - session.error_time).total_seconds()

                    entry = LogEntry(
                        event_id=f"error-recovery-complete-{error_id}",
                        timestamp=context.timestamp,
                        event_type="error_recovery",
                        event_data={
                            'error_id': error_id,
                            'error_type': session.error_type,
                            'recovery_strategy': session.recovery_strategy,
                            'recovery_phase': 'resolved',
                            'time_to_recovery_seconds': time_to_recovery,
                            'actions_taken': len(session.recovery_actions),
                            'successful': True
                        },
                        session_id=context.session_id,
                        tags=['error', 'recovery', 'resolved', session.recovery_strategy or 'unknown'],
                        caused_by=f"error-recovery-start-{error_id}"
                    )
                    entries.append(entry)

                    # Move to completed
                    self._complete_recovery(error_id, success=True)

        return entries if entries else None

    def _categorize_error(self, error_message: str) -> Optional[str]:
        """Categorize error type from message"""
        for category, pattern in self.ERROR_CATEGORIES.items():
            if pattern.search(error_message):
                return category
        return None

    def _detect_recovery_strategy(self, context: ProbeContext) -> Optional[str]:
        """Detect recovery strategy from event"""
        event_type = context.event_type
        data = context.event_data

        # Check thinking blocks for strategy indicators
        if event_type == 'thinking_block':
            content = data.get('content', '')
            for strategy, pattern in self.STRATEGY_PATTERNS.items():
                if pattern.search(content):
                    return strategy

        # Check tool usage for strategy
        elif event_type == 'tool_call_start':
            tool_name = data.get('tool_name', '')
            parameters = data.get('parameters', {})

            if tool_name == 'Read':
                # Reading docs or code for recovery
                file_path = parameters.get('file_path', '')
                if 'README' in file_path or 'doc' in file_path.lower():
                    return 'read_docs'
                return 'debug_inspect'

            elif tool_name == 'Grep':
                return 'search_code'

            elif tool_name == 'Edit':
                return 'fix_typo'  # Likely fixing the error

            elif tool_name == 'AskUserQuestion':
                return 'ask_user'

        return None

    def _is_resolution_indicator(self, context: ProbeContext, session: ErrorRecoverySession) -> bool:
        """Check if action indicates error resolution"""
        event_type = context.event_type
        data = context.event_data

        # Successful tool completion after error
        if event_type == 'tool_call_complete':
            success = data.get('success', False)
            return success

        # Thinking blocks with resolution language
        if event_type == 'thinking_block':
            content = data.get('content', '').lower()
            resolution_indicators = [
                'fixed', 'resolved', 'corrected', 'working now',
                'that should work', 'problem solved', 'issue resolved'
            ]
            return any(indicator in content for indicator in resolution_indicators)

        return False

    def _complete_recovery(self, error_id: str, success: bool):
        """Move error recovery session to completed"""
        if error_id in self._active_errors:
            session = self._active_errors.pop(error_id)
            session.resolved = success
            self._completed_recoveries.append(session)

    def get_recovery_stats(self) -> Dict:
        """Get recovery statistics"""
        if not self._completed_recoveries:
            return {
                'total_errors': 0,
                'resolved': 0,
                'unresolved': 0,
                'success_rate': 0.0,
                'avg_recovery_time': 0.0,
                'strategies': {}
            }

        total = len(self._completed_recoveries)
        resolved = sum(1 for s in self._completed_recoveries if s.resolved)

        # Calculate average recovery time for resolved errors
        recovery_times = [
            (s.resolution_time - s.error_time).total_seconds()
            for s in self._completed_recoveries
            if s.resolved and s.resolution_time
        ]
        avg_time = sum(recovery_times) / len(recovery_times) if recovery_times else 0.0

        # Strategy breakdown
        strategies = {}
        for session in self._completed_recoveries:
            if session.recovery_strategy:
                if session.recovery_strategy not in strategies:
                    strategies[session.recovery_strategy] = {
                        'count': 0,
                        'success': 0,
                        'fail': 0
                    }
                strategies[session.recovery_strategy]['count'] += 1
                if session.resolved:
                    strategies[session.recovery_strategy]['success'] += 1
                else:
                    strategies[session.recovery_strategy]['fail'] += 1

        return {
            'total_errors': total,
            'resolved': resolved,
            'unresolved': total - resolved,
            'success_rate': resolved / total if total > 0 else 0.0,
            'avg_recovery_time': avg_time,
            'strategies': strategies
        }
