"""
Pattern storage using JSON format.

Stores detected patterns with metadata and quality metrics.
"""

from pathlib import Path
from typing import List, Optional
import json

from ..models import PatternDefinition
from ..config import get_data_dir, ESASSConfig


class PatternStore:
    """Manages pattern storage in JSON files"""

    def __init__(self, config: Optional[ESASSConfig] = None):
        # Handle both Path and ESASSConfig
        if isinstance(config, Path):
            self.data_dir = config
        else:
            self.data_dir = get_data_dir(config)
        self.patterns_dir = self.data_dir / "patterns"
        self.patterns_dir.mkdir(parents=True, exist_ok=True)

    def _get_pattern_path(self, pattern_id: str) -> Path:
        """Get file path for a specific pattern"""
        return self.patterns_dir / f"{pattern_id}.json"

    def save(self, pattern: PatternDefinition) -> None:
        """Save a pattern to storage"""
        pattern_path = self._get_pattern_path(pattern.pattern_id)
        with open(pattern_path, 'w', encoding='utf-8') as f:
            json.dump(pattern.to_dict(), f, indent=2)

    def save_batch(self, patterns: List[PatternDefinition]) -> None:
        """Save multiple patterns"""
        for pattern in patterns:
            self.save(pattern)

    def save_many(self, patterns: List[PatternDefinition]) -> None:
        """Alias for save_batch for backward compatibility"""
        self.save_batch(patterns)

    def load(self, pattern_id: str) -> Optional[PatternDefinition]:
        """Load a specific pattern by ID"""
        pattern_path = self._get_pattern_path(pattern_id)
        if not pattern_path.exists():
            return None

        with open(pattern_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return PatternDefinition.from_dict(data)

    def load_all(self) -> List[PatternDefinition]:
        """Load all patterns from storage"""
        patterns = []
        for pattern_file in sorted(self.patterns_dir.glob("*.json")):
            with open(pattern_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                patterns.append(PatternDefinition.from_dict(data))
        return patterns

    def load_candidates(self) -> List[PatternDefinition]:
        """Load only patterns marked as skill candidates"""
        all_patterns = self.load_all()
        return [p for p in all_patterns if p.skill_candidate]

    def update(self, pattern: PatternDefinition) -> None:
        """Update an existing pattern (same as save)"""
        self.save(pattern)

    def delete(self, pattern_id: str) -> bool:
        """Delete a pattern from storage"""
        pattern_path = self._get_pattern_path(pattern_id)
        if pattern_path.exists():
            pattern_path.unlink()
            return True
        return False

    def exists(self, pattern_id: str) -> bool:
        """Check if a pattern exists in storage"""
        return self._get_pattern_path(pattern_id).exists()

    def count(self) -> int:
        """Count total number of patterns"""
        return len(list(self.patterns_dir.glob("*.json")))

    def count_candidates(self) -> int:
        """Count patterns marked as skill candidates"""
        return len(self.load_candidates())

    def get_by_sequence(self, sequence: List[str]) -> List[PatternDefinition]:
        """Find patterns matching a specific sequence"""
        all_patterns = self.load_all()
        return [p for p in all_patterns if p.sequence == sequence]

    def get_high_quality(self, min_support: int = 10,
                         min_confidence: float = 0.8,
                         min_stability_days: int = 7) -> List[PatternDefinition]:
        """Get patterns meeting quality thresholds"""
        all_patterns = self.load_all()
        return [
            p for p in all_patterns
            if (p.metrics.support >= min_support and
                p.metrics.confidence >= min_confidence and
                p.metrics.stability_days >= min_stability_days)
        ]

    def clear_all(self) -> None:
        """Delete all patterns (use with caution!)"""
        for pattern_file in self.patterns_dir.glob("*.json"):
            pattern_file.unlink()

    def export_summary(self) -> dict:
        """Export summary statistics about stored patterns"""
        patterns = self.load_all()
        if not patterns:
            return {
                "total_patterns": 0,
                "skill_candidates": 0,
                "avg_support": 0,
                "avg_confidence": 0,
                "avg_stability_days": 0
            }

        candidates = [p for p in patterns if p.skill_candidate]
        return {
            "total_patterns": len(patterns),
            "skill_candidates": len(candidates),
            "avg_support": sum(p.metrics.support for p in patterns) / len(patterns),
            "avg_confidence": sum(p.metrics.confidence for p in patterns) / len(patterns),
            "avg_stability_days": sum(p.metrics.stability_days for p in patterns) / len(patterns),
            "unique_sequences": len(set(tuple(p.sequence) for p in patterns))
        }
