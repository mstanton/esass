#!/usr/bin/env python3
"""
ESASS Event Simulator
=====================
Simulates Claude Code tool events for testing the dashboard.
"""

import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HOOK_PATH = Path(__file__).parent / "esass_hook.py"

# Realistic tool sequences
WORKFLOWS = [
    # Search -> Read -> Edit workflow
    [
        ("Grep", {"pattern": "class.*Handler"}, "Found 3 files"),
        ("Read", {"file_path": "src/handlers/base.py"}, "class BaseHandler:\n    pass"),
        (
            "Edit",
            {
                "file_path": "src/handlers/base.py",
                "old_string": "pass",
                "new_string": "self.init()",
            },
            "ok",
        ),
    ],
    # File exploration
    [
        ("Glob", {"pattern": "**/*.py", "path": "src/"}, "15 files found"),
        ("Read", {"file_path": "src/main.py"}, "import sys\ndef main(): pass"),
        ("Read", {"file_path": "src/config.py"}, "CONFIG = {}"),
    ],
    # Testing workflow
    [
        (
            "Edit",
            {
                "file_path": "tests/test_main.py",
                "old_string": "assert True",
                "new_string": "assert result == expected",
            },
            "ok",
        ),
        ("Bash", {"command": "pytest tests/ -v"}, "5 passed"),
        (
            "Read",
            {"file_path": "tests/test_main.py"},
            "def test_main(): assert result == expected",
        ),
    ],
    # Git workflow
    [
        ("Bash", {"command": "git status"}, "modified: src/main.py"),
        ("Bash", {"command": "git diff src/main.py"}, "+ new line"),
        (
            "Bash",
            {"command": 'git add src/main.py && git commit -m "fix"'},
            "[main abc123] fix",
        ),
    ],
    # Debug workflow
    [
        ("Grep", {"pattern": "error|exception", "path": "logs/"}, "Found in app.log"),
        ("Read", {"file_path": "logs/app.log"}, "ERROR: Connection failed"),
        ("Grep", {"pattern": "Connection", "path": "src/"}, "src/db.py:45"),
        ("Read", {"file_path": "src/db.py"}, "def connect(): raise ConnectionError"),
        (
            "Edit",
            {
                "file_path": "src/db.py",
                "old_string": "raise",
                "new_string": "retry(3); raise",
            },
            "ok",
        ),
    ],
    # Reliability failure workflow (consecutive failures)
    [
        ("Bash", {"command": "npm install"}, "Error: EACCES", False, "EACCES"),
        ("Bash", {"command": "npm install"}, "Error: EACCES", False, "EACCES"),
        (
            "Bash",
            {"command": "npm install"},
            "Error: EACCES",
            False,
            "EACCES",
        ),  # Should trigger alert
    ],
    # Boundary crossing (CORE zone)
    [
        ("Read", {"file_path": "pyproject.toml"}, '[project]\nname="esass"'),
        (
            "Edit",
            {
                "file_path": "pyproject.toml",
                "old_string": "0.1.0",
                "new_string": "0.2.0",
            },
            "ok",
        ),
    ],
]


def send_event(
    tool_name: str,
    parameters: dict,
    result: str,
    success: bool = True,
    error: str = None,
    session_id: str = "live-session",
):
    """Send event to ESASS hook."""
    event = {
        "tool_name": tool_name,
        "tool_input": parameters,
        "tool_output": result,
        "success": success,
        "error": error,
        "session_id": session_id,
    }

    try:
        proc = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input=json.dumps(event),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return proc.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False


def run_simulation(speed: float = 1.0, loops: int = 0):
    """Run event simulation."""
    print("=" * 60)
    print("  ESASS Event Simulator")
    print("=" * 60)
    print(f"  Speed: {speed}x")
    print(f"  Hook: {HOOK_PATH}")
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    print()

    iteration = 0
    session_id = f"sim-{datetime.now().strftime('%H%M%S')}"

    try:
        while loops == 0 or iteration < loops:
            iteration += 1
            # Force pick failure or boundary workflows (last 2)
            workflow = random.choice(WORKFLOWS[-2:])

            print(
                f"\n[Iteration {iteration}] Running workflow with {len(workflow)} steps..."
            )

            for step in workflow:
                # Handle both legacy (3-part) and new (5-part) workflow steps
                if len(step) == 3:
                    tool_name, params, result = step
                    success_flag, error_text = True, None
                else:
                    tool_name, params, result, success_flag, error_text = step

                # Send event
                hook_success = send_event(
                    tool_name, params, result, success_flag, error_text, session_id
                )
                status = "OK" if hook_success else "FAIL"

                # Display
                target = (
                    params.get("file_path")
                    or params.get("pattern")
                    or params.get("command", "")[:30]
                )
                print(f"  [{status}] {tool_name:10} {target}")

                # Random delay between 0.5-2 seconds (adjusted by speed)
                delay = random.uniform(0.5, 2.0) / speed
                time.sleep(delay)

            # Pause between workflows
            time.sleep(1.0 / speed)

    except KeyboardInterrupt:
        print(f"\n\nSimulation stopped after {iteration} iterations.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ESASS Event Simulator")
    parser.add_argument(
        "--speed", "-s", type=float, default=1.0, help="Speed multiplier (default: 1.0)"
    )
    parser.add_argument(
        "--loops", "-l", type=int, default=0, help="Number of loops (0=infinite)"
    )

    args = parser.parse_args()
    run_simulation(speed=args.speed, loops=args.loops)
