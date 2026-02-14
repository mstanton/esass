"""
Tests for the adapters module (~10 tests).
"""

import pytest
import yaml
from pathlib import Path

from esass_prototype.models import SkillManifest, TriggerCondition, PatternDefinition
from openclaw_plugin.adapters.metadata import OpenClawSkillMetadata
from openclaw_plugin.adapters.skill_formatter import SkillFormatter
from openclaw_plugin.donation.injector import FundingInjector


def _make_manifest(**overrides):
    defaults = dict(
        name="test_skill",
        description="A test skill",
        source_pattern_ids=["p1"],
        triggers=[TriggerCondition(trigger_type="intent_match", pattern="test")],
        capabilities=["git_operations"],
        implementation_summary="Do stuff",
        version="1.0.0",
    )
    defaults.update(overrides)
    return SkillManifest(**defaults)


def _make_pattern(**overrides):
    defaults = dict(
        pattern_type="temporal",
        support=20,
        confidence=0.9,
        stability_days=10,
        description="test pattern",
        sequence=["reasoning:git", "tool_usage:git,status"],
        exemplar_ids=["e1"],
        skill_candidate=True,
        tags=["git"],
        first_seen="2026-01-01T00:00:00",
        last_seen="2026-02-01T00:00:00",
    )
    defaults.update(overrides)
    return PatternDefinition(**defaults)


class TestOpenClawSkillMetadata:
    def test_default_values(self):
        m = OpenClawSkillMetadata()
        assert m.version == "1.0.0"
        assert m.author == "esass-genesis"

    def test_funding_field(self):
        m = OpenClawSkillMetadata(funding={"paypal": "https://paypal.me/mrstanton81"})
        assert m.funding["paypal"] == "https://paypal.me/mrstanton81"


class TestSkillFormatter:
    def test_format_skill_basic(self, tmp_skills_dir):
        fmt = SkillFormatter(output_dir=tmp_skills_dir)
        manifest = _make_manifest()
        content = fmt.format_skill(manifest)
        assert "---" in content
        assert "test-skill" in content

    def test_format_skill_with_funding(self, tmp_skills_dir):
        injector = FundingInjector()
        fmt = SkillFormatter(output_dir=tmp_skills_dir, funding_injector=injector)
        manifest = _make_manifest()
        content = fmt.format_skill(manifest)
        assert "funding:" in content
        assert "paypal" in content

    def test_format_skill_without_funding(self, tmp_skills_dir):
        from openclaw_plugin.donation.models import DonationConfig
        injector = FundingInjector(config=DonationConfig(enabled=False))
        fmt = SkillFormatter(output_dir=tmp_skills_dir, funding_injector=injector)
        manifest = _make_manifest()
        content = fmt.format_skill(manifest)
        assert "funding:" not in content

    def test_save_skill(self, tmp_skills_dir):
        fmt = SkillFormatter(output_dir=tmp_skills_dir)
        manifest = _make_manifest()
        path = fmt.save_skill(manifest)
        assert path.exists()
        assert path.name == "SKILL.md"

    def test_frontmatter_valid_yaml(self, tmp_skills_dir):
        fmt = SkillFormatter(output_dir=tmp_skills_dir)
        manifest = _make_manifest()
        content = fmt.format_skill(manifest)
        parts = content.split("---", 2)
        assert len(parts) >= 3
        data = yaml.safe_load(parts[1])
        assert data["name"] == "test-skill"
        assert data["version"] == "1.0.0"

    def test_lineage_in_frontmatter(self, tmp_skills_dir):
        fmt = SkillFormatter(output_dir=tmp_skills_dir)
        manifest = _make_manifest(parent_skill_ids=["parent1"])
        content = fmt.format_skill(manifest)
        parts = content.split("---", 2)
        data = yaml.safe_load(parts[1])
        assert "lineage" in data
        assert "parent1" in data["lineage"]["parent_skill_ids"]

    def test_workflow_from_pattern(self, tmp_skills_dir):
        fmt = SkillFormatter(output_dir=tmp_skills_dir)
        manifest = _make_manifest()
        pattern = _make_pattern()
        content = fmt.format_skill(manifest, pattern)
        assert "Analyze Context" in content
        assert "Execute Git" in content

    def test_batch_convert(self, tmp_skills_dir):
        fmt = SkillFormatter(output_dir=tmp_skills_dir)
        m1 = _make_manifest(name="skill_a")
        m2 = _make_manifest(name="skill_b")
        paths = fmt.batch_convert([m1, m2])
        assert len(paths) == 2

    def test_badge_in_body_when_funded(self, tmp_skills_dir):
        injector = FundingInjector()
        fmt = SkillFormatter(output_dir=tmp_skills_dir, funding_injector=injector)
        manifest = _make_manifest()
        content = fmt.format_skill(manifest)
        assert "shields.io" in content
        assert "## Support" in content
