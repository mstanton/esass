"""
Enhanced Pattern Detector with Deep Semantic Extraction.

Addresses the 'tool_call(none)' problem by extracting rich semantic tags
from nested event_data structures, enabling detection of meaningful patterns like:
- Read(py) → Grep(search) → Edit(py) → Bash(test)
- git_status → git_add → git_commit
- file_exploration → code_modification → validation

Enhanced with local LLM integration for:
- Semantic pattern clustering
- Improved pattern naming
- Duplicate detection
"""

import asyncio
import logging
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from esass.models import LogEntry, PatternDefinition, PatternType

logger = logging.getLogger(__name__)


class SemanticTagExtractor:
    """
    Extract rich semantic tags from event_data structures.

    Transforms nested data into flat, queryable tag sets for pattern mining.
    """

    # Known tool categories for semantic grouping
    TOOL_CATEGORIES = {
        'Read': 'file_read',
        'Write': 'file_write',
        'Edit': 'file_edit',
        'Glob': 'file_search',
        'Grep': 'content_search',
        'Bash': 'command',
        'Task': 'delegation',
        'WebFetch': 'web',
        'WebSearch': 'web',
        'AskUserQuestion': 'interaction',
    }

    # Tags to filter out (noise from hook execution)
    NOISE_TAGS = {
        'boundary_action', 'hook_error', 'hook_success',
        'unknown', 'none', 'null', ''
    }

    # File type semantic mappings
    FILE_TYPE_SEMANTICS = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.json': 'config',
        '.yaml': 'config',
        '.yml': 'config',
        '.md': 'docs',
        '.txt': 'text',
        '.sh': 'script',
        '.ps1': 'script',
    }

    # Command pattern recognition
    COMMAND_PATTERNS = {
        r'git\s+status': 'git_status',
        r'git\s+add': 'git_add',
        r'git\s+commit': 'git_commit',
        r'git\s+push': 'git_push',
        r'git\s+pull': 'git_pull',
        r'git\s+diff': 'git_diff',
        r'git\s+log': 'git_log',
        r'pytest|python\s+-m\s+pytest': 'test_run',
        r'npm\s+test|yarn\s+test': 'test_run',
        r'pip\s+install': 'dependency',
        r'npm\s+install|yarn\s+add': 'dependency',
        r'python|node|ruby': 'execution',
        r'docker': 'container',
        r'kubectl': 'kubernetes',
    }

    @classmethod
    def extract_tags(cls, entry: LogEntry) -> List[str]:
        """
        Extract all semantic tags from a log entry.

        Args:
            entry: LogEntry with potentially nested event_data

        Returns:
            List of semantic tags (e.g., ['Read', 'python', 'file_read'])
        """
        tags = set()
        event_data = entry.event_data or {}

        # 1. Add existing entry.tags if present
        if entry.tags:
            tags.update(entry.tags)

        # 2. Extract tool name (primary semantic key)
        tool_name = event_data.get('tool_name')
        if tool_name:
            tags.add(tool_name)
            # Add category tag
            if tool_name in cls.TOOL_CATEGORIES:
                tags.add(cls.TOOL_CATEGORIES[tool_name])

        # 3. Extract from nested context structure
        context = event_data.get('context', {})
        if isinstance(context, dict):
            # Category (file_operation, search, command, etc.)
            if context.get('category'):
                tags.add(context['category'])

            # Action (read, edit, search, etc.)
            if context.get('action'):
                tags.add(context['action'])

            # Context-level tags
            if context.get('tags'):
                for tag in context['tags']:
                    # Parse filetype tags: "filetype:.py" → "python"
                    if tag.startswith('filetype:'):
                        ext = tag.split(':', 1)[1]
                        if ext in cls.FILE_TYPE_SEMANTICS:
                            tags.add(cls.FILE_TYPE_SEMANTICS[ext])
                        else:
                            tags.add(ext.lstrip('.'))
                    else:
                        tags.add(tag)

        # 4. Extract from parameters
        params = event_data.get('parameters', {})
        if isinstance(params, dict):
            cls._extract_from_parameters(params, tags, tool_name)

        # 5. Extract from command (for Bash events)
        command = params.get('command', '') if isinstance(params, dict) else ''
        if command:
            cls._extract_from_command(command, tags)

        # 6. Event type augmentation
        event_type = entry.event_type
        if event_type and event_type not in ['tool_call', 'tool_usage']:
            tags.add(event_type)

        # 7. Filter out noise tags
        tags = {t for t in tags if t.lower() not in cls.NOISE_TAGS}

        return sorted(tags)

    @classmethod
    def _extract_from_parameters(cls, params: Dict, tags: Set[str],
                                  tool_name: Optional[str]) -> None:
        """Extract semantic tags from tool parameters."""
        # File path analysis
        file_path = params.get('file_path', '') or params.get('path', '')
        if file_path:
            # Extract file extension
            if '.' in file_path:
                ext = '.' + file_path.rsplit('.', 1)[-1].lower()
                if ext in cls.FILE_TYPE_SEMANTICS:
                    tags.add(cls.FILE_TYPE_SEMANTICS[ext])

            # Detect special directories
            path_lower = file_path.lower()
            if 'test' in path_lower:
                tags.add('testing')
            if 'src/' in path_lower or '/src/' in path_lower:
                tags.add('source')
            if 'config' in path_lower or 'settings' in path_lower:
                tags.add('config')

        # Search pattern analysis
        pattern = params.get('pattern', '')
        if pattern:
            if 'def ' in pattern or 'function' in pattern:
                tags.add('function_search')
            if 'class ' in pattern:
                tags.add('class_search')
            if 'import' in pattern:
                tags.add('import_search')

    @classmethod
    def _extract_from_command(cls, command: str, tags: Set[str]) -> None:
        """Extract semantic tags from bash commands."""
        import re

        command_lower = command.lower()

        for pattern, tag in cls.COMMAND_PATTERNS.items():
            if re.search(pattern, command_lower):
                tags.add(tag)

        # General git detection
        if command_lower.startswith('git '):
            tags.add('git')

        # Detect file operations
        if any(cmd in command_lower for cmd in ['rm ', 'mv ', 'cp ', 'mkdir']):
            tags.add('file_management')

    @classmethod
    def create_event_key(cls, entry: LogEntry, granularity: str = 'medium') -> str:
        """
        Create a semantic event key for pattern mining.

        Args:
            entry: LogEntry to process
            granularity: 'coarse', 'medium', or 'fine'
                - coarse: tool category only (file_read, command)
                - medium: tool + primary semantic (Read:python, Bash:git)
                - fine: tool + all semantics (Read:python,testing,source)

        Returns:
            Event key string for sequence mining
        """
        tags = cls.extract_tags(entry)
        event_data = entry.event_data or {}
        tool_name = event_data.get('tool_name', entry.event_type)

        # Skip noise event types entirely
        if tool_name and tool_name.lower() in cls.NOISE_TAGS:
            return None

        if granularity == 'coarse':
            # Just the category
            category = cls.TOOL_CATEGORIES.get(tool_name, tool_name)
            return category

        elif granularity == 'medium':
            # Tool + primary semantic tag
            primary_tags = []

            # Prioritize: filetype > action > category
            for tag in tags:
                if tag in cls.FILE_TYPE_SEMANTICS.values():
                    primary_tags.append(tag)
                    break

            if not primary_tags:
                context = event_data.get('context', {})
                if isinstance(context, dict) and context.get('action'):
                    primary_tags.append(context['action'])

            # For git commands, use git action
            if 'git' in tags:
                for tag in tags:
                    if tag.startswith('git_'):
                        primary_tags = [tag]
                        break

            if primary_tags:
                return f"{tool_name}:{','.join(primary_tags[:2])}"
            return tool_name

        else:  # fine
            # Tool + all relevant tags (limited)
            relevant_tags = [t for t in tags if t != tool_name][:4]
            if relevant_tags:
                return f"{tool_name}:{','.join(relevant_tags)}"
            return tool_name


class EnhancedPatternDetector:
    """
    Pattern detector with deep semantic extraction.

    Improvements over base detector:
    1. Extracts tool names and context from event_data
    2. Multiple granularity levels for pattern mining
    3. Semantic clustering of related patterns
    4. Workflow detection (git workflow, file modification, etc.)
    """

    def __init__(
        self,
        min_support: int = 5,
        min_confidence: float = 0.7,
        min_stability_days: int = 3,  # Reduced for faster candidacy
        max_gap_seconds: int = 600,
        min_sequence_length: int = 2,
        max_sequence_length: int = 6,
        granularity: str = 'medium',
        count_within_session: bool = True
    ):
        """
        Initialize enhanced pattern detector.

        Args:
            min_support: Minimum occurrences for a pattern
            min_confidence: Minimum reliability (0.0-1.0)
            min_stability_days: Minimum days pattern must appear
            max_gap_seconds: Maximum time between events in sequence
            min_sequence_length: Minimum events in a sequence
            max_sequence_length: Maximum events in a sequence
            granularity: 'coarse', 'medium', or 'fine'
            count_within_session: Count multiple occurrences within same session
        """
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_stability_days = min_stability_days
        self.max_gap_seconds = max_gap_seconds
        self.min_sequence_length = min_sequence_length
        self.max_sequence_length = max_sequence_length
        self.granularity = granularity
        self.count_within_session = count_within_session
        self.extractor = SemanticTagExtractor()

    def detect_patterns(self, logs: List[LogEntry]) -> List[PatternDefinition]:
        """
        Find recurring event sequences with semantic enrichment.

        Args:
            logs: List of log entries to analyze

        Returns:
            List of detected PatternDefinition objects
        """
        if not logs:
            return []

        # Step 1: Group by session
        sessions = self._group_by_session(logs)

        # Step 2: Extract enriched sequences
        sequences = []
        for session_logs in sessions.values():
            seq = self._extract_enriched_sequence(session_logs)
            if len(seq) >= self.min_sequence_length:
                sequences.append(seq)

        # Step 3: Mine frequent subsequences
        frequent_sequences = self._mine_frequent_sequences(
            sequences,
            count_within_session=self.count_within_session
        )

        # Step 4: Create pattern definitions
        patterns = []
        for seq, support in frequent_sequences.items():
            if support >= self.min_support:
                pattern = self._create_pattern(seq, support, logs)
                if pattern and pattern.confidence >= self.min_confidence:
                    patterns.append(pattern)

        # Step 5: Detect higher-level workflow patterns
        workflow_patterns = self._detect_workflow_patterns(patterns)
        patterns.extend(workflow_patterns)

        # Sort by support
        patterns.sort(key=lambda p: p.support, reverse=True)

        return patterns

    def _group_by_session(self, logs: List[LogEntry]) -> Dict[str, List[LogEntry]]:
        """Group log entries by session_id."""
        sessions = defaultdict(list)
        for entry in logs:
            sid = entry.session_id or 'unknown'
            sessions[sid].append(entry)
        return dict(sessions)

    def _extract_enriched_sequence(self, session: List[LogEntry]) -> List[str]:
        """
        Extract semantically enriched event sequence.

        Args:
            session: List of log entries in a session

        Returns:
            List of semantic event keys
        """
        sorted_session = sorted(session, key=lambda e: e.timestamp)

        sequence = []
        last_time = None

        for entry in sorted_session:
            # Check time gap
            try:
                current_time = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
                if last_time:
                    gap = (current_time - last_time).total_seconds()
                    if gap > self.max_gap_seconds:
                        # Gap too large - could indicate session break
                        pass
                last_time = current_time
            except:
                pass

            # Create semantic event key
            event_key = SemanticTagExtractor.create_event_key(
                entry,
                granularity=self.granularity
            )
            # Skip noise events
            if event_key is not None:
                sequence.append(event_key)

        return sequence

    def _mine_frequent_sequences(
        self,
        sequences: List[List[str]],
        count_within_session: bool = True
    ) -> Dict[Tuple[str, ...], int]:
        """
        Find subsequences that appear frequently.

        Args:
            sequences: List of event sequences (one per session)
            count_within_session: If True, count all occurrences within a session.
                                  If False, count each pattern once per session.
        """
        subsequence_counts = Counter()

        for seq in sequences:
            if count_within_session:
                # Count all occurrences within session
                for length in range(self.min_sequence_length,
                                  min(self.max_sequence_length + 1, len(seq) + 1)):
                    for i in range(len(seq) - length + 1):
                        subseq = tuple(seq[i:i+length])
                        subsequence_counts[subseq] += 1
            else:
                # Only count once per session (original behavior)
                seen_in_seq = set()
                for length in range(self.min_sequence_length,
                                  min(self.max_sequence_length + 1, len(seq) + 1)):
                    for i in range(len(seq) - length + 1):
                        subseq = tuple(seq[i:i+length])
                        if subseq not in seen_in_seq:
                            subsequence_counts[subseq] += 1
                            seen_in_seq.add(subseq)

        return dict(subsequence_counts)

    def _create_pattern(
        self,
        sequence: Tuple[str, ...],
        support: int,
        logs: List[LogEntry]
    ) -> Optional[PatternDefinition]:
        """Create PatternDefinition from enriched sequence."""
        exemplars = self._find_exemplars(sequence, logs, limit=5)

        if not exemplars:
            return None

        stability_days = self._calculate_stability(sequence, logs)
        description = self._generate_description(sequence)
        confidence = self._calculate_confidence(sequence, logs)

        # Determine skill candidacy with relaxed criteria
        skill_candidate = (
            support >= self.min_support and
            confidence >= self.min_confidence and
            stability_days >= self.min_stability_days and
            self._is_semantically_meaningful(sequence)
        )

        tags = self._extract_pattern_tags(sequence)
        first_seen, last_seen = self._get_date_range(sequence, logs)

        return PatternDefinition(
            pattern_type=PatternType.TEMPORAL.value,
            support=support,
            confidence=confidence,
            stability_days=stability_days,
            description=description,
            sequence=list(sequence),
            exemplar_ids=[e.entry_id for e in exemplars],
            skill_candidate=skill_candidate,
            tags=tags,
            first_seen=first_seen,
            last_seen=last_seen
        )

    def _is_semantically_meaningful(self, sequence: Tuple[str, ...]) -> bool:
        """
        Check if pattern has semantic meaning beyond generic tool chains.

        Rejects patterns like:
        - tool_call → tool_call (no specificity)
        - Read → Read → Read (repetitive, no workflow)

        Accepts patterns like:
        - Read:python → Edit:python → Bash:test_run
        - Grep:search → Read:python → Edit
        """
        # Reject if all items are identical
        if len(set(sequence)) == 1:
            return False

        # Reject if items lack semantic tags (just tool names)
        has_semantic = any(':' in item for item in sequence)

        # Reject generic patterns
        generic_patterns = {'tool_call', 'tool_usage', 'none'}
        all_generic = all(
            item.split(':')[0] in generic_patterns or item in generic_patterns
            for item in sequence
        )
        if all_generic:
            return False

        return True

    def _calculate_confidence(
        self,
        sequence: Tuple[str, ...],
        logs: List[LogEntry]
    ) -> float:
        """Calculate P(full sequence | first event)."""
        sessions = self._group_by_session(logs)

        sessions_with_first = 0
        sessions_with_full = 0

        for session_logs in sessions.values():
            seq = self._extract_enriched_sequence(session_logs)
            seq_tuple = tuple(seq)

            if len(seq_tuple) > 0:
                # Check if starts similarly (same tool or category)
                first_tool = sequence[0].split(':')[0]
                seq_first_tool = seq_tuple[0].split(':')[0] if seq_tuple else ''

                if first_tool == seq_first_tool:
                    sessions_with_first += 1
                    if self._sequence_contains(seq_tuple, sequence):
                        sessions_with_full += 1

        if sessions_with_first == 0:
            return 0.0

        return sessions_with_full / sessions_with_first

    def _sequence_contains(
        self,
        haystack: Tuple[str, ...],
        needle: Tuple[str, ...]
    ) -> bool:
        """Check if needle appears in haystack (flexible matching)."""
        if len(needle) > len(haystack):
            return False

        # Exact match first
        for i in range(len(haystack) - len(needle) + 1):
            if haystack[i:i+len(needle)] == needle:
                return True

        return False

    def _calculate_stability(
        self,
        sequence: Tuple[str, ...],
        logs: List[LogEntry]
    ) -> int:
        """Calculate days this pattern has appeared."""
        dates_with_pattern = set()

        sessions = self._group_by_session(logs)
        for session_logs in sessions.values():
            seq = self._extract_enriched_sequence(session_logs)
            if self._sequence_contains(tuple(seq), sequence):
                if session_logs:
                    try:
                        ts = session_logs[0].timestamp
                        date = datetime.fromisoformat(ts.replace('Z', '+00:00')).date()
                        dates_with_pattern.add(date)
                    except:
                        pass

        if not dates_with_pattern:
            return 0

        min_date = min(dates_with_pattern)
        max_date = max(dates_with_pattern)
        return (max_date - min_date).days + 1

    def _find_exemplars(
        self,
        sequence: Tuple[str, ...],
        logs: List[LogEntry],
        limit: int
    ) -> List[LogEntry]:
        """Find example log entries demonstrating this pattern."""
        exemplars = []
        sessions = self._group_by_session(logs)

        for session_logs in sessions.values():
            seq = self._extract_enriched_sequence(session_logs)
            if self._sequence_contains(tuple(seq), sequence):
                sorted_session = sorted(session_logs, key=lambda e: e.timestamp)
                if sorted_session:
                    exemplars.append(sorted_session[0])
                    if len(exemplars) >= limit:
                        break

        return exemplars

    def _generate_description(self, sequence: Tuple[str, ...]) -> str:
        """Generate human-readable pattern description."""
        steps = []
        for event_key in sequence:
            if ':' in event_key:
                tool, tags = event_key.split(':', 1)
                tag_list = tags.split(',')[:2]
                steps.append(f"{tool}({','.join(tag_list)})")
            else:
                steps.append(event_key)

        return " -> ".join(steps)

    def _extract_pattern_tags(self, sequence: Tuple[str, ...]) -> List[str]:
        """Extract unique tags from pattern sequence."""
        all_tags = set()

        for event_key in sequence:
            parts = event_key.split(':')
            all_tags.add(parts[0])  # Tool name
            if len(parts) > 1:
                all_tags.update(parts[1].split(','))

        return list(all_tags)

    def _get_date_range(
        self,
        sequence: Tuple[str, ...],
        logs: List[LogEntry]
    ) -> Tuple[str, str]:
        """Get first and last seen timestamps for pattern."""
        timestamps = []

        sessions = self._group_by_session(logs)
        for session_logs in sessions.values():
            seq = self._extract_enriched_sequence(session_logs)
            if self._sequence_contains(tuple(seq), sequence):
                if session_logs:
                    timestamps.append(session_logs[0].timestamp)

        if not timestamps:
            now = datetime.utcnow().isoformat()
            return now, now

        timestamps.sort()
        return timestamps[0], timestamps[-1]

    def cluster_patterns_semantically(
        self,
        patterns: List[PatternDefinition],
        use_llm: bool = True
    ) -> Dict[str, List[PatternDefinition]]:
        """
        Cluster patterns by semantic similarity.

        Uses local LLM for clustering when available, falls back to
        tag-based clustering otherwise.

        Args:
            patterns: List of patterns to cluster
            use_llm: Whether to try LLM-based clustering

        Returns:
            Dict mapping cluster name to list of patterns
        """
        if not patterns:
            return {}

        # Try LLM-based clustering
        if use_llm:
            clusters = self._cluster_with_llm(patterns)
            if clusters:
                return clusters

        # Fallback to tag-based clustering
        return self._cluster_by_tags(patterns)

    def _cluster_with_llm(
        self,
        patterns: List[PatternDefinition]
    ) -> Optional[Dict[str, List[PatternDefinition]]]:
        """Cluster patterns using local LLM."""
        try:
            from esass.integrations.local_llm import get_local_llm_client

            # Prepare pattern data for LLM
            pattern_data = [
                (p.description, p.sequence, p.tags)
                for p in patterns
            ]

            # Run async clustering
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            async def _cluster():
                client = await get_local_llm_client()
                if not await client.is_available():
                    return None
                return await client.cluster_patterns_semantically(pattern_data)

            cluster_indices = loop.run_until_complete(_cluster())

            if cluster_indices is None:
                return None

            # Convert indices to pattern clusters
            clusters: Dict[str, List[PatternDefinition]] = {}
            for i, indices in enumerate(cluster_indices):
                # Name cluster based on first pattern's category
                if indices:
                    first_pattern = patterns[indices[0]]
                    # Infer cluster name from tags
                    cluster_name = self._infer_cluster_name(first_pattern)
                    clusters[cluster_name] = [patterns[idx] for idx in indices]

            logger.debug(f"LLM clustering created {len(clusters)} clusters")
            return clusters

        except ImportError:
            logger.debug("Local LLM not available for clustering")
            return None
        except Exception as e:
            logger.debug(f"LLM clustering failed: {e}")
            return None

    def _cluster_by_tags(
        self,
        patterns: List[PatternDefinition]
    ) -> Dict[str, List[PatternDefinition]]:
        """Fallback clustering by shared tags."""
        clusters: Dict[str, List[PatternDefinition]] = defaultdict(list)

        for pattern in patterns:
            # Determine primary category
            category = self._infer_cluster_name(pattern)
            clusters[category].append(pattern)

        return dict(clusters)

    def _infer_cluster_name(self, pattern: PatternDefinition) -> str:
        """Infer cluster name from pattern tags and sequence."""
        tags_lower = [t.lower() for t in pattern.tags]
        seq_str = " ".join(pattern.sequence).lower()

        if "git" in seq_str or any("git" in t for t in tags_lower):
            return "git_workflow"
        elif "test" in seq_str or "pytest" in seq_str:
            return "testing"
        elif "grep" in seq_str or "glob" in seq_str:
            return "code_search"
        elif "edit" in seq_str and "read" in seq_str:
            return "file_modification"
        elif "documentation" in seq_str or "readme" in seq_str:
            return "documentation"
        elif "config" in seq_str:
            return "configuration"
        else:
            return "general"

    def deduplicate_patterns(
        self,
        patterns: List[PatternDefinition],
        similarity_threshold: float = 0.8
    ) -> List[PatternDefinition]:
        """
        Remove duplicate/very similar patterns.

        Uses semantic clustering to identify duplicates and keeps
        the pattern with highest support from each cluster.

        Args:
            patterns: List of patterns to deduplicate
            similarity_threshold: Minimum similarity to consider duplicate

        Returns:
            Deduplicated list of patterns
        """
        if len(patterns) <= 1:
            return patterns

        # Cluster patterns
        clusters = self.cluster_patterns_semantically(patterns, use_llm=True)

        deduplicated = []
        for cluster_name, cluster_patterns in clusters.items():
            if len(cluster_patterns) == 1:
                deduplicated.append(cluster_patterns[0])
            else:
                # Keep pattern with highest support
                best = max(cluster_patterns, key=lambda p: (p.support, p.confidence))
                deduplicated.append(best)
                logger.debug(
                    f"Deduplicated {len(cluster_patterns)} patterns in '{cluster_name}' "
                    f"cluster, keeping: {best.description[:50]}"
                )

        return deduplicated

    def _detect_workflow_patterns(
        self,
        base_patterns: List[PatternDefinition]
    ) -> List[PatternDefinition]:
        """
        Detect higher-level workflow patterns from base patterns.

        Identifies:
        - Git workflows (status → add → commit → push)
        - File modification workflows (Read → Edit → Write → test)
        - Exploration workflows (Glob/Grep → Read → Read)
        """
        workflow_patterns = []

        # Define known workflow signatures
        WORKFLOWS = {
            'git_workflow': {
                'indicators': ['git_status', 'git_add', 'git_commit'],
                'min_matches': 2
            },
            'file_modification': {
                'indicators': ['Read', 'Edit', 'file_edit', 'Write'],
                'min_matches': 2
            },
            'code_exploration': {
                'indicators': ['Grep', 'Glob', 'Read', 'content_search', 'file_search'],
                'min_matches': 2
            },
            'test_driven': {
                'indicators': ['test_run', 'Edit', 'Bash'],
                'min_matches': 2
            }
        }

        for pattern in base_patterns:
            pattern_tags = set(pattern.tags)
            seq_str = ' '.join(pattern.sequence)

            for workflow_name, config in WORKFLOWS.items():
                matches = sum(
                    1 for ind in config['indicators']
                    if ind in pattern_tags or ind in seq_str
                )

                if matches >= config['min_matches']:
                    # Tag existing pattern with workflow
                    if workflow_name not in pattern.tags:
                        pattern.tags.append(workflow_name)

        return workflow_patterns


# Convenience function for CLI integration
def analyze_with_enhanced_detection(logs: List[LogEntry],
                                     granularity: str = 'medium') -> List[PatternDefinition]:
    """
    Analyze logs with enhanced pattern detection.

    Args:
        logs: List of log entries
        granularity: Detection granularity ('coarse', 'medium', 'fine')

    Returns:
        List of detected patterns with semantic enrichment
    """
    detector = EnhancedPatternDetector(
        min_support=3,
        min_confidence=0.6,
        min_stability_days=1,  # Very relaxed for initial detection
        granularity=granularity
    )
    return detector.detect_patterns(logs)
