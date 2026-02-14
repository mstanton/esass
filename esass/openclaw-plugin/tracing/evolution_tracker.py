"""
Evolution history tracker.

Records skill lifecycle events: creation, version bumps, merges,
unifications, and deprecations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import EvolutionEvent, EvolutionEventType
from .stores import EvolutionStore


class EvolutionHistoryTracker:
    """Tracks skill evolution lifecycle events."""

    def __init__(self, store: Optional[EvolutionStore] = None):
        self.store = store or EvolutionStore()

    def record_creation(
        self,
        skill_id: str,
        version: str = "0.1.0",
        rationale: str = "",
        triggered_by: str = "",
        related_pattern_ids: Optional[List[str]] = None,
    ) -> EvolutionEvent:
        """Record initial skill genesis."""
        event = EvolutionEvent(
            skill_id=skill_id,
            event_type=EvolutionEventType.CREATED.value,
            to_version=version,
            rationale=rationale,
            triggered_by=triggered_by,
            related_pattern_ids=related_pattern_ids or [],
        )
        self.store.append(event)
        return event

    def record_version_bump(
        self,
        skill_id: str,
        from_version: str,
        to_version: str,
        changes: Optional[Dict[str, Any]] = None,
        rationale: str = "",
        triggered_by: str = "",
    ) -> EvolutionEvent:
        """Record a version change with field-level diffs."""
        event = EvolutionEvent(
            skill_id=skill_id,
            event_type=EvolutionEventType.VERSION_BUMP.value,
            from_version=from_version,
            to_version=to_version,
            changes=changes or {},
            rationale=rationale,
            triggered_by=triggered_by,
        )
        self.store.append(event)
        return event

    def record_unification(
        self,
        skill_id: str,
        source_skill_ids: List[str],
        version: str = "1.0.0",
        rationale: str = "",
        triggered_by: str = "",
    ) -> EvolutionEvent:
        """Record a skill merge / unification event."""
        event = EvolutionEvent(
            skill_id=skill_id,
            event_type=EvolutionEventType.UNIFICATION.value,
            to_version=version,
            rationale=rationale,
            triggered_by=triggered_by,
            related_skill_ids=source_skill_ids,
        )
        self.store.append(event)
        return event

    def record_deprecation(
        self,
        skill_id: str,
        replacement_skill_id: str = "",
        rationale: str = "",
        triggered_by: str = "",
    ) -> EvolutionEvent:
        """Record skill deprecation with optional replacement link."""
        event = EvolutionEvent(
            skill_id=skill_id,
            event_type=EvolutionEventType.DEPRECATION.value,
            rationale=rationale,
            triggered_by=triggered_by,
            related_skill_ids=[replacement_skill_id] if replacement_skill_id else [],
        )
        self.store.append(event)
        return event

    def get_history(self, skill_id: str) -> List[EvolutionEvent]:
        """Ordered timeline for a skill."""
        return self.store.read_for_skill(skill_id)

    def diff_versions(
        self,
        skill_id: str,
        from_version: str,
        to_version: str,
    ) -> Dict[str, Any]:
        """Accumulated changes between two versions."""
        history = self.get_history(skill_id)
        accumulated: Dict[str, Any] = {}
        in_range = False
        for evt in history:
            if evt.from_version == from_version:
                in_range = True
            if in_range and evt.changes:
                accumulated.update(evt.changes)
            if evt.to_version == to_version:
                break
        return accumulated
