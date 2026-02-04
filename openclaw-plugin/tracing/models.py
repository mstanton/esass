"""
Tracing data models.

Usage records, evolution events, and cross-skill lineage edges.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------

@dataclass
class UsageRecord:
    """Single skill activation / completion record."""
    usage_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    skill_id: str = ""
    skill_name: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    session_id: str = ""
    user_hash: str = ""  # SHA-256 anonymized
    agent_id: str = ""
    trigger_context: str = ""
    outcome: str = ""  # "success", "failure", "pending"
    duration_ms: float = 0.0
    error_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UsageRecord":
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in valid})

    @staticmethod
    def anonymize_user(user_id: str) -> str:
        """SHA-256 hash of user_id for privacy."""
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]


@dataclass
class UsageAggregation:
    """Rolled-up stats per skill per window."""
    skill_id: str = ""
    skill_name: str = ""
    window_start: str = ""
    window_end: str = ""
    activation_count: int = 0
    completion_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_duration_ms: float = 0.0
    unique_sessions: int = 0
    unique_users: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Evolution
# ---------------------------------------------------------------------------

class EvolutionEventType(str, Enum):
    CREATED = "created"
    VERSION_BUMP = "version_bump"
    MERGE = "merge"
    UNIFICATION = "unification"
    DEPRECATION = "deprecation"


@dataclass
class EvolutionEvent:
    """Single evolution event for a skill."""
    evolution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    skill_id: str = ""
    event_type: str = EvolutionEventType.CREATED.value
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    from_version: str = ""
    to_version: str = ""
    changes: Dict[str, Any] = field(default_factory=dict)  # field-level diffs
    rationale: str = ""
    triggered_by: str = ""  # what caused this event
    related_skill_ids: List[str] = field(default_factory=list)
    related_pattern_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvolutionEvent":
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in valid})


# ---------------------------------------------------------------------------
# Lineage
# ---------------------------------------------------------------------------

class LineageRelation(str, Enum):
    PARENT_CHILD = "parent_child"
    INFLUENCED = "influenced"
    COMPOSED_INTO = "composed_into"
    REPLACED_BY = "replaced_by"
    UNIFIED_INTO = "unified_into"
    FORKED_FROM = "forked_from"


@dataclass
class LineageEdge:
    """Directed graph edge between skills."""
    source_skill_id: str = ""
    target_skill_id: str = ""
    relation_type: str = LineageRelation.PARENT_CHILD.value
    confidence: float = 1.0
    evidence: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LineageEdge":
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in valid})


@dataclass
class SkillLineageSummary:
    """Aggregated view of a skill's graph neighborhood."""
    skill_id: str = ""
    parents: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    influenced_by: List[str] = field(default_factory=list)
    influences: List[str] = field(default_factory=list)
    composed_into: List[str] = field(default_factory=list)
    replaced_by: Optional[str] = None
    unified_into: Optional[str] = None
    forked_from: Optional[str] = None
    edges: List[LineageEdge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["edges"] = [e.to_dict() if hasattr(e, "to_dict") else e for e in self.edges]
        return d
