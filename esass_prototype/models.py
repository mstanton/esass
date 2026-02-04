"""
Core data models for ESASS prototype.

Aligned with specification sections 3 and 4.
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class EventType(Enum):
    """Event types from specification §4.3"""
    REASONING = "reasoning"
    TOOL_USAGE = "tool_usage"
    DECISION = "decision"
    ERROR = "error"
    OUTCOME = "outcome"
    # Meta-cognitive event types (from esass/probes)
    ERROR_RECOVERY = "error_recovery"
    STRATEGY_SHIFT = "strategy_shift"
    CALIBRATION = "calibration"
    INSIGHT = "insight"
    SCOPE_EXPANSION = "scope_expansion"


class PatternType(Enum):
    """Pattern types"""
    TEMPORAL = "temporal"
    SEMANTIC = "semantic"
    BEHAVIORAL = "behavioral"
    HYBRID = "hybrid"


@dataclass
class LogEntry:
    """
    Observation log entry (§4.3)

    Captures individual events with causality tracking and metadata.
    """
    event_id: str
    timestamp: str  # ISO format
    event_type: str
    event_data: Dict[str, Any]
    session_id: str
    caused_by: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    conversation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def entry_id(self) -> str:
        """Alias for event_id for backward compatibility"""
        return self.event_id

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Ensure timestamp is a string for JSON serialization
        if isinstance(data['timestamp'], datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'LogEntry':
        """Create from dictionary, ignoring unknown keys for forward-compatibility"""
        import dataclasses as _dc
        valid_fields = {f.name for f in _dc.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in valid_fields})

    @classmethod
    def create(cls, event_type: str, event_data: Dict[str, Any],
               session_id: str, caused_by: Optional[str] = None,
               tags: Optional[List[str]] = None) -> 'LogEntry':
        """Factory method to create a new log entry"""
        return cls(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type,
            event_data=event_data,
            session_id=session_id,
            caused_by=caused_by,
            tags=tags or []
        )


@dataclass
class PatternDefinition:
    """
    Detected temporal pattern (§3.1.2)

    Represents a recurring sequence of events with quality metrics.
    """
    pattern_type: str
    support: int
    confidence: float
    stability_days: int
    description: str
    sequence: List[str]  # Event type signatures (e.g., "reasoning:git", "tool_usage:git,status")
    exemplar_ids: List[str]  # Event IDs showing this pattern
    skill_candidate: bool
    tags: List[str]
    first_seen: str  # ISO timestamp
    last_seen: str  # ISO timestamp
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'PatternDefinition':
        """Create from dictionary"""
        return cls(**data)

    # Backward compatibility properties
    @property
    def metrics(self):
        """Provide backward compatible metrics access"""
        from collections import namedtuple
        Metrics = namedtuple('Metrics', ['support', 'confidence', 'stability_days'])
        return Metrics(self.support, self.confidence, self.stability_days)


@dataclass
class PatternQualityMetrics:
    """
    Quality metrics for pattern evaluation.

    Used in pattern ranking and skill candidacy evaluation.
    """
    support: int
    confidence: float
    stability_days: int
    lift: float = 1.0
    coherence: float = 0.0
    distinctiveness: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'PatternQualityMetrics':
        return cls(**data)


@dataclass
class TriggerCondition:
    """Trigger condition for skill activation (§3.1.3)"""
    trigger_type: str  # "intent_match", "event_type", "context_match"
    pattern: str
    confidence_threshold: float = 0.8

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'TriggerCondition':
        return cls(**data)


@dataclass
class SkillManifest:
    """
    Skill manifest (§3.1.3)

    Generated from validated patterns, ready for implementation.
    """
    name: str
    description: str
    source_pattern_ids: List[str]
    triggers: List[TriggerCondition]
    capabilities: List[str]
    implementation_summary: str
    genesis_type: str = "derived"
    keywords: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    validation_status: str = "pending"  # pending, validated, rejected
    version: str = "0.1.0"
    usage_count: int = 0
    success_rate: float = 0.0
    skill_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    funding: Optional[Dict[str, Any]] = None
    parent_skill_ids: List[str] = field(default_factory=list)
    child_skill_ids: List[str] = field(default_factory=list)
    derived_from_unification: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Handle both string triggers and TriggerCondition objects
        if self.triggers:
            if isinstance(self.triggers[0], str):
                data['triggers'] = self.triggers
            else:
                data['triggers'] = [t.to_dict() if hasattr(t, 'to_dict') else t for t in self.triggers]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'SkillManifest':
        """Create from dictionary, filtering unknown keys for forward-compatibility"""
        import dataclasses as _dc
        valid_fields = {f.name for f in _dc.fields(cls)}

        data_copy = {k: v for k, v in data.items() if k in valid_fields or k == 'triggers'}
        triggers_data = data_copy.pop('triggers', [])

        # Handle both string triggers and TriggerCondition objects
        triggers = []
        for t in triggers_data:
            if isinstance(t, str):
                # Parse string trigger format: "type:pattern"
                parts = t.split(':', 1)
                if len(parts) == 2:
                    triggers.append(TriggerCondition(
                        trigger_type=parts[0],
                        pattern=parts[1]
                    ))
                else:
                    # Fallback for malformed strings
                    triggers.append(TriggerCondition(
                        trigger_type="unknown",
                        pattern=t
                    ))
            elif isinstance(t, dict):
                triggers.append(TriggerCondition.from_dict(t))
            else:
                triggers.append(t)

        return cls(triggers=triggers, **data_copy)

    @classmethod
    def create(cls, name: str, description: str, source_pattern_ids: List[str],
               triggers: List[TriggerCondition], capabilities: List[str],
               implementation_summary: str) -> 'SkillManifest':
        """Factory method to create a new skill manifest"""
        return cls(
            skill_id=str(uuid.uuid4()),
            name=name,
            description=description,
            source_pattern_ids=source_pattern_ids,
            triggers=triggers,
            capabilities=capabilities,
            implementation_summary=implementation_summary,
            created_at=datetime.utcnow().isoformat()
        )


@dataclass
class ObserverState:
    """
    Runtime state for observation subsystem

    Tracks whether observation is active and metadata.
    """
    enabled: bool = False
    mode: str = "simulation"  # "simulation" or "capture"
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None
    session_count: int = 0
    event_count: int = 0
    total_sessions: int = 0  # Backward compatibility
    total_events: int = 0  # Backward compatibility

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> 'ObserverState':
        import dataclasses as _dc
        valid_fields = {f.name for f in _dc.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in valid_fields})

    @classmethod
    def from_json(cls, json_str: str) -> 'ObserverState':
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)


def serialize_to_json(obj: Any) -> str:
    """Serialize any model to JSON string"""
    if hasattr(obj, 'to_dict'):
        return json.dumps(obj.to_dict(), indent=2)
    return json.dumps(obj, indent=2)


def deserialize_from_json(json_str: str, model_class: type) -> Any:
    """Deserialize JSON string to model instance"""
    data = json.loads(json_str)
    if hasattr(model_class, 'from_dict'):
        return model_class.from_dict(data)
    return model_class(**data)


# Helper factory functions for creating specific event types

def create_reasoning_event(statement: Optional[str] = None,
                           hypothesis: Optional[str] = None,
                           confidence: float = 0.0,
                           evidence: Optional[List[str]] = None,
                           session_id: str = "",
                           caused_by: Optional[Any] = None,
                           tags: Optional[List[str]] = None) -> LogEntry:
    """Create a reasoning event"""
    # Support both 'statement' and 'hypothesis' for backward compatibility
    reasoning_text = statement or hypothesis or ""

    # Handle caused_by as either string or list
    caused_by_id = None
    if caused_by:
        if isinstance(caused_by, list):
            caused_by_id = caused_by[0] if caused_by else None
        else:
            caused_by_id = caused_by

    event_data = {
        "statement": reasoning_text,
        "confidence": confidence,
    }
    if evidence:
        event_data["evidence"] = evidence

    return LogEntry.create(
        event_type=EventType.REASONING.value,
        event_data=event_data,
        session_id=session_id,
        caused_by=caused_by_id,
        tags=tags or ["reasoning"]
    )


def create_tool_usage_event(tool_name: str,
                            parameters: Dict[str, Any],
                            outcome_assessment: str,
                            session_id: str = "",
                            caused_by: Optional[Any] = None,
                            tags: Optional[List[str]] = None) -> LogEntry:
    """Create a tool usage event"""
    # Handle caused_by as either string or list
    caused_by_id = None
    if caused_by:
        if isinstance(caused_by, list):
            caused_by_id = caused_by[0] if caused_by else None
        else:
            caused_by_id = caused_by

    event_data = {
        "tool_name": tool_name,
        "parameters": parameters,
        "outcome_assessment": outcome_assessment
    }
    return LogEntry.create(
        event_type=EventType.TOOL_USAGE.value,
        event_data=event_data,
        session_id=session_id,
        caused_by=caused_by_id,
        tags=tags or ["tool_usage", tool_name]
    )


def create_decision_event(decision: str,
                         confidence: float = 0.0,
                         options_considered: Optional[List[str]] = None,
                         rationale: Optional[str] = None,
                         session_id: str = "",
                         caused_by: Optional[Any] = None,
                         tags: Optional[List[str]] = None) -> LogEntry:
    """Create a decision event"""
    # Handle caused_by as either string or list
    caused_by_id = None
    if caused_by:
        if isinstance(caused_by, list):
            caused_by_id = caused_by[0] if caused_by else None
        else:
            caused_by_id = caused_by

    event_data = {
        "decision": decision,
        "confidence": confidence,
    }
    if options_considered:
        event_data["options_considered"] = options_considered
    if rationale:
        event_data["rationale"] = rationale

    return LogEntry.create(
        event_type=EventType.DECISION.value,
        event_data=event_data,
        session_id=session_id,
        caused_by=caused_by_id,
        tags=tags or ["decision"]
    )
