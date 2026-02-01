"""
Pattern detector using temporal sequence mining.

Implements simplified PrefixSpan algorithm to detect recurring event sequences.
"""

from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Set
from uuid import uuid4

from esass_prototype.models import LogEntry, PatternDefinition, PatternType


class TemporalPatternDetector:
    """
    Detect recurring temporal sequences in log data.

    Simplified from §5.1.1 of specification using frequency analysis.
    """

    def __init__(
        self,
        min_support: int = 10,
        min_confidence: float = 0.8,
        min_stability_days: int = 7,
        max_gap_seconds: int = 300,
        min_sequence_length: int = 2,
        max_sequence_length: int = 5
    ):
        """
        Initialize pattern detector.

        Args:
            min_support: Minimum number of instances for a pattern
            min_confidence: Minimum reliability (0.0-1.0)
            min_stability_days: Minimum days pattern must be stable
            max_gap_seconds: Maximum time between events in sequence
            min_sequence_length: Minimum events in a sequence
            max_sequence_length: Maximum events in a sequence
        """
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_stability_days = min_stability_days
        self.max_gap_seconds = max_gap_seconds
        self.min_sequence_length = min_sequence_length
        self.max_sequence_length = max_sequence_length

    def detect_patterns(self, logs: List[LogEntry]) -> List[PatternDefinition]:
        """
        Find recurring event sequences.

        Args:
            logs: List of log entries to analyze

        Returns:
            List of detected PatternDefinition objects
        """
        if not logs:
            return []

        # Step 1: Group by session
        sessions = self._group_by_session(logs)

        # Step 2: Extract event sequences from sessions
        sequences = [self._extract_sequence(session) for session in sessions.values()]

        # Step 3: Mine frequent subsequences
        frequent_sequences = self._mine_frequent_sequences(sequences)

        # Step 4: Calculate pattern metrics and create definitions
        patterns = []
        for seq, support in frequent_sequences.items():
            if support >= self.min_support:
                pattern = self._create_pattern(seq, support, logs)
                if pattern and pattern.confidence >= self.min_confidence:
                    patterns.append(pattern)

        # Sort by support (descending)
        patterns.sort(key=lambda p: p.support, reverse=True)

        return patterns

    def _group_by_session(self, logs: List[LogEntry]) -> Dict[str, List[LogEntry]]:
        """
        Group log entries by session_id.

        Args:
            logs: List of log entries

        Returns:
            Dictionary mapping session_id to list of entries
        """
        sessions = defaultdict(list)
        for entry in logs:
            if entry.session_id:
                sessions[entry.session_id].append(entry)
        return dict(sessions)

    def _extract_sequence(self, session: List[LogEntry]) -> List[str]:
        """
        Extract event type sequence from session.

        Args:
            session: List of log entries in a session

        Returns:
            List of event keys (type:tags)
        """
        # Sort by timestamp
        sorted_session = sorted(session, key=lambda e: e.timestamp)

        # Build sequence with event type and tags
        sequence = []
        for entry in sorted_session:
            # Create event key: "event_type:tag1,tag2"
            tags_str = ','.join(sorted(entry.tags)) if entry.tags else "none"
            event_key = f"{entry.event_type}:{tags_str}"
            sequence.append(event_key)

        return sequence

    def _mine_frequent_sequences(
        self,
        sequences: List[List[str]]
    ) -> Dict[Tuple[str, ...], int]:
        """
        Find subsequences that appear frequently.

        Args:
            sequences: List of event sequences

        Returns:
            Dictionary mapping subsequence tuple to occurrence count
        """
        subsequence_counts = Counter()

        # Extract all subsequences of length min_seq to max_seq
        for seq in sequences:
            for length in range(self.min_sequence_length, min(self.max_sequence_length + 1, len(seq) + 1)):
                for i in range(len(seq) - length + 1):
                    subseq = tuple(seq[i:i+length])
                    subsequence_counts[subseq] += 1

        return dict(subsequence_counts)

    def _create_pattern(
        self,
        sequence: Tuple[str, ...],
        support: int,
        logs: List[LogEntry]
    ) -> PatternDefinition:
        """
        Create PatternDefinition from sequence.

        Args:
            sequence: Event sequence tuple
            support: Number of occurrences
            logs: All log entries for context

        Returns:
            PatternDefinition object or None if invalid
        """
        # Find exemplar log entries
        exemplars = self._find_exemplars(sequence, logs, limit=5)

        if not exemplars:
            return None

        # Calculate stability (how many days has this pattern appeared)
        stability_days = self._calculate_stability(sequence, logs)

        # Generate description
        description = self._generate_description(sequence)

        # Calculate confidence (what % of sessions with first event have full sequence)
        confidence = self._calculate_confidence(sequence, logs)

        # Determine if this is a skill candidate
        skill_candidate = (
            support >= self.min_support and
            confidence >= self.min_confidence and
            stability_days >= self.min_stability_days
        )

        # Extract tags from sequence
        tags = self._extract_tags(sequence)

        # Get date range
        first_seen, last_seen = self._get_date_range(sequence, logs)

        pattern = PatternDefinition(
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

        return pattern

    def _calculate_confidence(
        self,
        sequence: Tuple[str, ...],
        logs: List[LogEntry]
    ) -> float:
        """
        Calculate pattern confidence.

        Confidence = P(full sequence | first event)

        Args:
            sequence: Event sequence
            logs: All log entries

        Returns:
            Confidence value (0.0-1.0)
        """
        sessions = self._group_by_session(logs)

        sessions_with_first = 0
        sessions_with_full = 0

        for session in sessions.values():
            seq = self._extract_sequence(session)
            seq_tuple = tuple(seq)

            # Check if session has first event
            if len(seq_tuple) > 0 and seq_tuple[0] == sequence[0]:
                sessions_with_first += 1

                # Check if full sequence appears
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
        """
        Check if needle is a subsequence of haystack.

        Args:
            haystack: Full sequence
            needle: Subsequence to find

        Returns:
            True if needle is found in haystack
        """
        if len(needle) > len(haystack):
            return False

        for i in range(len(haystack) - len(needle) + 1):
            if haystack[i:i+len(needle)] == needle:
                return True

        return False

    def _calculate_stability(
        self,
        sequence: Tuple[str, ...],
        logs: List[LogEntry]
    ) -> int:
        """
        Calculate how many days this pattern has appeared.

        Args:
            sequence: Event sequence
            logs: All log entries

        Returns:
            Number of days (span from first to last appearance)
        """
        # Group by date
        dates_with_pattern = set()

        sessions = self._group_by_session(logs)
        for session in sessions.values():
            seq = self._extract_sequence(session)
            if self._sequence_contains(tuple(seq), sequence):
                # Extract date from first entry
                if session:
                    date = datetime.fromisoformat(session[0].timestamp).date()
                    dates_with_pattern.add(date)

        if not dates_with_pattern:
            return 0

        # Calculate span from first to last appearance
        min_date = min(dates_with_pattern)
        max_date = max(dates_with_pattern)
        return (max_date - min_date).days + 1

    def _find_exemplars(
        self,
        sequence: Tuple[str, ...],
        logs: List[LogEntry],
        limit: int
    ) -> List[LogEntry]:
        """
        Find example log entries that demonstrate this pattern.

        Args:
            sequence: Event sequence
            logs: All log entries
            limit: Maximum number of exemplars

        Returns:
            List of LogEntry objects
        """
        exemplars = []
        sessions = self._group_by_session(logs)

        for session in sessions.values():
            seq = self._extract_sequence(session)
            if self._sequence_contains(tuple(seq), sequence):
                # Take first entry from this session
                if session:
                    exemplars.append(sorted(session, key=lambda e: e.timestamp)[0])
                    if len(exemplars) >= limit:
                        break

        return exemplars

    def _generate_description(self, sequence: Tuple[str, ...]) -> str:
        """
        Generate human-readable description.

        Args:
            sequence: Event sequence

        Returns:
            Description string
        """
        # Simplify event keys
        steps = []
        for event_key in sequence:
            event_type, tags = event_key.split(':', 1)
            # Take first 3 tags if many
            tag_list = tags.split(',')
            if len(tag_list) > 3:
                tag_list = tag_list[:3] + ['...']
            tags_display = ','.join(tag_list)
            steps.append(f"{event_type}({tags_display})")

        return " ->".join(steps)

    def _extract_tags(self, sequence: Tuple[str, ...]) -> List[str]:
        """
        Extract unique tags from sequence.

        Args:
            sequence: Event sequence

        Returns:
            List of unique tags
        """
        all_tags = []
        for event_key in sequence:
            _, tags_str = event_key.split(':', 1)
            if tags_str != "none":
                all_tags.extend(tags_str.split(','))

        # Return unique tags
        return list(set(all_tags))

    def _get_date_range(
        self,
        sequence: Tuple[str, ...],
        logs: List[LogEntry]
    ) -> Tuple[str, str]:
        """
        Get first and last seen dates for pattern.

        Args:
            sequence: Event sequence
            logs: All log entries

        Returns:
            Tuple of (first_seen, last_seen) as ISO8601 strings
        """
        timestamps = []

        sessions = self._group_by_session(logs)
        for session in sessions.values():
            seq = self._extract_sequence(session)
            if self._sequence_contains(tuple(seq), sequence):
                if session:
                    timestamps.append(session[0].timestamp)

        if not timestamps:
            now = datetime.utcnow().isoformat()
            return now, now

        timestamps.sort()
        return timestamps[0], timestamps[-1]
