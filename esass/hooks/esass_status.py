#!/usr/bin/env python3
"""
ESASS Status Display
====================
Shows synchronization status for Claude Code sessions.
"""

import json
import os
import sys
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

# Unicode support
UNICODE_OK = sys.stdout.encoding and sys.stdout.encoding.lower() in ('utf-8', 'utf8')

# Symbols
CHECK = '✓' if UNICODE_OK else '[OK]'
CROSS = '✗' if UNICODE_OK else '[X]'
BULLET = '●' if UNICODE_OK else '*'
CIRCLE = '○' if UNICODE_OK else 'o'
ARROW = '→' if UNICODE_OK else '->'
SYNC = '⟳' if UNICODE_OK else '~'

# Colors
class C:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


def check_hook_configured():
    """Check if the ESASS hook is configured in hooks.json."""
    hooks_file = CLAUDE_CONFIG_DIR / 'hooks.json'
    if not hooks_file.exists():
        return False, "hooks.json not found"

    try:
        with open(hooks_file, 'r') as f:
            config = json.load(f)

        hooks = config.get('hooks', {})
        post_tool_use = hooks.get('PostToolUse', [])

        for hook in post_tool_use:
            cmd = hook.get('command', '')
            if 'esass' in cmd.lower():
                return True, cmd

        return False, "ESASS hook not found in PostToolUse"
    except Exception as e:
        return False, f"Error reading hooks.json: {e}"


def check_data_directory():
    """Check if ESASS data directory exists and is writable."""
    if not ESASS_DATA_DIR.exists():
        try:
            ESASS_DATA_DIR.mkdir(parents=True, exist_ok=True)
            return True, "Created"
        except:
            return False, "Cannot create"
    return True, "Ready"


def get_today_event_count():
    """Get the number of events logged today."""
    today = datetime.now().strftime('%Y%m%d')
    log_file = ESASS_DATA_DIR / 'logs' / f'log_{today}.jsonl'

    if not log_file.exists():
        return 0

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f)
    except:
        return 0


def get_pattern_count():
    """Get the number of tracked patterns."""
    seq_file = ESASS_DATA_DIR / 'state' / 'sequence_state.json'

    if not seq_file.exists():
        return 0

    try:
        with open(seq_file, 'r') as f:
            data = json.load(f)
            return len(data.get('sequences', {}))
    except:
        return 0


def get_skill_candidate_count():
    """Get number of skill candidates (patterns with 5+ occurrences)."""
    seq_file = ESASS_DATA_DIR / 'state' / 'sequence_state.json'

    if not seq_file.exists():
        return 0

    try:
        with open(seq_file, 'r') as f:
            data = json.load(f)
            sequences = data.get('sequences', {})
            return sum(1 for count in sequences.values() if count >= 5)
    except:
        return 0


def display_sync_status(minimal=False):
    """Display ESASS synchronization status."""

    # Check components
    hook_ok, hook_info = check_hook_configured()
    data_ok, data_info = check_data_directory()

    events = get_today_event_count()
    patterns = get_pattern_count()
    skills = get_skill_candidate_count()

    all_ok = hook_ok and data_ok

    if minimal:
        # One-line status for embedding in prompts
        if all_ok:
            status = f"{C.GREEN}{CHECK} ESASS{C.RESET}"
            if events > 0:
                status += f" {C.DIM}[{events} events, {patterns} patterns]"
            return status + C.RESET
        else:
            return f"{C.YELLOW}{CIRCLE} ESASS not configured{C.RESET}"

    # Full status display
    print()

    if all_ok:
        # Success banner
        print(f"  {C.GREEN}╭{'─' * 50}╮{C.RESET}")
        print(f"  {C.GREEN}│{C.RESET}  {C.BOLD}{C.GREEN}{CHECK} ESASS SYNCHRONIZED{C.RESET}                           {C.GREEN}│{C.RESET}")
        print(f"  {C.GREEN}╰{'─' * 50}╯{C.RESET}")
    else:
        # Warning banner
        print(f"  {C.YELLOW}╭{'─' * 50}╮{C.RESET}")
        print(f"  {C.YELLOW}│{C.RESET}  {C.BOLD}{C.YELLOW}{SYNC} ESASS CONFIGURING...{C.RESET}                        {C.YELLOW}│{C.RESET}")
        print(f"  {C.YELLOW}╰{'─' * 50}╯{C.RESET}")

    print()

    # Component status
    print(f"  {C.BOLD}Components{C.RESET}")

    # Hook status
    if hook_ok:
        print(f"  {C.GREEN}{CHECK}{C.RESET} Hook configured")
    else:
        print(f"  {C.RED}{CROSS}{C.RESET} Hook: {hook_info}")

    # Data directory
    if data_ok:
        print(f"  {C.GREEN}{CHECK}{C.RESET} Data directory ready")
    else:
        print(f"  {C.RED}{CROSS}{C.RESET} Data: {data_info}")

    print()

    # Metrics (only if we have data)
    if events > 0 or patterns > 0:
        print(f"  {C.BOLD}Session Metrics{C.RESET}")
        print(f"  {C.CYAN}{BULLET}{C.RESET} Events today:     {events}")
        print(f"  {C.CYAN}{BULLET}{C.RESET} Patterns tracked: {patterns}")
        print(f"  {C.CYAN}{BULLET}{C.RESET} Skills forming:   {skills}")
        print()

    # Field status indicator
    if all_ok:
        if skills > 0:
            trust = min(100, 20 + skills * 10)
            print(f"  {C.BOLD}Protection Field{C.RESET}")
            bar_width = 30
            filled = int(trust / 100 * bar_width)
            bar = f"{C.GREEN}{'█' * filled}{C.DIM}{'░' * (bar_width - filled)}{C.RESET}"
            print(f"  Trust: [{bar}] {trust}%")
            print()

    # Quick actions if not configured
    if not all_ok:
        print(f"  {C.BOLD}Quick Setup{C.RESET}")
        print(f"  Run: {C.CYAN}python esass_cli.py setup{C.RESET}")
        print()

    return all_ok


def get_status_line():
    """Get a compact status line for embedding."""
    hook_ok, _ = check_hook_configured()
    data_ok, _ = check_data_directory()

    events = get_today_event_count()
    patterns = get_pattern_count()
    skills = get_skill_candidate_count()

    if hook_ok and data_ok:
        parts = [f"{C.GREEN}{CHECK} ESASS{C.RESET}"]

        if events > 0:
            parts.append(f"{events}ev")
        if patterns > 0:
            parts.append(f"{patterns}pat")
        if skills > 0:
            parts.append(f"{skills}sk")

        if len(parts) > 1:
            return parts[0] + f" {C.DIM}[" + "/".join(parts[1:]) + f"]{C.RESET}"
        return parts[0]
    else:
        return f"{C.YELLOW}{CIRCLE} ESASS{C.RESET}"


def get_status_dict():
    """Get status as a dictionary for programmatic use."""
    hook_ok, hook_info = check_hook_configured()
    data_ok, data_info = check_data_directory()

    return {
        'synchronized': hook_ok and data_ok,
        'hook_configured': hook_ok,
        'hook_info': hook_info,
        'data_ready': data_ok,
        'data_info': data_info,
        'events_today': get_today_event_count(),
        'patterns': get_pattern_count(),
        'skill_candidates': get_skill_candidate_count(),
        'timestamp': datetime.now().isoformat()
    }


# ASCII art logo for full display
ESASS_LOGO = f"""
{C.CYAN}  ███████╗███████╗ █████╗ ███████╗███████╗
  ██╔════╝██╔════╝██╔══██╗██╔════╝██╔════╝
  █████╗  ███████╗███████║███████╗███████╗
  ██╔══╝  ╚════██║██╔══██║╚════██║╚════██║
  ███████╗███████║██║  ██║███████║███████║
  ╚══════╝╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝{C.RESET}
{C.DIM}  Emergent Self-Adaptive Skill System{C.RESET}
"""


def display_banner():
    """Display the full ESASS banner with status."""
    print(ESASS_LOGO)
    display_sync_status()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='ESASS Status Display')
    parser.add_argument('--minimal', '-m', action='store_true', help='Minimal one-line output')
    parser.add_argument('--line', '-l', action='store_true', help='Single status line')
    parser.add_argument('--json', '-j', action='store_true', help='JSON output')
    parser.add_argument('--banner', '-b', action='store_true', help='Full banner with logo')

    args = parser.parse_args()

    if args.json:
        print(json.dumps(get_status_dict(), indent=2))
    elif args.line:
        print(get_status_line())
    elif args.minimal:
        print(display_sync_status(minimal=True))
    elif args.banner:
        display_banner()
    else:
        display_sync_status()
