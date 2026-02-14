"""
Donation display rendering.

Provides multiple rendering formats for donation notices:
agent (structured dict), human (CLI), markdown badge.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .models import DonationConfig, FundingInfo


class DonationDisplay:
    """Renders donation notices in various formats."""

    def __init__(self, config: Optional[DonationConfig] = None):
        self.config = config or DonationConfig()
        self.funding = FundingInfo.from_config(self.config)

    def render_activation_message(self, skill_name: str) -> str:
        """One-line string for log output on skill activation."""
        if not self.config.enabled:
            return ""
        msg = (
            f"[ESASS] Skill '{skill_name}' activated | "
            f"Support: {self.config.paypal_link}"
        )
        if self.config.paypal_crypto_enabled:
            msg += " (crypto accepted)"
        return msg

    def render_for_agent(self, skill_name: str) -> Dict[str, Any]:
        """Structured dict that agents can parse."""
        if not self.config.enabled:
            return {"donation_enabled": False}
        result = {
            "donation_enabled": True,
            "skill_name": skill_name,
            "project": self.config.project_name,
            "paypal_link": self.config.paypal_link,
            "paypal_username": self.config.paypal_username,
            "suggested_amounts": self.config.suggested_amounts,
            "message": self.config.render_message(),
        }
        if self.config.paypal_crypto_enabled:
            result["paypal_crypto_link"] = self.config.paypal_crypto_link
            result["paypal_crypto_enabled"] = True
        return result

    def render_for_human(self, skill_name: str) -> str:
        """Formatted CLI output with amounts table."""
        if not self.config.enabled:
            return ""
        lines = [
            f"--- ESASS Skill: {skill_name} ---",
            f"Project: {self.config.project_name}",
            f"Author: Matt Stanton (@{self.config.paypal_username})",
            "",
            "If you find this skill useful, consider supporting development:",
            f"  PayPal: {self.config.paypal_link}",
        ]
        if self.config.paypal_crypto_enabled:
            lines.append(f"  PayPal Crypto: {self.config.paypal_crypto_link}")
        lines += [
            "",
            "  Suggested amounts:",
        ]
        for amt in self.config.suggested_amounts:
            lines.append(
                f"    {amt['label']:12s}  ${amt['amount']:.2f} {amt['currency']}"
            )
        lines.append("")
        lines.append(self.config.render_message())
        lines.append("---")
        return "\n".join(lines)

    def render_markdown_badge(self) -> str:
        """Shields.io badge markdown for SKILL.md body."""
        if not self.config.enabled:
            return ""
        badge_url = (
            "https://img.shields.io/badge/"
            "Support-PayPal-blue?logo=paypal&logoColor=white"
        )
        badges = f"[![Support]({badge_url})]({self.config.paypal_link})"
        if self.config.paypal_crypto_enabled:
            crypto_badge_url = (
                "https://img.shields.io/badge/"
                "Crypto-PayPal-orange?logo=paypal&logoColor=white"
            )
            badges += f" [![Crypto]({crypto_badge_url})]({self.config.paypal_crypto_link})"
        return badges
