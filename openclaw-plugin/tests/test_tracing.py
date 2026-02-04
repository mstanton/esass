"""
Tests for the tracing subsystem (~18 tests).
"""

import pytest

from openclaw_plugin.tracing.models import (
    UsageRecord,
    UsageAggregation,
    EvolutionEvent,
    EvolutionEventType,
    LineageEdge,
    LineageRelation,
    SkillLineageSummary,
)
from openclaw_plugin.tracing.stores import UsageStore, EvolutionStore, LineageStore
from openclaw_plugin.tracing.usage_tracker import UsageAnalyticsTracker
from openclaw_plugin.tracing.evolution_tracker import EvolutionHistoryTracker
from openclaw_plugin.tracing.lineage_tracker import LineageTracker
from openclaw_plugin.tracing.query import TracingQueryAPI


# ---- Models ----

class TestUsageRecord:
    def test_anonymize_user(self):
        h = UsageRecord.anonymize_user("user123")
        assert len(h) == 16
        assert h == UsageRecord.anonymize_user("user123")  # deterministic
        assert h != UsageRecord.anonymize_user("user456")

    def test_serialization_roundtrip(self):
        r = UsageRecord(skill_id="s1", skill_name="test", session_id="sess1", outcome="success")
        d = r.to_dict()
        r2 = UsageRecord.from_dict(d)
        assert r2.skill_id == "s1"
        assert r2.outcome == "success"


class TestEvolutionEvent:
    def test_defaults(self):
        e = EvolutionEvent(skill_id="s1")
        assert e.event_type == EvolutionEventType.CREATED.value
        assert e.skill_id == "s1"

    def test_serialization_roundtrip(self):
        e = EvolutionEvent(skill_id="s1", from_version="0.1.0", to_version="0.2.0")
        d = e.to_dict()
        e2 = EvolutionEvent.from_dict(d)
        assert e2.from_version == "0.1.0"


class TestLineageEdge:
    def test_defaults(self):
        edge = LineageEdge(source_skill_id="a", target_skill_id="b")
        assert edge.relation_type == LineageRelation.PARENT_CHILD.value
        assert edge.confidence == 1.0

    def test_serialization(self):
        edge = LineageEdge(source_skill_id="a", target_skill_id="b", evidence="test")
        d = edge.to_dict()
        edge2 = LineageEdge.from_dict(d)
        assert edge2.evidence == "test"


# ---- Stores ----

class TestUsageStore:
    def test_append_and_read(self, tmp_data_dir):
        store = UsageStore(base_dir=tmp_data_dir["usage"])
        r = UsageRecord(skill_id="s1", skill_name="test", timestamp="2026-02-03T12:00:00")
        store.append(r)
        records = store.read_date("20260203")
        assert len(records) == 1
        assert records[0].skill_id == "s1"

    def test_read_for_skill(self, tmp_data_dir):
        store = UsageStore(base_dir=tmp_data_dir["usage"])
        store.append(UsageRecord(skill_id="s1", timestamp="2026-02-03T12:00:00"))
        store.append(UsageRecord(skill_id="s2", timestamp="2026-02-03T13:00:00"))
        assert len(store.read_for_skill("s1")) == 1

    def test_read_empty(self, tmp_data_dir):
        store = UsageStore(base_dir=tmp_data_dir["usage"])
        assert store.read_date("20260101") == []


class TestEvolutionStore:
    def test_append_and_read(self, tmp_data_dir):
        store = EvolutionStore(base_dir=tmp_data_dir["evolution"])
        e = EvolutionEvent(skill_id="s1", event_type="created")
        store.append(e)
        events = store.read_for_skill("s1")
        assert len(events) == 1

    def test_read_all(self, tmp_data_dir):
        store = EvolutionStore(base_dir=tmp_data_dir["evolution"])
        store.append(EvolutionEvent(skill_id="s1"))
        store.append(EvolutionEvent(skill_id="s2"))
        assert len(store.read_all()) == 2


class TestLineageStore:
    def test_append_and_read(self, tmp_data_dir):
        store = LineageStore(base_dir=tmp_data_dir["lineage"])
        edge = LineageEdge(source_skill_id="a", target_skill_id="b")
        store.append(edge)
        edges = store.read_all()
        assert len(edges) == 1

    def test_read_for_skill(self, tmp_data_dir):
        store = LineageStore(base_dir=tmp_data_dir["lineage"])
        store.append(LineageEdge(source_skill_id="a", target_skill_id="b"))
        store.append(LineageEdge(source_skill_id="c", target_skill_id="d"))
        assert len(store.read_for_skill("a")) == 1
        assert len(store.read_for_skill("d")) == 1


# ---- Trackers ----

class TestUsageAnalyticsTracker:
    def test_record_activation_and_stats(self, tmp_data_dir):
        store = UsageStore(base_dir=tmp_data_dir["usage"])
        tracker = UsageAnalyticsTracker(store=store)
        tracker.record_activation(skill_id="s1", skill_name="test", session_id="sess1", user_id="u1")
        tracker.record_completion(skill_id="s1", skill_name="test", session_id="sess1", success=True, duration_ms=100)
        stats = tracker.get_skill_stats("s1")
        assert stats.activation_count == 1
        assert stats.success_count == 1
        assert stats.avg_duration_ms == 100.0


class TestEvolutionHistoryTracker:
    def test_record_and_history(self, tmp_data_dir):
        store = EvolutionStore(base_dir=tmp_data_dir["evolution"])
        tracker = EvolutionHistoryTracker(store=store)
        tracker.record_creation(skill_id="s1", version="0.1.0", rationale="genesis")
        tracker.record_version_bump(skill_id="s1", from_version="0.1.0", to_version="0.2.0", changes={"description": "updated"})
        history = tracker.get_history("s1")
        assert len(history) == 2
        assert history[0].event_type == "created"
        assert history[1].event_type == "version_bump"

    def test_diff_versions(self, tmp_data_dir):
        store = EvolutionStore(base_dir=tmp_data_dir["evolution"])
        tracker = EvolutionHistoryTracker(store=store)
        tracker.record_version_bump(skill_id="s1", from_version="0.1.0", to_version="0.2.0", changes={"a": 1})
        tracker.record_version_bump(skill_id="s1", from_version="0.2.0", to_version="0.3.0", changes={"b": 2})
        diff = tracker.diff_versions("s1", "0.1.0", "0.3.0")
        assert diff == {"a": 1, "b": 2}


class TestLineageTracker:
    def test_record_and_summary(self, tmp_data_dir):
        store = LineageStore(base_dir=tmp_data_dir["lineage"])
        tracker = LineageTracker(store=store)
        tracker.record_parent_child("parent", "child")
        tracker.record_influence("influencer", "child")
        summary = tracker.get_summary("child")
        assert "parent" in summary.parents
        assert "influencer" in summary.influenced_by

    def test_get_influence_map(self, tmp_data_dir):
        store = LineageStore(base_dir=tmp_data_dir["lineage"])
        tracker = LineageTracker(store=store)
        tracker.record_influence("a", "b")
        imap = tracker.get_influence_map("b")
        assert "a" in imap["influenced_by"]


# ---- Query API ----

class TestTracingQueryAPI:
    def test_skill_report(self, tmp_data_dir):
        api = TracingQueryAPI(
            usage_store=UsageStore(base_dir=tmp_data_dir["usage"]),
            evolution_store=EvolutionStore(base_dir=tmp_data_dir["evolution"]),
            lineage_store=LineageStore(base_dir=tmp_data_dir["lineage"]),
        )
        api.usage_tracker.record_activation(skill_id="s1", skill_name="test", session_id="sess1")
        api.evolution_tracker.record_creation(skill_id="s1", version="0.1.0")
        report = api.skill_report("s1")
        assert report["skill_id"] == "s1"
        assert "usage" in report
        assert "evolution_events" in report
        assert len(report["evolution_events"]) == 1

    def test_top_skills(self, tmp_data_dir):
        api = TracingQueryAPI(
            usage_store=UsageStore(base_dir=tmp_data_dir["usage"]),
            evolution_store=EvolutionStore(base_dir=tmp_data_dir["evolution"]),
            lineage_store=LineageStore(base_dir=tmp_data_dir["lineage"]),
        )
        for i in range(5):
            api.usage_tracker.record_activation(skill_id="s1", skill_name="pop", session_id=f"sess{i}")
        api.usage_tracker.record_activation(skill_id="s2", skill_name="less_pop", session_id="sess0")
        top = api.top_skills(limit=1)
        assert len(top) == 1
        assert top[0]["skill_id"] == "s1"
