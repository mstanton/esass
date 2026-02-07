import json
import subprocess
import sys
import time
from pathlib import Path


def test_hook_and_cli():
    print("Testing ESASS Hook and CLI Integration...")

    # 1. Simulate a hook call
    hook_path = Path("esass/hooks/esass_hook.py").resolve()

    # Sample tool event
    event = {
        "tool_name": "Read",
        "tool_input": {"file_path": "test_file.py"},
        "tool_output": "def foo(): pass",
        "session_id": "test_session_1",
    }

    print(f"1. Sending event to hook: {hook_path}")
    try:
        process = subprocess.run(
            [sys.executable, str(hook_path)],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            timeout=5,
        )
        if process.returncode == 0:
            print("   [OK] Hook executed successfully")
        else:
            print(f"   [FAIL] Hook failed: {process.stderr}")
            return
    except Exception as e:
        print(f"   [FAIL] Execution error: {e}")
        return

    # 2. Check if event was logged (via CLI tail)
    print("\n2. Verifying with 'esass tail'...")
    try:
        result = subprocess.run(
            ["uv", "run", "esass", "tail", "1"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        output = result.stdout
        if "Read" in output and "test_file.py" in output:
            print("   [OK] Event found in tail output")
            print(f"   Output preview:\n{output.strip()}")
        else:
            print("   [FAIL] Event not found in tail output")
            print(f"   Stdout: {output}")
            print(f"   Stderr: {result.stderr}")

    except Exception as e:
        print(f"   [FAIL] CLI execution error: {e}")


if __name__ == "__main__":
    test_hook_and_cli()
