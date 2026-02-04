"""
OpenClaw skill metadata model.

Extended with funding and lineage fields for the new plugin architecture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class OpenClawSkillMetadata:
    """OpenClaw SKILL.md frontmatter structure."""
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    author: str = "esass-genesis"
    genesis_type: str = "emergent"
    pattern_id: Optional[str] = None
    confidence: float = 0.0
    support: int = 0
    first_observed: Optional[str] = None
    triggers: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    parent_skills: List[str] = field(default_factory=list)
    child_skills: List[str] = field(default_factory=list)
    generation: int = 1

    # Lineage fields
    parent_skill_ids: List[str] = field(default_factory=list)
    child_skill_ids: List[str] = field(default_factory=list)
    derived_from_unification: Optional[str] = None

    # Funding (populated by FundingInjector)
    funding: Optional[Dict[str, Any]] = None
