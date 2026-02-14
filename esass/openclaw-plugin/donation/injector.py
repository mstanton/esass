"""
Funding injector.

Injects FundingInfo into SkillManifest.funding and provides helpers
for SKILL.md frontmatter injection.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .models import DonationConfig, FundingInfo


class FundingInjector:
    """Injects funding information into manifests and metadata."""

    def __init__(self, config: Optional[DonationConfig] = None):
        self.config = config or DonationConfig()
        self._funding: Optional[FundingInfo] = None

    @property
    def funding(self) -> FundingInfo:
        if self._funding is None:
            self._funding = FundingInfo.from_config(self.config)
        return self._funding

    def inject_into_manifest(self, manifest: Any) -> Any:
        """
        Set manifest.funding to funding dict if donation is enabled.
        Modifies the manifest in-place and returns it.
        """
        if not self.config.enabled or not self.config.show_in_metadata:
            return manifest
        manifest.funding = self.funding.to_dict()
        return manifest

    def get_frontmatter_block(self) -> Dict[str, Any]:
        """
        Return a dict suitable for merging into SKILL.md YAML frontmatter.

        Example output:
        {
            "funding": {
                "paypal": "https://paypal.me/mrstanton81",
                "suggested_amounts": [...],
                "project": "ESASS",
                "project_url": "...",
                "message": "..."
            }
        }
        """
        if not self.config.enabled or not self.config.show_in_metadata:
            return {}
        return {"funding": self.funding.to_dict()}
