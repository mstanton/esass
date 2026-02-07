"""
Example: Integrating ESASS Probes with Claude Code

This module demonstrates how to integrate the ESASS probe system
with Claude Code to capture real execution events.

Installation:
    1. Copy this file to your Claude Code integration directory
    2. Modify Claude Code tool execution to call probe hooks
    3. Configure environment variables for ESASS

Usage:
    # Initialize ESASS system
    from examples.claude_code_integration import initialize_esass_integration

    registry, pipeline = initialize_esass_integration()

    # In Claude Code tool execution:
    from examples.claude_code_integration import notify_tool_call_start

    notify_tool_call_start('Read', {'file_path': 'test.py'}, context)
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

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
    Initialize ESASS integration with Claude Code.

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
        logger.info("ESASS integration initialized successfully")
        logger.info(f"Data directory: {config.storage.data_dir}")
        logger.info(f"Registered probes: {len(registry.probes)}")
    else:
        logger.warning("ESASS integration disabled")

    return registry, pipeline, config


# =============================================================================
# Claude Code Hook Functions
# =============================================================================

def notify_tool_call_start(
    tool_name: str,
    parameters: Dict[str, Any],
    context: Dict[str, Any],
    registry: Optional[ProbeRegistry] = None
) -> Optional[str]:
    """
    Notify ESASS of tool call start.

    Call this hook at the beginning of tool execution in Claude Code.

    Args:
        tool_name: Name of tool being called (Read, Write, Bash, etc.)
        parameters: Tool parameters
        context: Execution context (conversation_id, etc.)
        registry: Optional registry (uses global if None)

    Returns:
        Call ID for tracking completion

    Example:
        # In Claude Code tool executor:
        call_id = notify_tool_call_start(
            tool_name='Read',
            parameters={'file_path': '/path/to/file.py'},
            context={'conversation_id': conv_id}
        )
    """
    if registry is None:
        registry = global_registry

    import uuid
    call_id = str(uuid.uuid4())

    registry.notify('tool_call_start', {
        'tool_name': tool_name,
        'parameters': parameters,
        'call_id': call_id
    }, context)

    return call_id


def notify_tool_call_complete(
    call_id: str,
    result: Any,
    context: Dict[str, Any],
    registry: Optional[ProbeRegistry] = None
) -> None:
    """
    Notify ESASS of successful tool completion.

    Call this hook after tool execution succeeds.

    Args:
        call_id: ID from notify_tool_call_start
        result: Tool result
        context: Execution context
        registry: Optional registry

    Example:
        # In Claude Code tool executor:
        try:
            result = execute_tool(tool_name, params)
            notify_tool_call_complete(call_id, result, context)
        except Exception as e:
            notify_tool_call_error(call_id, e, context)
    """
    if registry is None:
        registry = global_registry

    registry.notify('tool_call_complete', {
        'call_id': call_id,
        'result': result
    }, context)


def notify_tool_call_error(
    call_id: str,
    error: Exception,
    context: Dict[str, Any],
    registry: Optional[ProbeRegistry] = None
) -> None:
    """
    Notify ESASS of tool execution error.

    Call this hook when tool execution fails.

    Args:
        call_id: ID from notify_tool_call_start
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


def notify_message_generated(
    message: str,
    context: Dict[str, Any],
    registry: Optional[ProbeRegistry] = None
) -> None:
    """
    Notify ESASS of message generation.

    Call this hook when Claude generates a message.

    Args:
        message: Generated message text
        context: Execution context
        registry: Optional registry

    Example:
        # In Claude Code message generator:
        message = generate_response(prompt)
        notify_message_generated(message, context)
    """
    if registry is None:
        registry = global_registry

    registry.notify('message_generated', {
        'message': message
    }, context)


def notify_thinking_block(
    thinking: str,
    context: Dict[str, Any],
    registry: Optional[ProbeRegistry] = None
) -> None:
    """
    Notify ESASS of thinking block.

    Call this hook when Claude produces a thinking block.

    Args:
        thinking: Thinking block content
        context: Execution context
        registry: Optional registry
    """
    if registry is None:
        registry = global_registry

    registry.notify('thinking_block', {
        'content': thinking
    }, context)


def notify_decision_made(
    decision: str,
    options: list,
    rationale: str,
    context: Dict[str, Any],
    registry: Optional[ProbeRegistry] = None
) -> None:
    """
    Notify ESASS of a decision point.

    Call this hook when Claude makes a significant decision.

    Args:
        decision: The decision made
        options: Alternative options considered
        rationale: Reason for decision
        context: Execution context
        registry: Optional registry

    Example:
        # When choosing between tools:
        notify_decision_made(
            decision='use_Grep',
            options=['Grep', 'Glob', 'Read'],
            rationale='Grep is more efficient for regex search',
            context=context
        )
    """
    if registry is None:
        registry = global_registry

    registry.notify('tool_selected', {
        'selected_tool': decision.replace('use_', ''),
        'alternatives': [opt for opt in options if opt != decision],
        'rationale': rationale
    }, context)


# =============================================================================
# Claude Code Tool Wrapper
# =============================================================================

class ESASSToolWrapper:
    """
    Wrapper for Claude Code tools that automatically logs to ESASS.

    Example:
        # Wrap existing tool executor
        original_executor = ClaudeToolExecutor()
        wrapped_executor = ESASSToolWrapper(original_executor)

        # Use wrapped executor - automatically logs to ESASS
        result = wrapped_executor.execute('Read', {'file_path': 'test.py'}, context)
    """

    def __init__(self, tool_executor, registry: Optional[ProbeRegistry] = None):
        """
        Initialize wrapper.

        Args:
            tool_executor: Original tool executor to wrap
            registry: Optional ESASS registry
        """
        self.tool_executor = tool_executor
        self.registry = registry or global_registry

    def execute(self, tool_name: str, parameters: Dict[str, Any],
                context: Dict[str, Any]) -> Any:
        """
        Execute tool with ESASS observation.

        Args:
            tool_name: Tool to execute
            parameters: Tool parameters
            context: Execution context

        Returns:
            Tool result
        """
        # Notify start
        call_id = notify_tool_call_start(
            tool_name, parameters, context, self.registry
        )

        try:
            # Execute tool
            result = self.tool_executor.execute(tool_name, parameters, context)

            # Notify success
            notify_tool_call_complete(call_id, result, context, self.registry)

            return result

        except Exception as e:
            # Notify error
            notify_tool_call_error(call_id, e, context, self.registry)
            raise


# =============================================================================
# Example: Mock Claude Code Integration
# =============================================================================

def example_simulated_session():
    """
    Simulate a Claude Code session with ESASS observation.

    This demonstrates the complete integration workflow.
    """
    import time

    print("=" * 70)
    print("ESASS Claude Code Integration Example")
    print("=" * 70)

    # Initialize ESASS
    print("\n[1] Initializing ESASS integration...")
    registry, pipeline, config = initialize_esass_integration(
        data_dir=Path('./data_example')
    )

    if not registry:
        print("ESASS integration disabled")
        return

    # Simulate conversation context
    context = {'conversation_id': 'example-session-001'}

    print(f"\n[2] Starting simulated Claude Code session: {context['conversation_id']}")
    print("-" * 70)

    # Simulate: User asks to read a file
    print("\nUser: Can you read src/main.py?")
    print("Claude: I'll read that file for you.")

    # Tool call: Read
    call_id_1 = notify_tool_call_start(
        tool_name='Read',
        parameters={'file_path': 'src/main.py'},
        context=context,
        registry=registry
    )
    time.sleep(0.1)  # Simulate execution

    notify_tool_call_complete(
        call_id=call_id_1,
        result="def main():\n    print('Hello')",
        context=context,
        registry=registry
    )
    print("[OK] Tool: Read src/main.py [SUCCESS]")

    # Thinking block
    notify_thinking_block(
        thinking="I see the file contains a simple main function. "
                "The user probably wants to understand what it does.",
        context=context,
        registry=registry
    )
    print("[OK] Thinking: Analyzed file content")

    # Message generation
    notify_message_generated(
        message="The file contains a main() function that prints 'Hello'.",
        context=context,
        registry=registry
    )
    print("[OK] Response: Explained file contents")

    print("\n" + "-" * 70)
    print("\nUser: Can you add error handling?")
    print("Claude: I'll add try-except error handling.")

    # Decision: Edit vs Write
    notify_decision_made(
        decision='Edit',
        options=['Edit', 'Write'],
        rationale='Edit is safer for existing files',
        context=context,
        registry=registry
    )
    print("[OK] Decision: Choose Edit over Write")

    # Tool call: Edit
    call_id_2 = notify_tool_call_start(
        tool_name='Edit',
        parameters={
            'file_path': 'src/main.py',
            'old_string': 'def main():',
            'new_string': 'def main():\n    try:'
        },
        context=context,
        registry=registry
    )
    time.sleep(0.1)

    notify_tool_call_complete(
        call_id=call_id_2,
        result={'success': True},
        context=context,
        registry=registry
    )
    print("[OK] Tool: Edit src/main.py [SUCCESS]")

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
    print("Example complete! Check data_example/ for captured events.")
    print("=" * 70)


# =============================================================================
# Example: Claude Code Integration Patch
# =============================================================================

INTEGRATION_PATCH_EXAMPLE = """
# Example: How to patch Claude Code for ESASS integration

## 1. In tool execution pipeline (wherever tools are executed):

```python
# Before (original code):
def execute_tool(tool_name: str, parameters: dict, context: dict):
    result = tool_implementations[tool_name](parameters)
    return result

# After (with ESASS):
from examples.claude_code_integration import notify_tool_call_start, notify_tool_call_complete, notify_tool_call_error

def execute_tool(tool_name: str, parameters: dict, context: dict):
    # ESASS: Notify start
    call_id = notify_tool_call_start(tool_name, parameters, context)

    try:
        result = tool_implementations[tool_name](parameters)

        # ESASS: Notify success
        notify_tool_call_complete(call_id, result, context)

        return result
    except Exception as e:
        # ESASS: Notify error
        notify_tool_call_error(call_id, e, context)
        raise
```

## 2. In message generation:

```python
# Before:
def generate_message(prompt: str, context: dict) -> str:
    message = model.generate(prompt)
    return message

# After:
from examples.claude_code_integration import notify_message_generated

def generate_message(prompt: str, context: dict) -> str:
    message = model.generate(prompt)

    # ESASS: Capture message
    notify_message_generated(message, context)

    return message
```

## 3. In thinking block processing:

```python
# If Claude produces thinking blocks:
from examples.claude_code_integration import notify_thinking_block

def process_thinking(thinking_content: str, context: dict):
    # ESASS: Capture thinking
    notify_thinking_block(thinking_content, context)

    # Continue processing...
```

## 4. Environment configuration:

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
"""


if __name__ == '__main__':
    # Run example
    example_simulated_session()

    # Print integration instructions
    print("\n\n" + INTEGRATION_PATCH_EXAMPLE)
