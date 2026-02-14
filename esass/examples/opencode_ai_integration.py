"""
Example: Integrating ESASS Probes with open-code-ai

This module demonstrates how to integrate the ESASS probe system
with open-code-ai to capture real execution events.

Installation:
    1. Copy this file to your open-code-ai integration directory
    2. Modify open-code-ai action execution to call probe hooks
    3. Configure environment variables for ESASS

Usage:
    # Initialize ESASS system
    from examples.opencode_ai_integration import initialize_esass_integration

    registry, pipeline = initialize_esass_integration()

    # In open-code-ai action execution:
    from examples.opencode_ai_integration import notify_action_start

    notify_action_start('file_edit', {'path': 'test.py'}, context)
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from esass.probes.config import ESASSProbeSystemConfig, initialize_system
from esass.probes.registry import ProbeRegistry, global_registry

logger = logging.getLogger(__name__)


# =============================================================================
# Integration Initialization
# =============================================================================

def initialize_esass_integration(
    data_dir: Optional[Path] = None,
    config: Optional[ESASSProbeSystemConfig] = None
) -> tuple:
    """
    Initialize ESASS integration with open-code-ai.

    Args:
        data_dir: Optional data directory (uses config if None)
        config: Optional custom configuration

    Returns:
        Tuple of (registry, pipeline, config)
    """
    # Load configuration from environment or use provided
    if config is None:
        config = ESASSProbeSystemConfig.from_env()

    # Override data directory if provided
    if data_dir:
        config.storage.data_dir = data_dir

    # Initialize system
    registry, pipeline, config = initialize_system(config)

    if registry:
        logger.info("ESASS integration with open-code-ai initialized successfully")
        logger.info(f"Data directory: {config.storage.data_dir}")
        logger.info(f"Registered probes: {len(registry.probes)}")
    else:
        logger.warning("ESASS integration disabled")

    return registry, pipeline, config


# =============================================================================
# open-code-ai Hook Functions
# =============================================================================

# Map open-code-ai actions to ESASS tool names
ACTION_TO_TOOL_MAP = {
    'file_read': 'Read',
    'file_write': 'Write',
    'file_edit': 'Edit',
    'command_run': 'Bash',
    'search_files': 'Grep',
    'list_files': 'Glob',
    'ask_followup_question': 'AskUserQuestion',
    'attempt_completion': 'CompleteTask',
    'web_search': 'WebSearch',
}


def notify_action_start(
    action: str,
    parameters: Dict[str, Any],
    context: Dict[str, Any],
    registry: Optional[ProbeRegistry] = None
) -> Optional[str]:
    """
    Notify ESASS of action start.

    Call this hook at the beginning of action execution in open-code-ai.

    Args:
        action: Name of action (file_read, file_edit, command_run, etc.)
        parameters: Action parameters
        context: Execution context (session_id, task_id, etc.)
        registry: Optional registry (uses global if None)

    Returns:
        Call ID for tracking completion

    Example:
        # In open-code-ai action executor:
        call_id = notify_action_start(
            action='file_edit',
            parameters={'path': 'src/main.py', 'content': '...'},
            context={'session_id': session_id}
        )
    """
    if registry is None:
        registry = global_registry

    import uuid
    call_id = str(uuid.uuid4())

    # Map action to tool name
    tool_name = ACTION_TO_TOOL_MAP.get(action, action)

    registry.notify('tool_call_start', {
        'tool_name': tool_name,
        'parameters': parameters,
        'call_id': call_id,
        'original_action': action  # Preserve original action name
    }, context)

    return call_id


def notify_action_complete(
    call_id: str,
    result: Any,
    context: Dict[str, Any],
    registry: Optional[ProbeRegistry] = None
) -> None:
    """
    Notify ESASS of successful action completion.

    Call this hook after action execution succeeds.

    Args:
        call_id: ID from notify_action_start
        result: Action result
        context: Execution context
        registry: Optional registry

    Example:
        # In open-code-ai action executor:
        try:
            result = execute_action(action, params)
            notify_action_complete(call_id, result, context)
        except Exception as e:
            notify_action_error(call_id, e, context)
    """
    if registry is None:
        registry = global_registry

    registry.notify('tool_call_complete', {
        'call_id': call_id,
        'result': result
    }, context)


def notify_action_error(
    call_id: str,
    error: Exception,
    context: Dict[str, Any],
    registry: Optional[ProbeRegistry] = None
) -> None:
    """
    Notify ESASS of action execution error.

    Call this hook when action execution fails.

    Args:
        call_id: ID from notify_action_start
        error: Exception that occurred
        context: Execution context
        registry: Optional registry
    """
    if registry is None:
        registry = global_registry

    registry.notify('tool_call_error', {
        'call_id': call_id,
        'error': error,
        'tool_name': context.get('tool_name', 'unknown')
    }, context)


def notify_thinking(
    thinking: str,
    context: Dict[str, Any],
    registry: Optional[ProbeRegistry] = None
) -> None:
    """
    Notify ESASS of AI thinking/reasoning.

    Call this hook when open-code-ai produces thinking/planning output.

    Args:
        thinking: Thinking content
        context: Execution context
        registry: Optional registry

    Example:
        # In open-code-ai reasoning module:
        thinking = generate_plan(task)
        notify_thinking(thinking, context)
    """
    if registry is None:
        registry = global_registry

    registry.notify('thinking_block', {
        'content': thinking
    }, context)


def notify_response(
    response: str,
    context: Dict[str, Any],
    registry: Optional[ProbeRegistry] = None
) -> None:
    """
    Notify ESASS of response generation.

    Call this hook when open-code-ai generates a response message.

    Args:
        response: Response message text
        context: Execution context
        registry: Optional registry
    """
    if registry is None:
        registry = global_registry

    registry.notify('message_generated', {
        'message': response
    }, context)


def notify_action_decision(
    selected_action: str,
    alternatives: List[str],
    rationale: str,
    context: Dict[str, Any],
    registry: Optional[ProbeRegistry] = None
) -> None:
    """
    Notify ESASS of an action selection decision.

    Call this hook when open-code-ai chooses between multiple possible actions.

    Args:
        selected_action: The action that was selected
        alternatives: Other actions that were considered
        rationale: Reason for selecting this action
        context: Execution context
        registry: Optional registry

    Example:
        # When choosing between editing and rewriting:
        notify_action_decision(
            selected_action='file_edit',
            alternatives=['file_write', 'file_edit'],
            rationale='Edit preserves formatting and is safer',
            context=context
        )
    """
    if registry is None:
        registry = global_registry

    # Map action to tool name
    tool_name = ACTION_TO_TOOL_MAP.get(selected_action, selected_action)
    alt_tools = [ACTION_TO_TOOL_MAP.get(a, a) for a in alternatives]

    registry.notify('tool_selected', {
        'selected_tool': tool_name,
        'alternatives': alt_tools,
        'rationale': rationale,
        'original_action': selected_action
    }, context)


# =============================================================================
# open-code-ai Action Wrapper
# =============================================================================

class ESASSActionWrapper:
    """
    Wrapper for open-code-ai actions that automatically logs to ESASS.

    Example:
        # Wrap existing action executor
        original_executor = OpenCodeAIActionExecutor()
        wrapped_executor = ESASSActionWrapper(original_executor)

        # Use wrapped executor - automatically logs to ESASS
        result = wrapped_executor.execute('file_edit', {'path': 'test.py', ...}, context)
    """

    def __init__(self, action_executor, registry: Optional[ProbeRegistry] = None):
        """
        Initialize wrapper.

        Args:
            action_executor: Original action executor to wrap
            registry: Optional ESASS registry
        """
        self.action_executor = action_executor
        self.registry = registry or global_registry

    def execute(self, action: str, parameters: Dict[str, Any],
                context: Dict[str, Any]) -> Any:
        """
        Execute action with ESASS observation.

        Args:
            action: Action to execute
            parameters: Action parameters
            context: Execution context

        Returns:
            Action result
        """
        # Notify start
        call_id = notify_action_start(
            action, parameters, context, self.registry
        )

        try:
            # Execute action
            result = self.action_executor.execute(action, parameters, context)

            # Notify success
            notify_action_complete(call_id, result, context, self.registry)

            return result

        except Exception as e:
            # Notify error
            notify_action_error(call_id, e, context, self.registry)
            raise


# =============================================================================
# Example: Mock open-code-ai Integration
# =============================================================================

def example_simulated_session():
    """
    Simulate an open-code-ai session with ESASS observation.

    This demonstrates the complete integration workflow.
    """
    import time

    print("=" * 70)
    print("ESASS open-code-ai Integration Example")
    print("=" * 70)

    # Initialize ESASS
    print("\n[1] Initializing ESASS integration...")
    registry, pipeline, config = initialize_esass_integration(
        data_dir=Path('./data_opencode')
    )

    if not registry:
        print("ESASS integration disabled")
        return

    # Simulate session context
    context = {'session_id': 'opencode-session-001', 'task_id': 'task-123'}

    print(f"\n[2] Starting simulated open-code-ai session: {context['session_id']}")
    print("-" * 70)

    # Simulate: User asks to implement a feature
    print("\nUser: Can you implement user authentication in auth.py?")
    print("AI: I'll implement user authentication with password hashing.")

    # Thinking block
    notify_thinking(
        thinking="I need to implement authentication. I should:\n"
                "1. Read the existing auth.py file\n"
                "2. Add password hashing with bcrypt\n"
                "3. Implement login/logout functions\n"
                "4. Add session management",
        context=context,
        registry=registry
    )
    print("[OK] Thinking: Planned implementation strategy")

    # Action: Read file
    call_id_1 = notify_action_start(
        action='file_read',
        parameters={'path': 'auth.py'},
        context=context,
        registry=registry
    )
    time.sleep(0.1)  # Simulate execution

    notify_action_complete(
        call_id=call_id_1,
        result="# Existing auth.py content\nfrom flask import Flask",
        context=context,
        registry=registry
    )
    print("[OK] Action: Read auth.py [SUCCESS]")

    # Decision: Edit vs Rewrite
    notify_action_decision(
        selected_action='file_edit',
        alternatives=['file_write', 'file_edit'],
        rationale='File exists and has imports, editing is safer',
        context=context,
        registry=registry
    )
    print("[OK] Decision: Choose file_edit over file_write")

    # Action: Edit file
    call_id_2 = notify_action_start(
        action='file_edit',
        parameters={
            'path': 'auth.py',
            'diff': '+ import bcrypt\n+ def hash_password(password):\n+     return bcrypt.hashpw(password, bcrypt.gensalt())'
        },
        context=context,
        registry=registry
    )
    time.sleep(0.1)

    notify_action_complete(
        call_id=call_id_2,
        result={'success': True, 'lines_changed': 3},
        context=context,
        registry=registry
    )
    print("[OK] Action: Edit auth.py [SUCCESS]")

    # Response
    notify_response(
        response="I've added password hashing with bcrypt to auth.py. "
                "The hash_password function securely hashes passwords using salt.",
        context=context,
        registry=registry
    )
    print("[OK] Response: Explained implementation")

    print("\n" + "-" * 70)
    print("\nUser: Can you add a test for this?")
    print("AI: I'll create a test file with password hashing tests.")

    # Action: Create test file
    call_id_3 = notify_action_start(
        action='file_write',
        parameters={
            'path': 'test_auth.py',
            'content': 'import pytest\nimport bcrypt\nfrom auth import hash_password\n\ndef test_hash_password():\n    ...'
        },
        context=context,
        registry=registry
    )
    time.sleep(0.1)

    notify_action_complete(
        call_id=call_id_3,
        result={'success': True, 'file_created': 'test_auth.py'},
        context=context,
        registry=registry
    )
    print("[OK] Action: Write test_auth.py [SUCCESS]")

    # Action: Run tests
    call_id_4 = notify_action_start(
        action='command_run',
        parameters={'command': 'pytest test_auth.py -v'},
        context=context,
        registry=registry
    )
    time.sleep(0.1)

    notify_action_complete(
        call_id=call_id_4,
        result={'exit_code': 0, 'output': 'test_auth.py::test_hash_password PASSED'},
        context=context,
        registry=registry
    )
    print("[OK] Action: Run pytest [SUCCESS]")

    # Wait for processing
    print("\n[3] Processing events...")
    time.sleep(0.5)

    # Show statistics
    print("\n[4] ESASS Statistics:")
    print("-" * 70)
    stats = registry.get_stats()
    print(f"Events received: {stats['total_events_received']}")
    print(f"Log entries generated: {stats['total_entries_generated']}")
    print(f"Active probes: {stats['registered_probes']}")

    print("\nProbe details:")
    for probe_name, probe_stats in stats['probes'].items():
        print(f"  - {probe_name}: {probe_stats['observations']} observations")

    # Flush and cleanup
    print("\n[5] Flushing pipeline...")
    registry.flush()
    time.sleep(0.5)

    pipeline_stats = pipeline.get_stats()
    print(f"Events written to storage: {pipeline_stats['total_written']}")
    print(f"Data directory: {config.storage.data_dir}")

    # Shutdown
    print("\n[6] Shutting down...")
    registry.stop()
    pipeline.shutdown()

    print("\n" + "=" * 70)
    print("Example complete! Check data_opencode/ for captured events.")
    print("=" * 70)


# =============================================================================
# Example: open-code-ai Integration Patch
# =============================================================================

INTEGRATION_PATCH_EXAMPLE = """
# Example: How to patch open-code-ai for ESASS integration

## 1. In action execution pipeline:

```python
# Before (original code):
def execute_action(action: str, parameters: dict, context: dict):
    result = action_implementations[action](parameters)
    return result

# After (with ESASS):
from examples.opencode_ai_integration import (
    notify_action_start,
    notify_action_complete,
    notify_action_error
)

def execute_action(action: str, parameters: dict, context: dict):
    # ESASS: Notify start
    call_id = notify_action_start(action, parameters, context)

    try:
        result = action_implementations[action](parameters)

        # ESASS: Notify success
        notify_action_complete(call_id, result, context)

        return result
    except Exception as e:
        # ESASS: Notify error
        notify_action_error(call_id, e, context)
        raise
```

## 2. In thinking/planning module:

```python
# Before:
def plan_task(task: str, context: dict) -> Plan:
    thinking = generate_thinking(task)
    plan = create_plan(thinking)
    return plan

# After:
from examples.opencode_ai_integration import notify_thinking

def plan_task(task: str, context: dict) -> Plan:
    thinking = generate_thinking(task)

    # ESASS: Capture thinking
    notify_thinking(thinking, context)

    plan = create_plan(thinking)
    return plan
```

## 3. In response generation:

```python
# Before:
def generate_response(plan: Plan, context: dict) -> str:
    response = format_response(plan)
    return response

# After:
from examples.opencode_ai_integration import notify_response

def generate_response(plan: Plan, context: dict) -> str:
    response = format_response(plan)

    # ESASS: Capture response
    notify_response(response, context)

    return response
```

## 4. In action selection:

```python
# When choosing between multiple actions:
from examples.opencode_ai_integration import notify_action_decision

def select_action(task: str, context: dict) -> str:
    options = ['file_edit', 'file_write', 'command_run']
    selected = choose_best_action(task, options)

    # ESASS: Log decision
    notify_action_decision(
        selected_action=selected,
        alternatives=[o for o in options if o != selected],
        rationale=f'Best action for {task}',
        context=context
    )

    return selected
```

## 5. Environment configuration:

```bash
# Enable ESASS
export ESASS_ENABLED=true

# Configure data directory
export ESASS_DATA_DIR=/path/to/esass/data

# Configure probes
export ESASS_TOOL_PROBE_ENABLED=true
export ESASS_REASONING_PROBE_ENABLED=true
export ESASS_DECISION_PROBE_ENABLED=true

# Pipeline settings
export ESASS_BUFFER_SIZE=100
export ESASS_FLUSH_INTERVAL=5.0

# Logging
export ESASS_LOG_LEVEL=INFO
```

## 6. Action Mapping:

The integration automatically maps open-code-ai actions to ESASS tool names:

- `file_read` → Read
- `file_write` → Write
- `file_edit` → Edit
- `command_run` → Bash
- `search_files` → Grep
- `list_files` → Glob
- `ask_followup_question` → AskUserQuestion
- `attempt_completion` → CompleteTask
- `web_search` → WebSearch

This ensures compatibility with existing ESASS probe system.
"""


if __name__ == '__main__':
    # Run example
    example_simulated_session()

    # Print integration instructions
    print("\n\n" + INTEGRATION_PATCH_EXAMPLE)
