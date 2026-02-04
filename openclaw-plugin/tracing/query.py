"""
Tracing query API.

Provides aggregated views combining usage, evolution, and lineage data.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .evolution_tracker import EvolutionHistoryTracker
from .lineage_tracker import LineageTracker
from .models import UsageAggregation
from .stores import EvolutionStore, LineageStore, UsageStore
from .usage_tracker import UsageAnalyticsTracker


class TracingQueryAPI:
    """High-level query interface over all tracing subsystems."""

    def __init__(
        self,
        usage_store: Optional[UsageStore] = None,
        evolution_store: Optional[EvolutionStore] = None,
        lineage_store: Optional[LineageStore] = None,
    ):
        self.usage_tracker = UsageAnalyticsTracker(store=usage_store or UsageStore())
        self.evolution_tracker = EvolutionHistoryTracker(store=evolution_store or EvolutionStore())
        self.lineage_tracker = LineageTracker(store=lineage_store or LineageStore())

    def skill_report(self, skill_id: str) -> Dict[str, Any]:
        """Combined usage + evolution + lineage for one skill."""
        usage = self.usage_tracker.get_skill_stats(skill_id)
        history = self.evolution_tracker.get_history(skill_id)
        lineage = self.lineage_tracker.get_summary(skill_id)

        return {
            "skill_id": skill_id,
            "usage": usage.to_dict(),
            "evolution_events": [e.to_dict() for e in history],
            "lineage": lineage.to_dict(),
        }

    def top_skills(
        self,
        limit: int = 10,
        window_start: Optional[str] = None,
        window_end: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Most used skills over window, sorted by activation count."""
        all_stats = self.usage_tracker.get_all_skill_stats()
        items = sorted(
            all_stats.values(),
            key=lambda a: a.activation_count + a.completion_count,
            reverse=True,
        )
        return [s.to_dict() for s in items[:limit]]

    def stale_skills(
        self,
        min_days_inactive: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Deprecation candidates: skills with no recent usage.
        Returns skills whose latest usage record is older than min_days_inactive.
        """
        from datetime import datetime, timedelta

        cutoff = (datetime.utcnow() - timedelta(days=min_days_inactive)).isoformat()
        all_records = self.usage_tracker.store.read_all()

        # Build latest-timestamp-per-skill map
        latest: Dict[str, str] = {}
        name_map: Dict[str, str] = {}
        for r in all_records:
            if r.skill_id not in latest or r.timestamp > latest[r.skill_id]:
                latest[r.skill_id] = r.timestamp
                name_map[r.skill_id] = r.skill_name

        stale = []
        for sid, ts in latest.items():
            if ts < cutoff:
                stale.append({
                    "skill_id": sid,
                    "skill_name": name_map.get(sid, ""),
                    "last_used": ts,
                })
        return stale

    def evolution_timeline(
        self,
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        """All evolution events in a date range (YYYY-MM-DD)."""
        events = self.evolution_tracker.store.read_date_range(start_date, end_date)
        return [e.to_dict() for e in events]
