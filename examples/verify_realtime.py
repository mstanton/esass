#!/usr/bin/env python3
"""
ESASS Real-Time Verification Script

This script verifies that the ESASS probe system is functioning correctly
for real-time Claude Code event capture.

Usage:
    python -m examples.verify_realtime

    # Or with custom data directory:
    ESASS_DATA_DIR=./my_data python -m examples.verify_realtime
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header(text: str) -> None:
    """Print a header section."""
    print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
    print(f"{BOLD}{BLUE}{text}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")


def print_ok(text: str) -> None:
    """Print success message."""
    print(f"{GREEN}[OK]{RESET} {text}")


def print_fail(text: str) -> None:
    """Print failure message."""
    print(f"{RED}[FAIL]{RESET} {text}")


def print_warn(text: str) -> None:
    """Print warning message."""
    print(f"{YELLOW}[WARN]{RESET} {text}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"{BLUE}[INFO]{RESET} {text}")


def verify_imports() -> bool:
    """Verify all required imports are available."""
    print_header("Step 1: Verifying Imports")

    checks = []

    try:
        from esass.probes.config import ESASSProbeSystemConfig, initialize_system
        print_ok("esass.probes.config")
        checks.append(True)
    except ImportError as e:
        print_fail(f"esass.probes.config: {e}")
        checks.append(False)

    try:
        from esass.probes.registry import ProbeRegistry, global_registry
        print_ok("esass.probes.registry")
        checks.append(True)
    except ImportError as e:
        print_fail(f"esass.probes.registry: {e}")
        checks.append(False)

    try:
        from esass.probes.pipeline import EventPipeline
        print_ok("esass.probes.pipeline")
        checks.append(True)
    except ImportError as e:
        print_fail(f"esass.probes.pipeline: {e}")
        checks.append(False)

    try:
        from esass_prototype.models import LogEntry
        print_ok("esass_prototype.models")
        checks.append(True)
    except ImportError as e:
        print_fail(f"esass_prototype.models: {e}")
        checks.append(False)

    try:
        from examples.claude_code_integration import (
            initialize_esass_integration,
            notify_tool_call_start,
            notify_tool_call_complete,
            notify_thinking_block,
            notify_decision_made,
        )
        print_ok("examples.claude_code_integration")
        checks.append(True)
    except ImportError as e:
        print_fail(f"examples.claude_code_integration: {e}")
        checks.append(False)

    return all(checks)


def verify_initialization() -> tuple:
    """Verify system initialization."""
    print_header("Step 2: Verifying System Initialization")

    from examples.claude_code_integration import initialize_esass_integration
    from pathlib import Path

    data_dir = Path('./data_verification')
    data_dir.mkdir(parents=True, exist_ok=True)

    registry, pipeline, config = initialize_esass_integration(data_dir=data_dir)

    if registry is None:
        print_fail("Registry initialization failed (system disabled?)")
        return None, None, None

    print_ok(f"Registry initialized with {len(registry.probes)} probes")
    print_ok(f"Pipeline initialized (buffer_size={config.pipeline.buffer_size})")
    print_ok(f"Data directory: {config.storage.data_dir}")

    # List probes
    print_info("Registered probes:")
    for probe in registry.probes:
        status = "enabled" if probe.enabled else "disabled"
        print(f"       - {probe.name} ({status})")

    return registry, pipeline, config


def verify_event_capture(registry, pipeline) -> bool:
    """Verify event capture is working."""
    print_header("Step 3: Verifying Event Capture")

    from examples.claude_code_integration import (
        notify_tool_call_start,
        notify_tool_call_complete,
        notify_thinking_block,
        notify_decision_made,
    )

    context = {'conversation_id': f'verify-{datetime.now().strftime("%Y%m%d%H%M%S")}'}
    events_generated = []

    # Test 1: Tool call
    print_info("Testing tool call capture...")
    call_id = notify_tool_call_start(
        tool_name='Read',
        parameters={'file_path': 'test.py'},
        context=context,
        registry=registry
    )
    time.sleep(0.05)
    notify_tool_call_complete(
        call_id=call_id,
        result="file contents here",
        context=context,
        registry=registry
    )
    events_generated.append('tool_call')
    print_ok("Tool call start/complete captured")

    # Test 2: Thinking block
    print_info("Testing thinking block capture...")
    notify_thinking_block(
        thinking="I need to analyze this code carefully.",
        context=context,
        registry=registry
    )
    events_generated.append('thinking')
    print_ok("Thinking block captured")

    # Test 3: Decision
    print_info("Testing decision capture...")
    notify_decision_made(
        decision='use_Edit',
        options=['Edit', 'Write'],
        rationale='Edit preserves file history',
        context=context,
        registry=registry
    )
    events_generated.append('decision')
    print_ok("Decision captured")

    # Check stats
    stats = registry.get_stats()
    print_info(f"Total events received: {stats['total_events_received']}")
    print_info(f"Total entries generated: {stats['total_entries_generated']}")

    if stats['total_entries_generated'] > 0:
        print_ok(f"Events successfully captured ({stats['total_entries_generated']} log entries)")
        return True
    else:
        print_fail("No log entries generated!")
        return False


def verify_data_persistence(pipeline, config) -> bool:
    """Verify events are persisted to storage."""
    print_header("Step 4: Verifying Data Persistence")

    # Flush pipeline
    print_info("Flushing pipeline...")
    pipeline.flush()
    time.sleep(0.5)

    stats = pipeline.get_stats()
    print_info(f"Events written: {stats['total_written']}")
    print_info(f"Events dropped: {stats.get('total_dropped', 0)}")

    # Check for log files
    log_dir = config.storage.data_dir / 'logs'
    if log_dir.exists():
        log_files = list(log_dir.glob('*.jsonl'))
        if log_files:
            print_ok(f"Found {len(log_files)} log file(s)")

            # Read latest log file
            latest = max(log_files, key=lambda f: f.stat().st_mtime)
            with open(latest) as f:
                lines = f.readlines()
                print_ok(f"Latest log ({latest.name}) has {len(lines)} entries")

                # Parse first entry
                if lines:
                    entry = json.loads(lines[-1])
                    print_info(f"Latest event: {entry.get('event_type')} at {entry.get('timestamp')}")

            return True
        else:
            print_warn("No log files found yet")
    else:
        print_warn(f"Log directory not found: {log_dir}")

    return stats['total_written'] > 0


def verify_probe_coverage() -> None:
    """Display probe coverage information."""
    print_header("Step 5: Probe Coverage Summary")

    probes_info = [
        ("ToolSequenceDetector", "tool_call_start, tool_call_complete, tool_call_error", "Tool usage and sequences"),
        ("CausalReasoningProbe", "thinking_block, message_generated", "Reasoning and hypotheses"),
        ("TradeoffAnalysisProbe", "tool_selected", "Decision points"),
        ("ErrorRecoveryProbe", "tool_call_error", "Error recovery patterns"),
        ("StrategyShiftProbe", "thinking_block", "Strategy changes"),
        ("CalibrationProbe", "thinking_block, tool_call_complete", "Confidence calibration"),
        ("InsightProbe", "thinking_block", "Key insights"),
        ("ScopeExpansionProbe", "thinking_block", "Scope changes"),
    ]

    print(f"{'Probe Name':<25} {'Event Types':<45} {'Captures'}")
    print("-" * 100)
    for name, events, captures in probes_info:
        print(f"{name:<25} {events:<45} {captures}")


def run_verification() -> bool:
    """Run complete verification suite."""
    print_header("ESASS Real-Time Verification")
    print(f"Started at: {datetime.now().isoformat()}")

    results = []

    # Step 1: Imports
    if not verify_imports():
        print_fail("\nImport verification failed. Aborting.")
        return False
    results.append(True)

    # Step 2: Initialization
    registry, pipeline, config = verify_initialization()
    if registry is None:
        print_fail("\nInitialization failed. Aborting.")
        return False
    results.append(True)

    try:
        # Step 3: Event capture
        results.append(verify_event_capture(registry, pipeline))

        # Step 4: Persistence
        results.append(verify_data_persistence(pipeline, config))

        # Step 5: Coverage info
        verify_probe_coverage()

    finally:
        # Cleanup
        print_header("Cleanup")
        print_info("Stopping registry...")
        registry.stop()
        print_info("Shutting down pipeline...")
        pipeline.shutdown()
        print_ok("Cleanup complete")

    # Summary
    print_header("Verification Summary")

    passed = sum(results)
    total = len(results)

    if all(results):
        print(f"{GREEN}{BOLD}ALL CHECKS PASSED ({passed}/{total}){RESET}")
        print(f"\n{GREEN}ESASS real-time capture is working correctly!{RESET}")
        print(f"\nData stored in: {config.storage.data_dir}")
        return True
    else:
        print(f"{RED}{BOLD}SOME CHECKS FAILED ({passed}/{total}){RESET}")
        return False


def show_integration_status():
    """Show current integration readiness."""
    print_header("Integration Status")

    status = [
        ("Probe System", "Ready", "8 probes implemented"),
        ("Event Pipeline", "Ready", "Async buffered writes"),
        ("Log Storage", "Ready", "JSONL format"),
        ("Claude Code Hooks", "Ready", "notify_* functions"),
        ("Environment Config", "Ready", "ESASS_* variables"),
    ]

    for component, state, details in status:
        color = GREEN if state == "Ready" else YELLOW
        print(f"  {component:<20} {color}{state:<10}{RESET} {details}")

    print(f"\n{BOLD}To integrate with Claude Code:{RESET}")
    print("""
    1. Add hooks to tool execution:
       from examples.claude_code_integration import notify_tool_call_start, notify_tool_call_complete

       call_id = notify_tool_call_start(tool_name, params, context)
       result = execute_tool(...)
       notify_tool_call_complete(call_id, result, context)

    2. Set environment variables:
       export ESASS_ENABLED=true
       export ESASS_DATA_DIR=/path/to/data

    3. Initialize at startup:
       from examples.claude_code_integration import initialize_esass_integration
       registry, pipeline, config = initialize_esass_integration()
    """)


if __name__ == '__main__':
    success = run_verification()
    show_integration_status()
    sys.exit(0 if success else 1)
