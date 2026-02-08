#!/usr/bin/env python3
"""
ESASS Session Start Hook

Automatically launches the ESASS dashboard in a new terminal window
when a Claude Code session starts or continues.
"""

import os
import subprocess
import sys
from pathlib import Path

# Dashboard script location
HOOKS_DIR = Path(__file__).parent
DASHBOARD_SCRIPT = HOOKS_DIR / "esass_dashboard.py"
DASHBOARD_BAT = HOOKS_DIR / "esass_dashboard.bat"

# Lock file to prevent multiple dashboards
LOCK_FILE = Path.home() / ".esass" / "dashboard.lock"


def is_dashboard_running():
    """Check if dashboard is already running via lock file."""
    if not LOCK_FILE.exists():
        return False

    try:
        # Check if lock file is stale (older than 1 hour)
        import time
        age = time.time() - LOCK_FILE.stat().st_mtime
        if age > 3600:  # 1 hour
            LOCK_FILE.unlink()
            return False
        return True
    except Exception:
        return False


def create_lock():
    """Create lock file to indicate dashboard is running."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.write_text(str(os.getpid()))


def launch_dashboard():
    """Launch dashboard in a new terminal window."""
    if sys.platform == "win32":
        # Windows: use start command to open new terminal
        if DASHBOARD_BAT.exists():
            subprocess.Popen(
                ["cmd", "/c", "start", "ESASS Dashboard", str(DASHBOARD_BAT)],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                shell=True
            )
        else:
            subprocess.Popen(
                ["cmd", "/c", "start", "ESASS Dashboard", "python", str(DASHBOARD_SCRIPT)],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                shell=True
            )
    else:
        # Unix/Linux/Mac: try common terminal emulators
        terminals = [
            ["gnome-terminal", "--", "python3", str(DASHBOARD_SCRIPT)],
            ["xterm", "-e", f"python3 {DASHBOARD_SCRIPT}"],
            ["konsole", "-e", f"python3 {DASHBOARD_SCRIPT}"],
        ]

        for term_cmd in terminals:
            try:
                subprocess.Popen(term_cmd, start_new_session=True)
                break
            except FileNotFoundError:
                continue


def main():
    """Main entry point for session start hook."""
    # Check if dashboard already running
    if is_dashboard_running():
        # Just touch the lock file to update timestamp
        LOCK_FILE.touch()
        return

    # Launch dashboard
    try:
        create_lock()
        launch_dashboard()
        print("\033[92m✓ ESASS Dashboard launched\033[0m")
    except Exception as e:
        print(f"\033[93m⚠ Could not launch dashboard: {e}\033[0m")


if __name__ == "__main__":
    main()
