"""
Cross-skill lineage tracker.

Manages directed graph edges between skills representing
derivation, influence, composition, and replacement relationships.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .models import LineageEdge, LineageRelation, SkillLineageSummary
from .stores import LineageStore


class LineageTracker:
    """Tracks and queries cross-skill lineage relationships."""

    def __init__(self, store: Optional[LineageStore] = None):
        self.store = store or LineageStore()

    # ---- Recording helpers ----

    def record_parent_child(
        self, parent_id: str, child_id: str, evidence: str = "", confidence: float = 1.0
    ) -> LineageEdge:
        edge = LineageEdge(
            source_skill_id=parent_id,
            target_skill_id=child_id,
            relation_type=LineageRelation.PARENT_CHILD.value,
            confidence=confidence,
            evidence=evidence,
        )
        self.store.append(edge)
        return edge

    def record_influence(
        self, influencer_id: str, influenced_id: str, evidence: str = "", confidence: float = 0.8
    ) -> LineageEdge:
        edge = LineageEdge(
            source_skill_id=influencer_id,
            target_skill_id=influenced_id,
            relation_type=LineageRelation.INFLUENCED.value,
            confidence=confidence,
            evidence=evidence,
        )
        self.store.append(edge)
        return edge

    def record_composition(
        self, component_id: str, composite_id: str, evidence: str = "", confidence: float = 1.0
    ) -> LineageEdge:
        edge = LineageEdge(
            source_skill_id=component_id,
            target_skill_id=composite_id,
            relation_type=LineageRelation.COMPOSED_INTO.value,
            confidence=confidence,
            evidence=evidence,
        )
        self.store.append(edge)
        return edge

    def record_replacement(
        self, old_id: str, new_id: str, evidence: str = "", confidence: float = 1.0
    ) -> LineageEdge:
        edge = LineageEdge(
            source_skill_id=old_id,
            target_skill_id=new_id,
            relation_type=LineageRelation.REPLACED_BY.value,
            confidence=confidence,
            evidence=evidence,
        )
        self.store.append(edge)
        return edge

    def record_unification(
        self, source_id: str, unified_id: str, evidence: str = "", confidence: float = 1.0
    ) -> LineageEdge:
        edge = LineageEdge(
            source_skill_id=source_id,
            target_skill_id=unified_id,
            relation_type=LineageRelation.UNIFIED_INTO.value,
            confidence=confidence,
            evidence=evidence,
        )
        self.store.append(edge)
        return edge

    # ---- Query helpers ----

    def get_summary(self, skill_id: str) -> SkillLineageSummary:
        """Full neighborhood graph for a skill."""
        edges = self.store.read_for_skill(skill_id)
        summary = SkillLineageSummary(skill_id=skill_id, edges=edges)

        for edge in edges:
            is_source = edge.source_skill_id == skill_id
            other = edge.target_skill_id if is_source else edge.source_skill_id

            if edge.relation_type == LineageRelation.PARENT_CHILD.value:
                if is_source:
                    summary.children.append(other)
                else:
                    summary.parents.append(other)

            elif edge.relation_type == LineageRelation.INFLUENCED.value:
                if is_source:
                    summary.influences.append(other)
                else:
                    summary.influenced_by.append(other)

            elif edge.relation_type == LineageRelation.COMPOSED_INTO.value:
                if is_source:
                    summary.composed_into.append(other)

            elif edge.relation_type == LineageRelation.REPLACED_BY.value:
                if is_source:
                    summary.replaced_by = other

            elif edge.relation_type == LineageRelation.UNIFIED_INTO.value:
                if is_source:
                    summary.unified_into = other

            elif edge.relation_type == LineageRelation.FORKED_FROM.value:
                if not is_source:
                    summary.forked_from = other

        return summary

    def get_influence_map(self, skill_id: str) -> Dict[str, List[str]]:
        """Who influenced / was influenced by a skill."""
        summary = self.get_summary(skill_id)
        return {
            "influenced_by": summary.influenced_by,
            "influences": summary.influences,
        }
