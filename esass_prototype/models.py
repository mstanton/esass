"""
Core data models for ESASS prototype.

Simplified versions of specification types from esass-specification_v0.01.md:
- LogEntry (§4.3): Observation records
- PatternDefinition (§3.1.2): Detected patterns
- SkillManifest (§3.1.3): Generated skills
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from uuid import uuid4
import json


# Event Types (§4.4 of specification)
class EventType(Enum):
    """Types of events captured during observation"""
    REASONING = "reasoning"
    TOOL_USAGE = "tool_usage"
    DECISION = "decision"
    OUTPUT = "output"


# Log Levels (§4.2 of specification)
class LogLevel(Enum):
    """Hierarchical log retention levels"""
    TRACE = "L0"      # 24 hours
    DEBUG = "L1"      # 7 days
    INFO = "L2"       # 90 days
    SUMMARY = "L3"    # Indefinite
    INSIGHT = "L4"    # Permanent


# Pattern Types (§5.1 of specification)
class PatternType(Enum):
    """Categories of detected patterns"""
    TEMPORAL = "temporal"          # Sequences, cycles
    STRUCTURAL = "structural"      # Tool combinations
    SEMANTIC = "semantic"          # Conceptual clustering
    BEHAVIORAL = "behavioral"      # Response styles


@dataclass
class LogEntry:
    """
    Simplified observation record from §4.3 of specification.

    Captures execution events with causality tracking.
    """
    entry_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    level: str = LogLevel.INFO.value
    event_type: str = EventType.REASONING.value
    event_data: Dict[str, Any] = field(default_factory=dict)
    session_id: str = ""
    caused_by: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        """Create from dictionary"""
        return cls(**data)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'LogEntry':
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class PatternQualityMetrics:
    """
    Pattern quality metrics from §5.3 of specification.
    """
    support: int = 0              # How many instances
    confidence: float = 0.0       # 0.0-1.0 reliability
    lift: float = 1.0             # Surprising vs baseline
    stability_days: int = 0       # Days pattern has been stable
    coherence: float = 0.0        # Internal consistency
    distinctiveness: float = 0.0  # Separation from other patterns

    def meets_candidacy_criteria(self) -> bool:
        """
        Check if pattern meets skill candidacy criteria (§6.2).

        Criteria:
        - Support ≥ 10 instances
        - Confidence ≥ 0.8
        - Stability ≥ 7 days
        """
        return (
            self.support >= 10 and
            self.confidence >= 0.8 and
            self.stability_days >= 7
        )


@dataclass
class PatternDefinition:
    """
    Simplified pattern definition from §3.1.2 of specification.

    Represents a recurring structure detected in observation logs.
    """
    pattern_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    pattern_type: str = PatternType.TEMPORAL.value

    # Quality metrics (§5.3 of specification)
    support: int = 0              # How many instances
    confidence: float = 0.0       # 0.0-1.0
    stability_days: int = 0       # Days pattern has been stable

    # Structure
    description: str = ""
    sequence: List[str] = field(default_factory=list)  # Event type sequence
    exemplar_ids: List[str] = field(default_factory=list)  # Example log entries

    # Genesis potential
    skill_candidate: bool = False

    # Additional metadata
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PatternDefinition':
        """Create from dictionary"""
        return cls(**data)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'PatternDefinition':
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))

    def get_quality_metrics(self) -> PatternQualityMetrics:
        """Get pattern quality metrics"""
        return PatternQualityMetrics(
            support=self.support,
            confidence=self.confidence,
            stability_days=self.stability_days
        )


@dataclass
class SkillManifest:
    """
    Simplified skill manifest from §3.1.3 of specification.

    Complete specification of an auto-generated skill.
    """
    skill_id: str = field(default_factory=lambda: str(uuid4()))
    version: str = "0.1.0"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    genesis_type: str = "derived"  # derived, authored, hybrid

    # Identity
    name: str = ""
    description: str = ""
    keywords: List[str] = field(default_factory=list)

    # Lineage
    source_pattern_ids: List[str] = field(default_factory=list)
    parent_skills: List[str] = field(default_factory=list)

    # Specification
    triggers: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)

    # Implementation (simplified - just a description for prototype)
    implementation_summary: str = ""

    # Quality
    validation_status: str = "pending"  # pending, validated, active, deprecated
    usage_count: int = 0
    success_rate: float = 0.0

    # Metadata
    tags: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillManifest':
        """Create from dictionary"""
        return cls(**data)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'SkillManifest':
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class ObserverState:
    """
    Runtime state for observation controller.
    """
    is_enabled: bool = False
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None
    total_sessions: int = 0
    total_events: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ObserverState':
        """Create from dictionary"""
        return cls(**data)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'ObserverState':
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))


# Helper functions for common operations

def create_reasoning_event(
    statement: str,
    confidence: float,
    session_id: str,
    tags: List[str],
    caused_by: Optional[List[str]] = None
) -> LogEntry:
    """Create a reasoning event log entry"""
    return LogEntry(
        event_type=EventType.REASONING.value,
        event_data={
            "statement": statement,
            "confidence": confidence,
            "subtype": "hypothesis_generation"
        },
        session_id=session_id,
        tags=tags,
        caused_by=caused_by or []
    )


def create_tool_usage_event(
    tool_name: str,
    parameters: Dict[str, Any],
    outcome_assessment: str,
    session_id: str,
    tags: List[str],
    caused_by: Optional[List[str]] = None
) -> LogEntry:
    """Create a tool usage event log entry"""
    return LogEntry(
        event_type=EventType.TOOL_USAGE.value,
        event_data={
            "tool_name": tool_name,
            "parameters": parameters,
            "outcome_assessment": outcome_assessment,
            "phase": "invocation"
        },
        session_id=session_id,
        tags=tags,
        caused_by=caused_by or []
    )


def create_decision_event(
    decision: str,
    confidence: float,
    session_id: str,
    tags: List[str],
    caused_by: Optional[List[str]] = None
) -> LogEntry:
    """Create a decision event log entry"""
    return LogEntry(
        event_type=EventType.DECISION.value,
        event_data={
            "decision": decision,
            "confidence": confidence,
            "decision_class": "strategy_selection"
        },
        session_id=session_id,
        tags=tags,
        caused_by=caused_by or []
    )
