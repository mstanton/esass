"""
Tests for the donation subsystem (~10 tests).
"""

import os
import pytest

from openclaw_plugin.donation.models import DonationConfig, FundingInfo
from openclaw_plugin.donation.display import DonationDisplay
from openclaw_plugin.donation.injector import FundingInjector


class TestDonationConfig:
    def test_default_values(self):
        cfg = DonationConfig()
        assert cfg.enabled is True
        assert cfg.paypal_username == "mrstanton81"
        assert cfg.paypal_link == "https://paypal.me/mrstanton81"
        assert cfg.project_name == "ESASS"
        assert len(cfg.suggested_amounts) == 3

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("ESASS_DONATION_ENABLED", "false")
        cfg = DonationConfig.from_env()
        assert cfg.enabled is False

    def test_from_env_custom_paypal(self, monkeypatch):
        monkeypatch.setenv("ESASS_PAYPAL_USERNAME", "testuser")
        monkeypatch.setenv("ESASS_PAYPAL_LINK", "https://paypal.me/testuser")
        cfg = DonationConfig.from_env()
        assert cfg.paypal_username == "testuser"
        assert cfg.paypal_link == "https://paypal.me/testuser"

    def test_render_message(self):
        cfg = DonationConfig()
        msg = cfg.render_message()
        assert "ESASS" in msg
        assert "paypal.me/mrstanton81" in msg


class TestFundingInfo:
    def test_from_config(self):
        cfg = DonationConfig()
        info = FundingInfo.from_config(cfg)
        assert info.paypal == cfg.paypal_link
        assert info.project == "ESASS"
        assert len(info.suggested_amounts) == 3

    def test_serialization_roundtrip(self):
        info = FundingInfo()
        d = info.to_dict()
        info2 = FundingInfo.from_dict(d)
        assert info2.paypal == info.paypal
        assert info2.project == info.project
        assert info2.suggested_amounts == info.suggested_amounts


class TestFundingInjector:
    def test_inject_into_manifest(self):
        from esass_prototype.models import SkillManifest
        manifest = SkillManifest(
            name="test-skill",
            description="test",
            source_pattern_ids=[],
            triggers=[],
            capabilities=[],
            implementation_summary="test",
        )
        injector = FundingInjector()
        injector.inject_into_manifest(manifest)
        assert manifest.funding is not None
        assert "paypal" in manifest.funding

    def test_inject_disabled(self):
        from esass_prototype.models import SkillManifest
        manifest = SkillManifest(
            name="test-skill",
            description="test",
            source_pattern_ids=[],
            triggers=[],
            capabilities=[],
            implementation_summary="test",
        )
        cfg = DonationConfig(enabled=False)
        injector = FundingInjector(config=cfg)
        injector.inject_into_manifest(manifest)
        assert manifest.funding is None

    def test_get_frontmatter_block(self):
        injector = FundingInjector()
        block = injector.get_frontmatter_block()
        assert "funding" in block
        assert block["funding"]["paypal"] == "https://paypal.me/mrstanton81"


class TestDonationDisplay:
    def test_render_activation_message(self):
        display = DonationDisplay()
        msg = display.render_activation_message("my-skill")
        assert "my-skill" in msg
        assert "paypal.me" in msg

    def test_render_for_agent(self):
        display = DonationDisplay()
        d = display.render_for_agent("my-skill")
        assert d["donation_enabled"] is True
        assert d["skill_name"] == "my-skill"
        assert "paypal_link" in d

    def test_render_for_human(self):
        display = DonationDisplay()
        txt = display.render_for_human("my-skill")
        assert "my-skill" in txt
        assert "Coffee" in txt
        assert "Matt Stanton" in txt

    def test_render_markdown_badge(self):
        display = DonationDisplay()
        badge = display.render_markdown_badge()
        assert "shields.io" in badge
        assert "paypal.me" in badge

    def test_disabled_returns_empty(self):
        cfg = DonationConfig(enabled=False)
        display = DonationDisplay(config=cfg)
        assert display.render_activation_message("x") == ""
        assert display.render_for_agent("x") == {"donation_enabled": False}
        assert display.render_for_human("x") == ""
        assert display.render_markdown_badge() == ""
