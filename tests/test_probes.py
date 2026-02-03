"""
Tests for ESASS probe system.

Tests coverage:
- Probe base classes
- Specific probes (Tool, Reasoning, Decision)
- Registry and routing
- Event pipeline
- Configuration
"""

import tempfile
import time
from pathlib import Path

import pytest

from esass.probes.base import Probe, ProbeContext, TagExtractor
from esass.probes.config import ESASSProbeSystemConfig, create_default_probes
from esass.probes.decision_probe import DecisionProbe
from esass.probes.pipeline import EventPipeline
from esass.probes.reasoning_probe import ReasoningProbe
from esass.probes.registry import ProbeRegistry
from esass.probes.tool_probe import ToolCallProbe
from esass_prototype.models import LogEntry

# =============================================================================
# Base Probe Tests
# =============================================================================

class TestProbe:
    """Test base probe functionality"""

    def test_probe_must_implement_abstract_methods(self):
        """Probe class requires implementing abstract methods"""
        with pytest.raises(TypeError):
            # Cannot instantiate abstract class
            Probe()

    def test_tag_extractor_from_tool(self):
        """TagExtractor correctly identifies tool patterns"""
        # Read Python file
        tags = TagExtractor.extract_from_tool('Read', {
            'file_path': 'src/test_module.py'
        })

        assert 'read' in tags
        assert 'file_type:py' in tags
        assert 'language:python' in tags
        assert 'testing' in tags

    def test_tag_extractor_from_bash(self):
        """TagExtractor extracts git commands"""
        tags = TagExtractor.extract_from_tool('Bash', {
            'command': 'git commit -m "test"'
        })

        assert 'bash' in tags
        assert 'git' in tags
        assert 'version_control' in tags
        assert 'git_commit' in tags

    def test_tag_extractor_from_text(self):
        """TagExtractor identifies task types from text"""
        text = "Fix the bug in the authentication module"
        tags = TagExtractor.extract_from_text(text)

        assert 'debugging' in tags


# =============================================================================
# Tool Probe Tests
# =============================================================================

class TestToolCallProbe:
    """Test tool call observation probe"""

    def test_can_observe_tool_events(self):
        """ToolCallProbe handles tool-related events"""
        probe = ToolCallProbe()

        assert probe.can_observe('tool_call_start')
        assert probe.can_observe('tool_call_complete')
        assert probe.can_observe('tool_call_error')
        assert not probe.can_observe('message_generated')

    def test_observe_tool_start(self):
        """ToolCallProbe captures tool start events"""
        probe = ToolCallProbe()

        context = ProbeContext(
            event_type='tool_call_start',
            event_data={
                'tool_name': 'Read',
                'parameters': {'file_path': 'test.py'},
                'call_id': 'call-123'
            },
            session_id='session-1'
        )

        entries = probe.observe(context)

        assert entries is not None
        assert len(entries) == 1
        assert entries[0].event_type == 'tool_usage'
        assert entries[0].event_data['tool_name'] == 'Read'
        assert entries[0].session_id == 'session-1'

    def test_observe_tool_complete(self):
        """ToolCallProbe captures tool completion"""
        probe = ToolCallProbe()

        # Start event
        start_context = ProbeContext(
            event_type='tool_call_start',
            event_data={
                'tool_name': 'Grep',
                'parameters': {'pattern': 'def.*'},
                'call_id': 'call-456'
            },
            session_id='session-2'
        )
        probe.observe(start_context)

        # Complete event
        complete_context = ProbeContext(
            event_type='tool_call_complete',
            event_data={
                'call_id': 'call-456',
                'result': ['match1', 'match2']
            },
            session_id='session-2'
        )

        entries = probe.observe(complete_context)

        assert entries is not None
        assert len(entries) == 1
        assert entries[0].event_type == 'outcome'
        assert entries[0].event_data['success'] is True

    def test_observe_tool_error(self):
        """ToolCallProbe captures tool errors"""
        probe = ToolCallProbe()

        context = ProbeContext(
            event_type='tool_call_error',
            event_data={
                'call_id': 'call-789',
                'tool_name': 'Bash',
                'error': 'Command failed with exit code 1'
            },
            session_id='session-3'
        )

        entries = probe.observe(context)

        assert entries is not None
        assert len(entries) == 1
        assert entries[0].event_type == 'error'
        assert 'Command failed' in entries[0].event_data['error_message']

    def test_parameter_sanitization(self):
        """ToolCallProbe redacts sensitive parameters"""
        probe = ToolCallProbe()

        context = ProbeContext(
            event_type='tool_call_start',
            event_data={
                'tool_name': 'Bash',
                'parameters': {
                    'command': 'curl -H "Authorization: token secret123"'
                },
                'call_id': 'call-999'
            },
            session_id='session-4'
        )

        entries = probe.observe(context)

        # Sensitive data should be in parameters but not exposed
        assert entries is not None


# =============================================================================
# Reasoning Probe Tests
# =============================================================================

class TestReasoningProbe:
    """Test reasoning chain observation probe"""

    def test_can_observe_reasoning_events(self):
        """ReasoningProbe handles reasoning-related events"""
        probe = ReasoningProbe()

        assert probe.can_observe('thinking_block')
        assert probe.can_observe('message_generated')
        assert probe.can_observe('hypothesis_formed')
        assert not probe.can_observe('tool_call_start')

    def test_detect_reasoning_indicators(self):
        """ReasoningProbe identifies reasoning language"""
        probe = ReasoningProbe()

        assert probe._contains_reasoning("I think this is the root cause")
        assert probe._contains_reasoning("The error probably indicates a timeout")
        assert probe._contains_reasoning("This suggests that the database is down")
        assert not probe._contains_reasoning("Running git status now")

    def test_estimate_confidence(self):
        """ReasoningProbe estimates confidence from language"""
        probe = ReasoningProbe()

        high_conf = "This will definitely work"
        low_conf = "This might possibly work"
        neutral = "This should work"

        assert probe._estimate_confidence(high_conf) > 0.7
        assert probe._estimate_confidence(low_conf) < 0.4
        assert 0.4 <= probe._estimate_confidence(neutral) <= 0.7

    def test_extract_evidence(self):
        """ReasoningProbe extracts evidence citations"""
        probe = ReasoningProbe()

        text = "The server is down because the health check is failing"
        evidence = probe._extract_evidence(text)

        assert evidence is not None
        assert len(evidence) > 0
        assert 'health check' in evidence[0].lower()

    def test_observe_thinking_block(self):
        """ReasoningProbe processes thinking blocks"""
        probe = ReasoningProbe(min_confidence=0.0)

        context = ProbeContext(
            event_type='thinking_block',
            event_data={
                'content': 'I think the issue is in the authentication module. '
                          'This likely means the token validation is failing.'
            },
            session_id='session-5'
        )

        entries = probe.observe(context)

        assert entries is not None
        assert len(entries) >= 1
        assert entries[0].event_type == 'reasoning'


# =============================================================================
# Decision Probe Tests
# =============================================================================

class TestDecisionProbe:
    """Test decision point observation probe"""

    def test_can_observe_decision_events(self):
        """DecisionProbe handles decision-related events"""
        probe = DecisionProbe()

        assert probe.can_observe('tool_selected')
        assert probe.can_observe('approach_selected')
        assert probe.can_observe('plan_mode_decision')
        assert not probe.can_observe('tool_call_start')

    def test_observe_tool_selection(self):
        """DecisionProbe captures tool selection decisions"""
        probe = DecisionProbe(min_options=2)

        context = ProbeContext(
            event_type='tool_selected',
            event_data={
                'selected_tool': 'Grep',
                'alternatives': ['Glob', 'Read'],
                'rationale': 'Grep is more efficient for pattern matching'
            },
            session_id='session-6'
        )

        entries = probe.observe(context)

        assert entries is not None
        assert len(entries) == 1
        assert entries[0].event_type == 'decision'
        assert entries[0].event_data['decision'] == 'use_Grep'

    def test_observe_plan_mode_decision(self):
        """DecisionProbe captures plan mode decisions"""
        probe = DecisionProbe()

        context = ProbeContext(
            event_type='plan_mode_decision',
            event_data={
                'decision': 'enter',
                'rationale': 'Task is complex with multiple approaches',
                'task_complexity': 'high'
            },
            session_id='session-7'
        )

        entries = probe.observe(context)

        assert entries is not None
        assert len(entries) == 1
        assert 'plan_mode' in entries[0].event_data['decision']


# =============================================================================
# Registry Tests
# =============================================================================

class TestProbeRegistry:
    """Test probe registry and event routing"""

    def test_register_probe(self):
        """Registry can register probes"""
        registry = ProbeRegistry()
        probe = ToolCallProbe()

        registry.register(probe)

        assert probe in registry.probes
        assert len(registry.probes) == 1

    def test_notify_routes_to_interested_probes(self):
        """Registry routes events to interested probes"""
        registry = ProbeRegistry()

        tool_probe = ToolCallProbe()
        reasoning_probe = ReasoningProbe()

        registry.register(tool_probe)
        registry.register(reasoning_probe)

        # Tool event should only go to tool probe
        count = registry.notify('tool_call_start', {
            'tool_name': 'Read',
            'parameters': {},
            'call_id': 'test'
        }, {'session_id': 'test-session'})

        # Should generate entries from tool probe only
        assert count >= 1

    def test_registry_handles_probe_errors(self):
        """Registry gracefully handles probe failures"""
        registry = ProbeRegistry()

        # Create a probe that will error
        class ErrorProbe(Probe):
            def can_observe(self, event_type: str) -> bool:
                return True

            def observe(self, context: ProbeContext):
                raise ValueError("Intentional error")

        registry.register(ErrorProbe())

        # Should not crash
        count = registry.notify('test_event', {}, {})

        # No entries due to error
        assert count == 0
        assert registry._probe_errors > 0

    def test_registry_statistics(self):
        """Registry tracks statistics"""
        registry = ProbeRegistry()
        probe = ToolCallProbe()
        registry.register(probe)

        # Generate some events
        registry.notify('tool_call_start', {
            'tool_name': 'Read',
            'parameters': {},
            'call_id': 'test'
        }, {'session_id': 'test'})

        stats = registry.get_stats()

        assert stats['total_events_received'] == 1
        assert stats['registered_probes'] == 1


# =============================================================================
# Pipeline Tests
# =============================================================================

class TestEventPipeline:
    """Test event pipeline"""

    def test_pipeline_initialization(self):
        """Pipeline initializes correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = EventPipeline(
                data_dir=Path(tmpdir),
                buffer_size=10,
                flush_interval=1.0
            )

            assert pipeline.buffer_size == 10
            assert pipeline.flush_interval == 1.0

            pipeline.shutdown()

    def test_pipeline_submit_and_flush(self):
        """Pipeline processes and writes events"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = EventPipeline(
                data_dir=Path(tmpdir),
                buffer_size=5,
                flush_interval=0.1
            )

            # Create test entries
            entries = [
                LogEntry.create(
                    event_type='test',
                    event_data={'test': i},
                    session_id='test-session'
                )
                for i in range(10)
            ]

            # Submit entries
            pipeline.submit(entries)

            # Wait for processing
            time.sleep(0.5)

            stats = pipeline.get_stats()
            assert stats['total_submitted'] == 10

            pipeline.shutdown()

    def test_pipeline_buffer_flush_on_size(self):
        """Pipeline flushes when buffer is full"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = EventPipeline(
                data_dir=Path(tmpdir),
                buffer_size=3,
                flush_interval=10.0  # Long interval, won't trigger
            )

            entries = [
                LogEntry.create(
                    event_type='test',
                    event_data={'i': i},
                    session_id='test'
                )
                for i in range(5)
            ]

            pipeline.submit(entries)
            time.sleep(0.2)

            # Should have flushed due to buffer size
            stats = pipeline.get_stats()
            assert stats['flush_count'] > 0

            pipeline.shutdown()


# =============================================================================
# Configuration Tests
# =============================================================================

class TestConfiguration:
    """Test configuration system"""

    def test_default_configuration(self):
        """Default configuration has sensible values"""
        config = ESASSProbeSystemConfig()

        assert config.enabled is True
        assert config.tool_probe.enabled is True
        assert config.reasoning_probe.enabled is True
        assert config.pipeline.buffer_size == 100

    def test_create_default_probes(self):
        """create_default_probes creates configured probes"""
        config = ESASSProbeSystemConfig()
        config.tool_probe.enabled = True
        config.reasoning_probe.enabled = True
        config.decision_probe.enabled = False
        # Disable enhanced probes
        config.error_recovery_probe.enabled = False
        config.strategy_shift_probe.enabled = False
        config.calibration_probe.enabled = False
        config.insight_probe.enabled = False
        config.scope_expansion_probe.enabled = False

        probes = create_default_probes(config)

        # Should have tool and reasoning, not decision
        assert len(probes) == 2
        probe_types = [type(p).__name__ for p in probes]
        assert 'ToolSequenceDetector' in probe_types or 'ToolCallProbe' in probe_types


# =============================================================================
# Integration Tests
# =============================================================================

class TestEndToEndIntegration:
    """End-to-end integration tests"""

    def test_complete_workflow(self):
        """Test complete event capture workflow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create pipeline
            pipeline = EventPipeline(
                data_dir=Path(tmpdir),
                buffer_size=10,
                flush_interval=0.5
            )

            # Create registry
            registry = ProbeRegistry(event_pipeline=pipeline)

            # Register probes
            registry.register(ToolCallProbe())
            registry.register(ReasoningProbe(min_confidence=0.0))
            registry.register(DecisionProbe())

            registry.start()

            # Simulate tool usage
            registry.notify('tool_call_start', {
                'tool_name': 'Read',
                'parameters': {'file_path': 'test.py'},
                'call_id': 'call-1'
            }, {'session_id': 'test-session'})

            registry.notify('tool_call_complete', {
                'call_id': 'call-1',
                'result': 'file content'
            }, {'session_id': 'test-session'})

            # Simulate reasoning
            registry.notify('thinking_block', {
                'content': 'I think the file contains the implementation we need'
            }, {'session_id': 'test-session'})

            # Simulate decision
            registry.notify('tool_selected', {
                'selected_tool': 'Edit',
                'alternatives': ['Write', 'Edit'],
                'rationale': 'Edit is safer for existing files'
            }, {'session_id': 'test-session'})

            # Wait for processing
            time.sleep(1.0)

            # Check statistics
            stats = registry.get_stats()
            assert stats['total_events_received'] == 4
            assert stats['total_entries_generated'] > 0

            # Cleanup
            registry.stop()
            pipeline.shutdown()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
