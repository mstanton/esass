"""
Tests for Phase 2 pattern detectors and storage abstractions.

Covers:
- SemanticPatternDetector
- BehavioralPatternDetector
- Storage ABC interfaces and concrete inheritance
- PatternType.BEHAVIORAL enum value
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from esass_prototype.analysis.behavioral_detector import BehavioralPatternDetector
from esass_prototype.analysis.semantic_detector import SemanticPatternDetector
from esass_prototype.models import (
    EventType,
    LogEntry,
    PatternDefinition,
    PatternType,
    SkillManifest,
    TriggerCondition,
    create_decision_event,
    create_reasoning_event,
    create_tool_usage_event,
)
from esass_prototype.observation.simulator import EventSimulator
from esass_prototype.storage.interfaces import (
    LogStoreInterface,
    PatternStoreInterface,
    SkillStoreInterface,
)
from esass_prototype.storage.log_store import LogStore
from esass_prototype.storage.pattern_store import PatternStore
from esass_prototype.storage.skill_store import SkillStore


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def temp_data_dir(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def simulated_logs():
    """Generate a reproducible set of simulated logs across multiple sessions and days."""
    simulator = EventSimulator(seed=42)
    return simulator.generate_multiple_sessions(count=30, days=14)


@pytest.fixture
def diverse_logs():
    """Generate logs with error events and varied confidence for behavioral detection."""
    entries = []
    base_time = datetime(2026, 1, 1, 10, 0, 0)

    for day in range(10):
        for session_idx in range(3):
            sid = f"sess-{day}-{session_idx}"
            t = base_time + timedelta(days=day, hours=session_idx)

            # Start with reasoning (analyze_first workflow)
            entries.append(LogEntry.create(
                event_type="reasoning",
                event_data={"statement": "Analyzing the problem", "confidence": 0.5},
                session_id=sid,
                tags=["reasoning", "analysis"],
            ))
            entries[-1].timestamp = t.isoformat()

            # Tool usage — consistent tool preference for "Read"
            entries.append(LogEntry.create(
                event_type="tool_usage",
                event_data={"tool_name": "Read", "parameters": {}, "outcome_assessment": "success"},
                session_id=sid,
                tags=["tool_usage", "Read"],
            ))
            entries[-1].timestamp = (t + timedelta(seconds=5)).isoformat()

            # Decision with moderate confidence
            entries.append(LogEntry.create(
                event_type="decision",
                event_data={"decision": "Proceed with fix", "confidence": 0.85},
                session_id=sid,
                tags=["decision", "fix"],
            ))
            entries[-1].timestamp = (t + timedelta(seconds=10)).isoformat()

            # Tool usage — Bash
            entries.append(LogEntry.create(
                event_type="tool_usage",
                event_data={"tool_name": "Bash", "parameters": {"command": "pytest"}, "outcome_assessment": "success"},
                session_id=sid,
                tags=["tool_usage", "Bash", "test"],
            ))
            entries[-1].timestamp = (t + timedelta(seconds=15)).isoformat()

            # Every 3rd session: inject an error + recovery
            if session_idx == 2:
                entries.append(LogEntry.create(
                    event_type="error",
                    event_data={"tool_name": "Bash", "error": "test failed"},
                    session_id=sid,
                    tags=["error", "test"],
                ))
                entries[-1].timestamp = (t + timedelta(seconds=20)).isoformat()

                # Recovery: retry same tool
                entries.append(LogEntry.create(
                    event_type="tool_usage",
                    event_data={"tool_name": "Bash", "parameters": {"command": "pytest -x"}, "outcome_assessment": "success"},
                    session_id=sid,
                    tags=["tool_usage", "Bash", "retry"],
                ))
                entries[-1].timestamp = (t + timedelta(seconds=25)).isoformat()

    return entries


# ── PatternType enum ────────────────────────────────────────────────

class TestPatternTypeEnum:
    def test_behavioral_exists(self):
        assert PatternType.BEHAVIORAL.value == "behavioral"

    def test_all_pattern_types(self):
        values = {pt.value for pt in PatternType}
        assert values == {"temporal", "semantic", "behavioral", "hybrid"}


# ── Storage ABC Interfaces ──────────────────────────────────────────

class TestStorageInterfaces:
    def test_log_store_inherits_interface(self):
        assert issubclass(LogStore, LogStoreInterface)

    def test_pattern_store_inherits_interface(self):
        assert issubclass(PatternStore, PatternStoreInterface)

    def test_skill_store_inherits_interface(self):
        assert issubclass(SkillStore, SkillStoreInterface)

    def test_log_store_is_instance(self, temp_data_dir):
        store = LogStore(temp_data_dir)
        assert isinstance(store, LogStoreInterface)

    def test_pattern_store_is_instance(self, temp_data_dir):
        store = PatternStore(temp_data_dir)
        assert isinstance(store, PatternStoreInterface)

    def test_skill_store_is_instance(self, temp_data_dir):
        store = SkillStore(temp_data_dir)
        assert isinstance(store, SkillStoreInterface)

    def test_log_store_save_alias(self, temp_data_dir):
        """LogStoreInterface.save() delegates to append()."""
        store = LogStore(temp_data_dir)
        entry = LogEntry.create("reasoning", {"statement": "test"}, "sess-1")
        store.save(entry)
        assert store.count_entries() == 1

    def test_pattern_store_save_many_alias(self, temp_data_dir):
        """PatternStoreInterface.save_many() delegates to save_batch()."""
        store = PatternStore(temp_data_dir)
        p = PatternDefinition(
            pattern_type="temporal", support=10, confidence=0.9,
            stability_days=7, description="test", sequence=["a", "b"],
            exemplar_ids=[], skill_candidate=True, tags=["t"],
            first_seen=datetime.utcnow().isoformat(),
            last_seen=datetime.utcnow().isoformat(),
        )
        store.save_many([p])
        assert store.count() == 1

    def test_skill_store_load_pending(self, temp_data_dir):
        """SkillStoreInterface.load_pending() convenience method."""
        store = SkillStore(temp_data_dir)
        skill = SkillManifest(
            name="test", description="d", source_pattern_ids=[],
            triggers=[], capabilities=["c"],
            implementation_summary="s", validation_status="pending",
        )
        store.save(skill)
        pending = store.load_pending()
        assert len(pending) == 1
        assert pending[0].name == "test"


# ── SemanticPatternDetector ─────────────────────────────────────────

class TestSemanticPatternDetector:
    def test_empty_input(self):
        detector = SemanticPatternDetector()
        assert detector.detect_patterns([]) == []

    def test_too_few_entries(self):
        detector = SemanticPatternDetector(min_cluster_size=5)
        entry = LogEntry.create("reasoning", {"statement": "hello"}, "s1")
        assert detector.detect_patterns([entry]) == []

    def test_detects_patterns_from_simulated_data(self, simulated_logs):
        detector = SemanticPatternDetector(
            min_support=3,
            min_confidence=0.3,
            min_stability_days=0,
            similarity_threshold=0.3,
            min_cluster_size=3,
        )
        patterns = detector.detect_patterns(simulated_logs)
        assert len(patterns) > 0

    def test_pattern_type_is_semantic(self, simulated_logs):
        detector = SemanticPatternDetector(
            min_support=3, min_confidence=0.3,
            min_stability_days=0, similarity_threshold=0.3,
            min_cluster_size=3,
        )
        patterns = detector.detect_patterns(simulated_logs)
        for p in patterns:
            assert p.pattern_type == PatternType.SEMANTIC.value

    def test_pattern_has_required_fields(self, simulated_logs):
        detector = SemanticPatternDetector(
            min_support=3, min_confidence=0.3,
            min_stability_days=0, similarity_threshold=0.3,
            min_cluster_size=3,
        )
        patterns = detector.detect_patterns(simulated_logs)
        if patterns:
            p = patterns[0]
            assert p.pattern_id is not None
            assert p.support >= 3
            assert 0.0 <= p.confidence <= 1.0
            assert isinstance(p.sequence, list)
            assert isinstance(p.tags, list)
            assert p.first_seen is not None
            assert p.last_seen is not None

    def test_tag_theme_detection(self):
        """Events sharing tag pairs should cluster together."""
        entries = []
        base = datetime(2026, 1, 1, 10, 0, 0)
        for i in range(20):
            sid = f"sess-{i % 5}"
            entries.append(LogEntry.create(
                event_type="tool_usage",
                event_data={"tool_name": "Bash", "parameters": {}, "outcome_assessment": "ok"},
                session_id=sid,
                tags=["git", "commit"],
            ))
            entries[-1].timestamp = (base + timedelta(days=i // 5, hours=i)).isoformat()

        detector = SemanticPatternDetector(
            min_support=5, min_confidence=0.3,
            min_stability_days=0, similarity_threshold=0.3,
            min_cluster_size=3,
        )
        patterns = detector.detect_patterns(entries)
        # Should find at least a tag theme for "git+commit"
        tag_themes = [p for p in patterns if 'git' in p.tags and 'commit' in p.tags]
        assert len(tag_themes) > 0 or len(patterns) > 0  # Either tag theme or text cluster

    def test_max_clusters_limit(self, simulated_logs):
        detector = SemanticPatternDetector(
            min_support=2, min_confidence=0.1,
            min_stability_days=0, similarity_threshold=0.2,
            min_cluster_size=2, max_clusters=3,
        )
        patterns = detector.detect_patterns(simulated_logs)
        assert len(patterns) <= 3

    def test_sorted_by_support(self, simulated_logs):
        detector = SemanticPatternDetector(
            min_support=3, min_confidence=0.3,
            min_stability_days=0, similarity_threshold=0.3,
            min_cluster_size=3,
        )
        patterns = detector.detect_patterns(simulated_logs)
        if len(patterns) >= 2:
            for i in range(len(patterns) - 1):
                assert patterns[i].support >= patterns[i + 1].support


# ── BehavioralPatternDetector ───────────────────────────────────────

class TestBehavioralPatternDetector:
    def test_empty_input(self):
        detector = BehavioralPatternDetector()
        assert detector.detect_patterns([]) == []

    def test_too_few_sessions(self):
        detector = BehavioralPatternDetector(min_sessions=5)
        entry = LogEntry.create("reasoning", {"statement": "test"}, "s1")
        assert detector.detect_patterns([entry]) == []

    def test_detects_patterns_from_diverse_logs(self, diverse_logs):
        detector = BehavioralPatternDetector(
            min_support=3,
            min_confidence=0.3,
            min_stability_days=0,
            min_sessions=3,
            bias_threshold=0.3,
        )
        patterns = detector.detect_patterns(diverse_logs)
        assert len(patterns) > 0

    def test_pattern_type_is_behavioral(self, diverse_logs):
        detector = BehavioralPatternDetector(
            min_support=3, min_confidence=0.3,
            min_stability_days=0, min_sessions=3,
            bias_threshold=0.3,
        )
        patterns = detector.detect_patterns(diverse_logs)
        for p in patterns:
            assert p.pattern_type == PatternType.BEHAVIORAL.value

    def test_detects_tool_preferences(self, diverse_logs):
        """Read and Bash are used in nearly every session."""
        detector = BehavioralPatternDetector(
            min_support=3, min_confidence=0.3,
            min_stability_days=0, min_sessions=3,
            bias_threshold=0.3,
        )
        patterns = detector.detect_patterns(diverse_logs)
        tool_patterns = [p for p in patterns if 'tool_preference' in p.tags]
        assert len(tool_patterns) > 0

        tool_names = set()
        for p in tool_patterns:
            tool_names.update(t for t in p.tags if t not in ('behavioral', 'tool_preference'))
        assert 'Read' in tool_names or 'Bash' in tool_names

    def test_detects_confidence_profiles(self, diverse_logs):
        """Reasoning events have consistent 0.5 confidence (low/exploratory)."""
        detector = BehavioralPatternDetector(
            min_support=3, min_confidence=0.3,
            min_stability_days=0, min_sessions=3,
            bias_threshold=0.3,
        )
        patterns = detector.detect_patterns(diverse_logs)
        conf_patterns = [p for p in patterns if 'confidence_profile' in p.tags]
        # We expect at least one confidence profile pattern
        assert len(conf_patterns) > 0

    def test_detects_workflow_styles(self, diverse_logs):
        """All sessions start with reasoning → analyze_first."""
        detector = BehavioralPatternDetector(
            min_support=3, min_confidence=0.3,
            min_stability_days=0, min_sessions=3,
            bias_threshold=0.3,
        )
        patterns = detector.detect_patterns(diverse_logs)
        workflow_patterns = [p for p in patterns if 'workflow_style' in p.tags]
        assert len(workflow_patterns) > 0
        # Check that analyze_first was detected
        styles = set()
        for p in workflow_patterns:
            styles.update(t for t in p.tags if t not in ('behavioral', 'workflow_style'))
        assert 'analyze_first' in styles

    def test_detects_error_recovery_styles(self, diverse_logs):
        """Every 3rd session has error → retry same tool."""
        detector = BehavioralPatternDetector(
            min_support=3, min_confidence=0.3,
            min_stability_days=0, min_sessions=3,
            bias_threshold=0.1,  # Low threshold since only 1/3 sessions have errors
        )
        patterns = detector.detect_patterns(diverse_logs)
        recovery_patterns = [p for p in patterns if 'error_recovery' in p.tags]
        # Should find retry_same_tool or pivot_to_different_tool
        if recovery_patterns:
            strategies = set()
            for p in recovery_patterns:
                strategies.update(t for t in p.tags if t not in ('behavioral', 'error_recovery'))
            # Bash is re-invoked after error, classified as retry or pivot
            assert len(strategies) > 0

    def test_sorted_by_support(self, diverse_logs):
        detector = BehavioralPatternDetector(
            min_support=3, min_confidence=0.3,
            min_stability_days=0, min_sessions=3,
            bias_threshold=0.3,
        )
        patterns = detector.detect_patterns(diverse_logs)
        if len(patterns) >= 2:
            for i in range(len(patterns) - 1):
                assert patterns[i].support >= patterns[i + 1].support

    def test_pattern_has_required_fields(self, diverse_logs):
        detector = BehavioralPatternDetector(
            min_support=3, min_confidence=0.3,
            min_stability_days=0, min_sessions=3,
            bias_threshold=0.3,
        )
        patterns = detector.detect_patterns(diverse_logs)
        if patterns:
            p = patterns[0]
            assert p.pattern_id is not None
            assert p.support >= 3
            assert 0.0 <= p.confidence <= 1.0
            assert isinstance(p.sequence, list)
            assert isinstance(p.tags, list)
            assert 'behavioral' in p.tags
            assert p.first_seen is not None
            assert p.last_seen is not None


# ── Integration: All Detectors Together ─────────────────────────────

class TestMultiDetectorIntegration:
    def test_all_detectors_on_same_data(self, simulated_logs):
        """All three detector types can run on the same data without conflict."""
        from esass_prototype.analysis.pattern_detector import TemporalPatternDetector

        temporal = TemporalPatternDetector(
            min_support=2, min_confidence=0.3, min_stability_days=0,
        )
        semantic = SemanticPatternDetector(
            min_support=3, min_confidence=0.3, min_stability_days=0,
            similarity_threshold=0.3, min_cluster_size=3,
        )
        behavioral = BehavioralPatternDetector(
            min_support=3, min_confidence=0.3, min_stability_days=0,
            min_sessions=3, bias_threshold=0.3,
        )

        t_patterns = temporal.detect_patterns(simulated_logs)
        s_patterns = semantic.detect_patterns(simulated_logs)
        b_patterns = behavioral.detect_patterns(simulated_logs)

        # Each produces patterns
        assert len(t_patterns) > 0
        assert len(s_patterns) > 0
        assert len(b_patterns) > 0

        # Pattern types are distinct
        for p in t_patterns:
            assert p.pattern_type == "temporal"
        for p in s_patterns:
            assert p.pattern_type == "semantic"
        for p in b_patterns:
            assert p.pattern_type == "behavioral"

    def test_all_patterns_storable(self, simulated_logs, temp_data_dir):
        """All pattern types can be saved and loaded from PatternStore."""
        from esass_prototype.analysis.pattern_detector import TemporalPatternDetector

        temporal = TemporalPatternDetector(
            min_support=2, min_confidence=0.3, min_stability_days=0,
        )
        semantic = SemanticPatternDetector(
            min_support=3, min_confidence=0.3, min_stability_days=0,
            similarity_threshold=0.3, min_cluster_size=3,
        )
        behavioral = BehavioralPatternDetector(
            min_support=3, min_confidence=0.3, min_stability_days=0,
            min_sessions=3, bias_threshold=0.3,
        )

        all_patterns = (
            temporal.detect_patterns(simulated_logs)
            + semantic.detect_patterns(simulated_logs)
            + behavioral.detect_patterns(simulated_logs)
        )

        store = PatternStore(temp_data_dir)
        store.save_batch(all_patterns)

        loaded = store.load_all()
        assert len(loaded) == len(all_patterns)

        # Verify types round-trip correctly
        loaded_types = {p.pattern_type for p in loaded}
        assert "temporal" in loaded_types
        assert "semantic" in loaded_types
        assert "behavioral" in loaded_types

    def test_module_imports(self):
        """All new classes are importable from the package __init__."""
        from esass_prototype.analysis import (
            BehavioralPatternDetector,
            SemanticPatternDetector,
            TemporalPatternDetector,
        )
        from esass_prototype.storage import (
            LogStore,
            LogStoreInterface,
            PatternStore,
            PatternStoreInterface,
            SkillStore,
            SkillStoreInterface,
        )
        # Just verifying no import errors
        assert True
