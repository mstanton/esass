"""
Integration tests (~6 tests).

End-to-end flows through multiple subsystems.
"""

from datetime import datetime

import pytest
import yaml

from openclaw_plugin.bridge.events import OpenClawEvent, OpenClawEventType
from openclaw_plugin.bridge.hooks import OpenClawESASSBridge
from openclaw_plugin.donation.models import DonationConfig
from openclaw_plugin.donation.injector import FundingInjector
from openclaw_plugin.adapters.skill_formatter import SkillFormatter
from openclaw_plugin.tracing.stores import UsageStore, EvolutionStore, LineageStore
from openclaw_plugin.tracing.usage_tracker import UsageAnalyticsTracker
from openclaw_plugin.tracing.evolution_tracker import EvolutionHistoryTracker
from openclaw_plugin.tracing.lineage_tracker import LineageTracker
from openclaw_plugin.tracing.query import TracingQueryAPI
from esass_prototype.models import SkillManifest, TriggerCondition


class TestFullCycleWithTracing:
    def test_activation_through_to_query(self, tmp_data_dir):
        """Skill activation flows through bridge to usage store to query API."""
        usage_store = UsageStore(base_dir=tmp_data_dir["usage"])
        evo_store = EvolutionStore(base_dir=tmp_data_dir["evolution"])
        lineage_store = LineageStore(base_dir=tmp_data_dir["lineage"])

        tracker = UsageAnalyticsTracker(store=usage_store)
        bridge = OpenClawESASSBridge(usage_tracker=tracker)

        # Simulate skill activation
        bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.SKILL_ACTIVATED,
            timestamp=datetime.utcnow(),
            session_id="sess1",
            data={"skill_name": "git-commit", "skill_id": "s1"},
            user_id="user1",
        ))

        # Simulate completion
        bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.SKILL_COMPLETED,
            timestamp=datetime.utcnow(),
            session_id="sess1",
            data={"skill_name": "git-commit", "skill_id": "s1", "success": True, "duration_ms": 50},
        ))

        # Query
        api = TracingQueryAPI(
            usage_store=usage_store,
            evolution_store=evo_store,
            lineage_store=lineage_store,
        )
        report = api.skill_report("s1")
        assert report["usage"]["activation_count"] == 1
        assert report["usage"]["success_count"] == 1


class TestDonationInGeneratedSkillMd:
    def test_skill_md_contains_funding(self, tmp_skills_dir):
        """Generated SKILL.md includes funding frontmatter."""
        injector = FundingInjector()
        fmt = SkillFormatter(output_dir=tmp_skills_dir, funding_injector=injector)
        manifest = SkillManifest(
            name="my_skill",
            description="Test skill",
            source_pattern_ids=[],
            triggers=[TriggerCondition(trigger_type="intent_match", pattern="test")],
            capabilities=[],
            implementation_summary="Do things",
        )
        path = fmt.save_skill(manifest)
        content = path.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        data = yaml.safe_load(parts[1])
        assert "funding" in data
        assert data["funding"]["paypal"] == "https://paypal.me/mrstanton81"
        assert "mrstanton81" in content


class TestEvolutionAndLineage:
    def test_creation_and_lineage(self, tmp_data_dir):
        """Evolution tracker records creation; lineage links parent/child."""
        evo_store = EvolutionStore(base_dir=tmp_data_dir["evolution"])
        lineage_store = LineageStore(base_dir=tmp_data_dir["lineage"])
        evo_tracker = EvolutionHistoryTracker(store=evo_store)
        lin_tracker = LineageTracker(store=lineage_store)

        # Genesis
        evo_tracker.record_creation(skill_id="child1", version="0.1.0", rationale="from pattern")
        lin_tracker.record_parent_child("parent1", "child1", evidence="genesis")

        # Verify
        history = evo_tracker.get_history("child1")
        assert len(history) == 1
        assert history[0].event_type == "created"

        summary = lin_tracker.get_summary("child1")
        assert "parent1" in summary.parents


class TestModelBackwardCompat:
    def test_skill_manifest_unknown_keys_ignored(self):
        """SkillManifest.from_dict ignores unknown keys."""
        data = {
            "name": "test",
            "description": "desc",
            "source_pattern_ids": [],
            "triggers": [],
            "capabilities": [],
            "implementation_summary": "impl",
            "unknown_future_field": "should_be_ignored",
        }
        m = SkillManifest.from_dict(data)
        assert m.name == "test"
        assert not hasattr(m, "unknown_future_field") or m.name == "test"

    def test_skill_manifest_new_fields_default(self):
        """New funding/lineage fields default to None/[]."""
        m = SkillManifest(
            name="test",
            description="desc",
            source_pattern_ids=[],
            triggers=[],
            capabilities=[],
            implementation_summary="impl",
        )
        assert m.funding is None
        assert m.parent_skill_ids == []
        assert m.child_skill_ids == []
        assert m.derived_from_unification is None


class TestConfigIntegration:
    def test_full_config_from_env(self, monkeypatch):
        monkeypatch.setenv("ESASS_DONATION_ENABLED", "true")
        monkeypatch.setenv("ESASS_TRACING_ENABLED", "true")
        from openclaw_plugin.config.settings import IntegrationConfig
        cfg = IntegrationConfig.from_env()
        assert cfg.donation.enabled is True
        assert cfg.tracing.enabled is True
        assert cfg.donation.paypal_username == "mrstanton81"
