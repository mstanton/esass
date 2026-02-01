"""
Pattern storage using JSON files.

Provides storage and retrieval for detected patterns.
"""

from pathlib import Path
from typing import List, Optional
import json

from esass_prototype.models import PatternDefinition


class PatternStore:
    """
    Storage for pattern definitions using JSON files.

    Each pattern is stored in its own file for easy inspection.
    """

    def __init__(self, data_dir: Path):
        """
        Initialize pattern store.

        Args:
            data_dir: Base directory for data storage
        """
        self.data_dir = Path(data_dir)
        self.patterns_dir = self.data_dir / "patterns"
        self.patterns_dir.mkdir(parents=True, exist_ok=True)

    def save(self, pattern: PatternDefinition):
        """
        Save a pattern definition.

        Args:
            pattern: PatternDefinition to save
        """
        filename = f"pattern_{pattern.pattern_id[:8]}.json"
        filepath = self.patterns_dir / filename

        with open(filepath, 'w') as f:
            f.write(pattern.to_json())

    def save_many(self, patterns: List[PatternDefinition]):
        """
        Save multiple patterns.

        Args:
            patterns: List of PatternDefinition objects
        """
        for pattern in patterns:
            self.save(pattern)

    def load(self, pattern_id: str) -> Optional[PatternDefinition]:
        """
        Load a specific pattern by ID.

        Args:
            pattern_id: Pattern ID to load

        Returns:
            PatternDefinition if found, None otherwise
        """
        # Try short ID (first 8 chars)
        filename = f"pattern_{pattern_id[:8]}.json"
        filepath = self.patterns_dir / filename

        if not filepath.exists():
            return None

        with open(filepath, 'r') as f:
            return PatternDefinition.from_json(f.read())

    def load_all(self) -> List[PatternDefinition]:
        """
        Load all patterns.

        Returns:
            List of all PatternDefinition objects
        """
        patterns = []

        for pattern_file in self.patterns_dir.glob("pattern_*.json"):
            with open(pattern_file, 'r') as f:
                patterns.append(PatternDefinition.from_json(f.read()))

        # Sort by created_at
        patterns.sort(key=lambda p: p.created_at, reverse=True)

        return patterns

    def load_candidates(self) -> List[PatternDefinition]:
        """
        Load only patterns that are skill candidates.

        Returns:
            List of PatternDefinition objects where skill_candidate=True
        """
        all_patterns = self.load_all()
        return [p for p in all_patterns if p.skill_candidate]

    def delete(self, pattern_id: str) -> bool:
        """
        Delete a pattern.

        Args:
            pattern_id: Pattern ID to delete

        Returns:
            True if deleted, False if not found
        """
        filename = f"pattern_{pattern_id[:8]}.json"
        filepath = self.patterns_dir / filename

        if filepath.exists():
            filepath.unlink()
            return True

        return False

    def get_stats(self) -> dict:
        """
        Get pattern storage statistics.

        Returns:
            Dictionary with stats
        """
        all_patterns = self.load_all()

        if not all_patterns:
            return {
                "total_patterns": 0,
                "skill_candidates": 0,
                "by_type": {}
            }

        by_type = {}
        for pattern in all_patterns:
            ptype = pattern.pattern_type
            by_type[ptype] = by_type.get(ptype, 0) + 1

        return {
            "total_patterns": len(all_patterns),
            "skill_candidates": len([p for p in all_patterns if p.skill_candidate]),
            "by_type": by_type,
            "avg_support": sum(p.support for p in all_patterns) / len(all_patterns),
            "avg_confidence": sum(p.confidence for p in all_patterns) / len(all_patterns)
        }
