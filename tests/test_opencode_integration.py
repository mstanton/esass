"""
Tests for open-code-ai integration.

Tests coverage:
- Action notification hooks
- Action wrapper
- Action to tool mapping
- Integration initialization
"""

import tempfile
import time
from pathlib import Path

import pytest

from esass.probes.registry import ProbeRegistry
from esass.probes.pipeline import EventPipeline
from esass.probes.tool_probe import ToolCallProbe


# Mock open-code-ai action executor
class MockActionExecutor:
    """Mock action executor for testing"""

    def execute(self, action: str, parameters: dict, context: dict):
        """Simulate action execution"""
        if action == 'file_read':
            return "file content"
        elif action == 'file_edit':
            return {'success': True, 'lines_changed': 5}
        elif action == 'command_run':
            return {'exit_code': 0, 'output': 'success'}
        else:
            return {'success': True}


# =============================================================================
# Integration Tests
# =============================================================================

class TestOpenCodeIntegration:
    """Test open-code-ai integration hooks"""

    def test_initialize_integration(self):
        """Integration initializes correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from examples.opencode_ai_integration import initialize_esass_integration

            registry, pipeline, config = initialize_esass_integration(
                data_dir=Path(tmpdir)
            )

            assert registry is not None
            assert pipeline is not None
            assert config is not None
            assert len(registry.probes) > 0

            # Cleanup
            registry.stop()
            pipeline.shutdown()

    def test_action_start_notification(self):
        """notify_action_start creates proper event"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from examples.opencode_ai_integration import (
                initialize_esass_integration,
                notify_action_start
            )

            registry, pipeline, config = initialize_esass_integration(
                data_dir=Path(tmpdir)
            )

            context = {'session_id': 'test-session'}

            # Notify action start
            call_id = notify_action_start(
                action='file_read',
                parameters={'path': 'test.py'},
                context=context,
                registry=registry
            )

            assert call_id is not None
            assert isinstance(call_id, str)

            # Cleanup
            registry.stop()
            pipeline.shutdown()

    def test_action_complete_notification(self):
        """notify_action_complete logs success"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from examples.opencode_ai_integration import (
                initialize_esass_integration,
                notify_action_start,
                notify_action_complete
            )

            registry, pipeline, config = initialize_esass_integration(
                data_dir=Path(tmpdir)
            )

            context = {'session_id': 'test-session'}

            # Start and complete action
            call_id = notify_action_start(
                action='file_write',
                parameters={'path': 'output.txt', 'content': 'data'},
                context=context,
                registry=registry
            )

            notify_action_complete(
                call_id=call_id,
                result={'success': True},
                context=context,
                registry=registry
            )

            # Wait for processing
            time.sleep(0.1)

            # Cleanup
            registry.stop()
            pipeline.shutdown()

    def test_action_error_notification(self):
        """notify_action_error logs failure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from examples.opencode_ai_integration import (
                initialize_esass_integration,
                notify_action_start,
                notify_action_error
            )

            registry, pipeline, config = initialize_esass_integration(
                data_dir=Path(tmpdir)
            )

            context = {'session_id': 'test-session'}

            # Start action
            call_id = notify_action_start(
                action='command_run',
                parameters={'command': 'invalid_cmd'},
                context=context,
                registry=registry
            )

            # Notify error
            error = ValueError("Command failed")
            notify_action_error(
                call_id=call_id,
                error=error,
                context=context,
                registry=registry
            )

            # Wait for processing
            time.sleep(0.1)

            # Cleanup
            registry.stop()
            pipeline.shutdown()

    def test_thinking_notification(self):
        """notify_thinking captures reasoning"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from examples.opencode_ai_integration import (
                initialize_esass_integration,
                notify_thinking
            )

            registry, pipeline, config = initialize_esass_integration(
                data_dir=Path(tmpdir)
            )

            context = {'session_id': 'test-session'}

            # Notify thinking
            notify_thinking(
                thinking="I think I should read the file first to understand the structure",
                context=context,
                registry=registry
            )

            # Wait for processing
            time.sleep(0.1)

            # Cleanup
            registry.stop()
            pipeline.shutdown()

    def test_response_notification(self):
        """notify_response captures AI responses"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from examples.opencode_ai_integration import (
                initialize_esass_integration,
                notify_response
            )

            registry, pipeline, config = initialize_esass_integration(
                data_dir=Path(tmpdir)
            )

            context = {'session_id': 'test-session'}

            # Notify response
            notify_response(
                response="I've successfully edited the file with the requested changes.",
                context=context,
                registry=registry
            )

            # Wait for processing
            time.sleep(0.1)

            # Cleanup
            registry.stop()
            pipeline.shutdown()

    def test_action_decision_notification(self):
        """notify_action_decision logs decision-making"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from examples.opencode_ai_integration import (
                initialize_esass_integration,
                notify_action_decision
            )

            registry, pipeline, config = initialize_esass_integration(
                data_dir=Path(tmpdir)
            )

            context = {'session_id': 'test-session'}

            # Notify decision
            notify_action_decision(
                selected_action='file_edit',
                alternatives=['file_write', 'file_edit'],
                rationale='Editing is safer than rewriting',
                context=context,
                registry=registry
            )

            # Wait for processing
            time.sleep(0.1)

            # Cleanup
            registry.stop()
            pipeline.shutdown()


class TestActionMapping:
    """Test action to tool mapping"""

    def test_action_to_tool_mapping(self):
        """Actions map correctly to tool names"""
        from examples.opencode_ai_integration import ACTION_TO_TOOL_MAP

        assert ACTION_TO_TOOL_MAP['file_read'] == 'Read'
        assert ACTION_TO_TOOL_MAP['file_write'] == 'Write'
        assert ACTION_TO_TOOL_MAP['file_edit'] == 'Edit'
        assert ACTION_TO_TOOL_MAP['command_run'] == 'Bash'
        assert ACTION_TO_TOOL_MAP['search_files'] == 'Grep'
        assert ACTION_TO_TOOL_MAP['list_files'] == 'Glob'

    def test_unmapped_actions_pass_through(self):
        """Unmapped actions use original name"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from examples.opencode_ai_integration import (
                initialize_esass_integration,
                notify_action_start
            )

            registry, pipeline, config = initialize_esass_integration(
                data_dir=Path(tmpdir)
            )

            context = {'session_id': 'test-session'}

            # Use unmapped action
            call_id = notify_action_start(
                action='custom_action',
                parameters={},
                context=context,
                registry=registry
            )

            assert call_id is not None

            # Cleanup
            registry.stop()
            pipeline.shutdown()


class TestActionWrapper:
    """Test ESASS action wrapper"""

    def test_wrapper_executes_action(self):
        """Wrapper successfully executes wrapped action"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from examples.opencode_ai_integration import (
                ESASSActionWrapper,
                initialize_esass_integration
            )

            registry, pipeline, config = initialize_esass_integration(
                data_dir=Path(tmpdir)
            )

            # Create wrapper
            executor = MockActionExecutor()
            wrapped = ESASSActionWrapper(executor, registry)

            # Execute action
            context = {'session_id': 'test-session'}
            result = wrapped.execute(
                'file_read',
                {'path': 'test.py'},
                context
            )

            assert result == "file content"

            # Cleanup
            registry.stop()
            pipeline.shutdown()

    def test_wrapper_logs_to_esass(self):
        """Wrapper logs events to ESASS"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from examples.opencode_ai_integration import (
                ESASSActionWrapper,
                initialize_esass_integration
            )

            registry, pipeline, config = initialize_esass_integration(
                data_dir=Path(tmpdir)
            )

            # Create wrapper
            executor = MockActionExecutor()
            wrapped = ESASSActionWrapper(executor, registry)

            # Execute action
            context = {'session_id': 'test-session'}
            wrapped.execute('file_edit', {'path': 'test.py'}, context)

            # Wait for events to process
            time.sleep(0.2)

            # Check statistics
            stats = registry.get_stats()
            assert stats['total_events_received'] > 0

            # Cleanup
            registry.stop()
            pipeline.shutdown()

    def test_wrapper_handles_errors(self):
        """Wrapper logs errors and re-raises"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from examples.opencode_ai_integration import (
                ESASSActionWrapper,
                initialize_esass_integration
            )

            class FailingExecutor:
                def execute(self, action, parameters, context):
                    raise ValueError("Action failed")

            registry, pipeline, config = initialize_esass_integration(
                data_dir=Path(tmpdir)
            )

            # Create wrapper with failing executor
            executor = FailingExecutor()
            wrapped = ESASSActionWrapper(executor, registry)

            # Execute should raise error
            context = {'session_id': 'test-session'}
            with pytest.raises(ValueError, match="Action failed"):
                wrapped.execute('file_read', {}, context)

            # Wait for events
            time.sleep(0.1)

            # Error should be logged
            stats = registry.get_stats()
            assert stats['total_events_received'] > 0

            # Cleanup
            registry.stop()
            pipeline.shutdown()


class TestEndToEndWorkflow:
    """End-to-end integration tests"""

    def test_complete_action_workflow(self):
        """Test complete action lifecycle"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from examples.opencode_ai_integration import (
                initialize_esass_integration,
                notify_action_start,
                notify_action_complete,
                notify_thinking,
                notify_response
            )

            registry, pipeline, config = initialize_esass_integration(
                data_dir=Path(tmpdir)
            )

            context = {'session_id': 'test-session', 'task_id': 'task-001'}

            # Simulate thinking
            notify_thinking(
                "I should first read the file to understand its structure",
                context, registry
            )

            # Execute action
            call_id = notify_action_start(
                'file_read',
                {'path': 'config.json'},
                context, registry
            )

            notify_action_complete(
                call_id,
                '{"setting": "value"}',
                context, registry
            )

            # Generate response
            notify_response(
                "I've read the config file. It contains one setting.",
                context, registry
            )

            # Wait for processing
            time.sleep(0.3)

            # Verify events were captured
            stats = registry.get_stats()
            assert stats['total_events_received'] >= 3
            assert stats['total_entries_generated'] > 0

            # Cleanup
            registry.stop()
            pipeline.shutdown()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
