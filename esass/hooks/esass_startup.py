#!/usr/bin/env python3
"""
ESASS Session Startup Launcher
==============================
Automatically launches ESASS monitoring tools when Claude Code session starts.

Checks if:
1. ESASS observer is configured and running
2. Dashboard is not already open
Then launches monitoring tools in separate terminal windows.
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Enable UTF-8 and ANSI on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
except:
    pass

# Configuration
ESASS_DATA_DIR = Path(os.environ.get('ESASS_DATA_DIR', Path.home() / '.esass' / 'data'))
CLAUDE_CONFIG_DIR = Path.home() / '.claude'
STATE_DIR = ESASS_DATA_DIR / 'state'
HOOKS_DIR = Path(__file__).parent

# Lock file to prevent duplicate launches
DASHBOARD_LOCK = STATE_DIR / 'dashboard.lock'

# Colors
class C:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    DIM = '\033[2m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def check_esass_configured():
    """Check if ESASS hook is configured in Claude Code."""
    hooks_file = CLAUDE_CONFIG_DIR / 'hooks.json'
    if not hooks_file.exists():
        return False, "No hooks.json"

    try:
        with open(hooks_file, 'r') as f:
            config = json.load(f)

        hooks = config.get('hooks', {})
        post_tool_use = hooks.get('PostToolUse', [])

        for hook in post_tool_use:
            cmd = hook.get('command', '')
            if 'esass' in cmd.lower():
                return True, "ESASS hook active"

        return False, "ESASS hook not found"
    except Exception as e:
        return False, str(e)


def is_dashboard_running():
    """Check if dashboard is already running (via lock file)."""
    if not DASHBOARD_LOCK.exists():
        return False

    try:
        with open(DASHBOARD_LOCK, 'r') as f:
            data = json.load(f)

        # Check if lock is stale (older than 5 minutes)
        lock_time = datetime.fromisoformat(data.get('timestamp', '2000-01-01'))
        age_seconds = (datetime.now() - lock_time).total_seconds()

        if age_seconds > 300:  # 5 minutes
            DASHBOARD_LOCK.unlink()
            return False

        # Check if process is still running (Windows)
        pid = data.get('pid')
        if pid:
            try:
                import psutil
                if not psutil.pid_exists(pid):
                    DASHBOARD_LOCK.unlink()
                    return False
            except ImportError:
                pass  # psutil not available, trust lock file

        return True
    except:
        return False


def create_dashboard_lock(pid=None):
    """Create lock file to indicate dashboard is running."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(DASHBOARD_LOCK, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'pid': pid
        }, f)


def launch_dashboard():
    """Launch the ESASS unified dashboard in a new terminal."""
    dashboard_script = HOOKS_DIR / 'esass_dashboard.py'
    dashboard_bat = HOOKS_DIR / 'esass_dashboard.bat'

    if not dashboard_script.exists():
        return False, "Dashboard script not found"

    try:
        if sys.platform == 'win32':
            # Use the batch file if available
            if dashboard_bat.exists():
                proc = subprocess.Popen(
                    ['start', '', str(dashboard_bat)],
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                proc = subprocess.Popen(
                    ['start', 'cmd', '/k', 'python', str(dashboard_script)],
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            create_dashboard_lock(proc.pid if proc else None)
            return True, "Dashboard launched"
        else:
            # Unix/Mac - try common terminal emulators
            terminals = [
                ['gnome-terminal', '--', 'python3', str(dashboard_script)],
                ['xterm', '-e', 'python3', str(dashboard_script)],
                ['konsole', '-e', 'python3', str(dashboard_script)],
            ]
            for term_cmd in terminals:
                try:
                    proc = subprocess.Popen(term_cmd, start_new_session=True)
                    create_dashboard_lock(proc.pid)
                    return True, "Dashboard launched"
                except FileNotFoundError:
                    continue
            return False, "No terminal emulator found"
    except Exception as e:
        return False, str(e)


def get_session_stats():
    """Get current session statistics."""
    today = datetime.now().strftime('%Y%m%d')
    log_file = ESASS_DATA_DIR / 'logs' / f'log_{today}.jsonl'

    events = 0
    if log_file.exists():
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                events = sum(1 for _ in f)
        except:
            pass

    patterns = 0
    skills = 0
    seq_file = STATE_DIR / 'sequence_state.json'
    if seq_file.exists():
        try:
            with open(seq_file, 'r') as f:
                data = json.load(f)
                sequences = data.get('sequences', {})
                patterns = len(sequences)
                skills = sum(1 for c in sequences.values() if c >= 5)
        except:
            pass

    return events, patterns, skills


def startup(auto_launch=True, quiet=False):
    """
    Run ESASS session startup.

    Args:
        auto_launch: If True, automatically launch dashboard if not running
        quiet: If True, minimal output (just status line)

    Returns:
        dict with status information
    """
    is_configured, config_msg = check_esass_configured()
    events, patterns, skills = get_session_stats()
    dashboard_running = is_dashboard_running()

    result = {
        'configured': is_configured,
        'config_message': config_msg,
        'events': events,
        'patterns': patterns,
        'skills': skills,
        'dashboard_running': dashboard_running,
        'dashboard_launched': False
    }

    # Auto-launch dashboard if configured and not running
    if auto_launch and is_configured and not dashboard_running:
        success, launch_msg = launch_dashboard()
        result['dashboard_launched'] = success
        result['launch_message'] = launch_msg

    # Output
    if quiet:
        # Single line status
        if is_configured:
            status = f"{C.GREEN}[OK]{C.RESET}"
            dash = f"{C.GREEN}[DASH]{C.RESET}" if (dashboard_running or result['dashboard_launched']) else f"{C.DIM}[no dash]{C.RESET}"
            print(f"ESASS {status} {dash} {C.DIM}[{events}ev/{patterns}pat/{skills}sk]{C.RESET}")
        else:
            print(f"ESASS {C.YELLOW}[NOT CONFIGURED]{C.RESET}")
    else:
        # Full startup banner
        print()
        if is_configured:
            print(f"  {C.GREEN}{'=' * 50}{C.RESET}")
            print(f"  {C.BOLD}{C.GREEN}ESASS OBSERVER ACTIVE{C.RESET}")
            print(f"  {C.GREEN}{'=' * 50}{C.RESET}")
            print()
            print(f"  {C.CYAN}Events:{C.RESET}   {events}")
            print(f"  {C.CYAN}Patterns:{C.RESET} {patterns}")
            print(f"  {C.CYAN}Skills:{C.RESET}   {skills}")
            print()

            if result['dashboard_launched']:
                print(f"  {C.GREEN}Dashboard launched in new terminal{C.RESET}")
            elif dashboard_running:
                print(f"  {C.DIM}Dashboard already running{C.RESET}")
            else:
                print(f"  {C.DIM}Run: python hooks/esass_dashboard.py{C.RESET}")
            print()
        else:
            print(f"  {C.YELLOW}ESASS not configured: {config_msg}{C.RESET}")
            print(f"  {C.DIM}Run: python esass_cli.py setup{C.RESET}")
            print()

    return result


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='ESASS Session Startup')
    parser.add_argument('--no-launch', action='store_true',
                       help='Do not auto-launch dashboard')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Quiet mode (single line output)')
    parser.add_argument('--json', action='store_true',
                       help='Output as JSON')

    args = parser.parse_args()

    result = startup(
        auto_launch=not args.no_launch,
        quiet=args.quiet
    )

    if args.json:
        print(json.dumps(result, indent=2))
