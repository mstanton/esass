"""
Usage analytics tracker.

Records skill activations/completions and computes aggregations.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from .models import UsageAggregation, UsageRecord
from .stores import UsageStore


class UsageAnalyticsTracker:
    """Tracks skill usage events and provides aggregated statistics."""

    def __init__(self, store: Optional[UsageStore] = None):
        self.store = store or UsageStore()

    def record_activation(
        self,
        skill_id: str,
        skill_name: str,
        session_id: str,
        user_id: str = "",
        agent_id: str = "",
        trigger_context: str = "",
        anonymize: bool = True,
    ) -> UsageRecord:
        """Create a UsageRecord on skill activation."""
        user_hash = UsageRecord.anonymize_user(user_id) if anonymize and user_id else user_id
        record = UsageRecord(
            skill_id=skill_id,
            skill_name=skill_name,
            session_id=session_id,
            user_hash=user_hash,
            agent_id=agent_id,
            trigger_context=trigger_context,
            outcome="pending",
        )
        self.store.append(record)
        return record

    def record_completion(
        self,
        skill_id: str,
        skill_name: str,
        session_id: str,
        success: bool = True,
        duration_ms: float = 0.0,
        error_type: Optional[str] = None,
        user_id: str = "",
        agent_id: str = "",
        anonymize: bool = True,
    ) -> UsageRecord:
        """Append a completion record (JSONL is append-only)."""
        user_hash = UsageRecord.anonymize_user(user_id) if anonymize and user_id else user_id
        record = UsageRecord(
            skill_id=skill_id,
            skill_name=skill_name,
            session_id=session_id,
            user_hash=user_hash,
            agent_id=agent_id,
            outcome="success" if success else "failure",
            duration_ms=duration_ms,
            error_type=error_type,
        )
        self.store.append(record)
        return record

    def get_skill_stats(
        self,
        skill_id: str,
        window_start: Optional[str] = None,
        window_end: Optional[str] = None,
    ) -> UsageAggregation:
        """Compute UsageAggregation over rolling window."""
        records = self.store.read_for_skill(skill_id)

        if window_start:
            records = [r for r in records if r.timestamp >= window_start]
        if window_end:
            records = [r for r in records if r.timestamp <= window_end]

        activations = [r for r in records if r.outcome == "pending"]
        completions = [r for r in records if r.outcome in ("success", "failure")]
        successes = [r for r in completions if r.outcome == "success"]
        failures = [r for r in completions if r.outcome == "failure"]

        durations = [r.duration_ms for r in completions if r.duration_ms > 0]
        avg_dur = sum(durations) / len(durations) if durations else 0.0

        sessions = {r.session_id for r in records if r.session_id}
        users = {r.user_hash for r in records if r.user_hash}

        skill_name = records[0].skill_name if records else ""

        return UsageAggregation(
            skill_id=skill_id,
            skill_name=skill_name,
            window_start=window_start or "",
            window_end=window_end or "",
            activation_count=len(activations),
            completion_count=len(completions),
            success_count=len(successes),
            failure_count=len(failures),
            avg_duration_ms=avg_dur,
            unique_sessions=len(sessions),
            unique_users=len(users),
        )

    def get_all_skill_stats(self) -> Dict[str, UsageAggregation]:
        """Get aggregated stats for every skill that has records."""
        all_records = self.store.read_all()
        skill_ids = {r.skill_id for r in all_records}
        return {sid: self.get_skill_stats(sid) for sid in skill_ids}
