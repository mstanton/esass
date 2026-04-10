#!/usr/bin/env python3
"""
ESASS Session Start Hook

Automatically launches the ESASS dashboard in a new terminal window
when a Claude Code session starts or continues.

Run via: python -m esass.hooks.session_start
"""

import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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
    """Launch dashboard in a new terminal window using python -m."""
    python = sys.executable
    dashboard_cmd = [python, "-m", "esass.hooks.dashboard"]

    if sys.platform == "win32":
        subprocess.Popen(
            ["cmd", "/c", "start", "ESASS Dashboard"] + dashboard_cmd,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            shell=True,
        )
    else:
        terminals = [
            ["gnome-terminal", "--"] + dashboard_cmd,
            ["xterm", "-e"] + dashboard_cmd,
            ["konsole", "-e"] + dashboard_cmd,
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
        print("\033[92m[OK] ESASS Dashboard launched\033[0m")
    except Exception as e:
        print(f"\033[93m[WARN] Could not launch dashboard: {e}\033[0m")


if __name__ == "__main__":
    main()
