"""
Abstract base classes for ESASS storage layer.

Defines the contracts that all storage backends must implement,
enabling future migration from file-based to database-backed stores.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from ..models import LogEntry, PatternDefinition, SkillManifest


class LogStoreInterface(ABC):
    """Abstract interface for log entry storage."""

    @abstractmethod
    def append(self, entry: LogEntry) -> None:
        """Append a single log entry."""
        ...

    @abstractmethod
    def append_batch(self, entries: List[LogEntry]) -> None:
        """Append multiple log entries efficiently."""
        ...

    @abstractmethod
    def read_date(self, date: datetime) -> List[LogEntry]:
        """Read all log entries for a specific date."""
        ...

    @abstractmethod
    def read_date_range(self, start_date: datetime, end_date: datetime) -> List[LogEntry]:
        """Read all log entries within a date range (inclusive)."""
        ...

    @abstractmethod
    def read_all(self) -> List[LogEntry]:
        """Read all log entries."""
        ...

    @abstractmethod
    def get_session_logs(self, session_id: str) -> List[LogEntry]:
        """Get all log entries for a specific session."""
        ...

    @abstractmethod
    def count_entries(self) -> int:
        """Count total number of log entries."""
        ...

    @abstractmethod
    def get_date_range(self) -> tuple:
        """Get the date range of available logs."""
        ...

    @abstractmethod
    def get_stats(self) -> dict:
        """Get statistics about stored logs."""
        ...

    # Optional convenience methods with default implementations

    def save(self, entry: LogEntry) -> None:
        """Alias for append."""
        self.append(entry)

    def save_many(self, entries: List[LogEntry]) -> None:
        """Alias for append_batch."""
        self.append_batch(entries)

    def load_all(self) -> List[LogEntry]:
        """Alias for read_all."""
        return self.read_all()


class PatternStoreInterface(ABC):
    """Abstract interface for pattern storage."""

    @abstractmethod
    def save(self, pattern: PatternDefinition) -> None:
        """Save a pattern to storage."""
        ...

    @abstractmethod
    def save_batch(self, patterns: List[PatternDefinition]) -> None:
        """Save multiple patterns."""
        ...

    @abstractmethod
    def load(self, pattern_id: str) -> Optional[PatternDefinition]:
        """Load a specific pattern by ID."""
        ...

    @abstractmethod
    def load_all(self) -> List[PatternDefinition]:
        """Load all patterns from storage."""
        ...

    @abstractmethod
    def load_candidates(self) -> List[PatternDefinition]:
        """Load only patterns marked as skill candidates."""
        ...

    @abstractmethod
    def delete(self, pattern_id: str) -> bool:
        """Delete a pattern from storage."""
        ...

    @abstractmethod
    def exists(self, pattern_id: str) -> bool:
        """Check if a pattern exists in storage."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count total number of patterns."""
        ...

    @abstractmethod
    def get_high_quality(self, min_support: int = 10,
                         min_confidence: float = 0.8,
                         min_stability_days: int = 7) -> List[PatternDefinition]:
        """Get patterns meeting quality thresholds."""
        ...

    @abstractmethod
    def get_by_sequence(self, sequence: List[str]) -> List[PatternDefinition]:
        """Find patterns matching a specific sequence."""
        ...

    @abstractmethod
    def get_stats(self) -> dict:
        """Get statistics about stored patterns."""
        ...

    # Convenience aliases

    def save_many(self, patterns: List[PatternDefinition]) -> None:
        """Alias for save_batch."""
        self.save_batch(patterns)

    def update(self, pattern: PatternDefinition) -> None:
        """Update an existing pattern (same as save)."""
        self.save(pattern)


class SkillStoreInterface(ABC):
    """Abstract interface for skill manifest storage."""

    @abstractmethod
    def save(self, skill: SkillManifest) -> None:
        """Save a skill manifest to storage."""
        ...

    @abstractmethod
    def save_batch(self, skills: List[SkillManifest]) -> None:
        """Save multiple skill manifests."""
        ...

    @abstractmethod
    def load(self, skill_id: str) -> Optional[SkillManifest]:
        """Load a specific skill by ID."""
        ...

    @abstractmethod
    def load_all(self) -> List[SkillManifest]:
        """Load all skills from storage."""
        ...

    @abstractmethod
    def load_by_status(self, status: str) -> List[SkillManifest]:
        """Load skills with a specific validation status."""
        ...

    @abstractmethod
    def delete(self, skill_id: str) -> bool:
        """Delete a skill from storage."""
        ...

    @abstractmethod
    def exists(self, skill_id: str) -> bool:
        """Check if a skill exists in storage."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count total number of skills."""
        ...

    @abstractmethod
    def get_by_pattern(self, pattern_id: str) -> List[SkillManifest]:
        """Find skills generated from a specific pattern."""
        ...

    @abstractmethod
    def get_by_capability(self, capability: str) -> List[SkillManifest]:
        """Find skills with a specific capability."""
        ...

    @abstractmethod
    def get_stats(self) -> dict:
        """Get statistics about stored skills."""
        ...

    # Convenience aliases

    def save_many(self, skills: List[SkillManifest]) -> None:
        """Alias for save_batch."""
        self.save_batch(skills)

    def update(self, skill: SkillManifest) -> None:
        """Update an existing skill (same as save)."""
        self.save(skill)

    def load_pending(self) -> List[SkillManifest]:
        """Load skills pending validation."""
        return self.load_by_status("pending")

    def load_validated(self) -> List[SkillManifest]:
        """Load validated skills."""
        return self.load_by_status("validated")
