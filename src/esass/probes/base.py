"""
Base probe interface and context management.

Defines the core abstractions for event observation probes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from esass.models import LogEntry


@dataclass
class ProbeContext:
    """
    Context information passed to probes.

    Provides access to session state, causality tracking, and metadata.
    """
    event_type: str
    event_data: Dict[str, Any]
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    call_stack: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

        # Ensure session_id is set
        if self.session_id is None and self.conversation_id:
            self.session_id = self.conversation_id

    @property
    def current_parent(self) -> Optional[str]:
        """Get the most recent event ID for causality tracking"""
        return self.call_stack[-1] if self.call_stack else None


class Probe(ABC):
    """
    Base class for all ESASS observation probes.

    Probes observe specific types of events and transform them into
    structured log entries for pattern detection.

    Subclasses must implement:
    - can_observe(): Determine if this probe handles an event type
    - observe(): Process the event and return log entries
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize probe.

        Args:
            enabled: Whether this probe is active
        """
        self.enabled = enabled
        self.observations_count = 0
        self.errors_count = 0

    @abstractmethod
    def can_observe(self, event_type: str) -> bool:
        """
        Determine if this probe can handle the event type.

        Args:
            event_type: The type of event (e.g., 'tool_call_start')

        Returns:
            True if this probe should observe this event type
        """
        pass

    @abstractmethod
    def observe(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """
        Process an event and generate log entries.

        Args:
            context: Event context with data and metadata

        Returns:
            List of log entries to record, or None if event ignored
        """
        pass

    def on_error(self, error: Exception, context: ProbeContext):
        """
        Handle probe errors gracefully.

        Args:
            error: The exception that occurred
            context: Context when error occurred
        """
        self.errors_count += 1
        # Default: log and continue (don't crash the system)
        import logging
        logging.error(f"{self.__class__.__name__} error: {error}", exc_info=True)

    @property
    def name(self) -> str:
        """Get probe name for identification"""
        return self.__class__.__name__

    @property
    def stats(self) -> Dict[str, int]:
        """Get probe statistics"""
        return {
            'observations': self.observations_count,
            'errors': self.errors_count,
        }


class FilteringProbe(Probe):
    """
    Probe with configurable filtering capabilities.

    Allows filtering events by session, tags, or custom predicates.
    """

    def __init__(self, enabled: bool = True,
                 include_sessions: Optional[List[str]] = None,
                 exclude_sessions: Optional[List[str]] = None,
                 min_interval_seconds: float = 0.0):
        """
        Initialize filtering probe.

        Args:
            enabled: Whether probe is active
            include_sessions: Only observe these session IDs (None = all)
            exclude_sessions: Skip these session IDs
            min_interval_seconds: Minimum time between observations
        """
        super().__init__(enabled)
        self.include_sessions = include_sessions
        self.exclude_sessions = exclude_sessions or []
        self.min_interval_seconds = min_interval_seconds
        self.last_observation_time: Optional[datetime] = None

    def should_filter(self, context: ProbeContext) -> bool:
        """
        Determine if event should be filtered out.

        Args:
            context: Event context

        Returns:
            True if event should be ignored
        """
        # Session filtering
        if self.include_sessions and context.session_id not in self.include_sessions:
            return True

        if context.session_id in self.exclude_sessions:
            return True

        # Rate limiting
        if self.min_interval_seconds > 0 and self.last_observation_time:
            elapsed = (context.timestamp - self.last_observation_time).total_seconds()
            if elapsed < self.min_interval_seconds:
                return True

        return False

    def observe(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """Apply filtering before observation"""
        if self.should_filter(context):
            return None

        result = self.observe_filtered(context)
        if result:
            self.last_observation_time = context.timestamp
            self.observations_count += 1

        return result

    @abstractmethod
    def observe_filtered(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """
        Process event after filtering.

        Subclasses implement this instead of observe().
        """
        pass


class TagExtractor:
    """
    Helper for extracting semantic tags from event data.

    Used by probes to enrich events with contextual tags.
    """

    @staticmethod
    def extract_from_tool(tool_name: str, parameters: Dict[str, Any]) -> List[str]:
        """
        Extract tags from tool usage.

        Args:
            tool_name: Name of tool (Read, Write, Bash, etc.)
            parameters: Tool parameters

        Returns:
            List of semantic tags
        """
        tags = [tool_name.lower()]

        # File operation tags
        if tool_name in ['Read', 'Write', 'Edit']:
            file_path = parameters.get('file_path', '')
            if file_path:
                # File extension
                if '.' in file_path:
                    ext = file_path.rsplit('.', 1)[-1].lower()
                    tags.append(f'file_type:{ext}')

                    # Language detection
                    lang_map = {
                        'py': 'python', 'js': 'javascript', 'ts': 'typescript',
                        'java': 'java', 'cpp': 'cpp', 'c': 'c', 'go': 'go',
                        'rs': 'rust', 'rb': 'ruby', 'php': 'php',
                        'md': 'markdown', 'json': 'json', 'yaml': 'yaml',
                        'yml': 'yaml', 'xml': 'xml', 'html': 'html', 'css': 'css'
                    }
                    if ext in lang_map:
                        tags.append(f'language:{lang_map[ext]}')

                # Path analysis
                path_lower = file_path.lower()
                if 'test' in path_lower:
                    tags.append('testing')
                if 'doc' in path_lower or 'readme' in path_lower:
                    tags.append('documentation')
                if 'config' in path_lower:
                    tags.append('configuration')
                if '.git' in path_lower:
                    tags.append('version_control')

        # Bash command tags
        elif tool_name == 'Bash':
            command = parameters.get('command', '')
            if command:
                cmd_lower = command.lower()

                # Git operations
                if 'git' in cmd_lower:
                    tags.append('git')
                    tags.append('version_control')
                    if 'commit' in cmd_lower:
                        tags.append('git_commit')
                    elif 'push' in cmd_lower:
                        tags.append('git_push')
                    elif 'pull' in cmd_lower:
                        tags.append('git_pull')
                    elif 'status' in cmd_lower:
                        tags.append('git_status')
                    elif 'diff' in cmd_lower:
                        tags.append('git_diff')

                # Testing
                if any(test in cmd_lower for test in ['pytest', 'npm test', 'jest', 'mocha']):
                    tags.append('testing')

                # Build
                if any(build in cmd_lower for build in ['make', 'build', 'compile', 'npm run build']):
                    tags.append('build')

                # Package management
                if any(pkg in cmd_lower for pkg in ['npm install', 'pip install', 'cargo add']):
                    tags.append('dependencies')

        # Search operations
        elif tool_name in ['Grep', 'Glob']:
            tags.append('code_search')
            pattern = parameters.get('pattern', '')
            if pattern:
                tags.append('pattern_matching')

        return tags

    @staticmethod
    def extract_from_text(text: str) -> List[str]:
        """
        Extract semantic tags from text content.

        Args:
            text: Text to analyze

        Returns:
            List of semantic tags
        """
        tags = []
        text_lower = text.lower()

        # Common task types
        task_keywords = {
            'bug': 'debugging',
            'fix': 'debugging',
            'error': 'debugging',
            'test': 'testing',
            'refactor': 'refactoring',
            'optimize': 'optimization',
            'document': 'documentation',
            'implement': 'feature_implementation',
            'add feature': 'feature_implementation',
            'review': 'code_review',
            'deploy': 'deployment',
        }

        for keyword, tag in task_keywords.items():
            if keyword in text_lower:
                tags.append(tag)

        return tags
