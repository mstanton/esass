#!/usr/bin/env python3
"""
ESASS Notification System
=========================
Provides visual notifications for ESASS synchronization events.

Can be used:
1. As a startup check when Claude Code session begins
2. As a flash notification when events are captured
3. As a toast notification on Windows
"""

import json
import os
import sys
import time
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
SYNC = '⟳' if UNICODE_OK else '~'
BULLET = '●' if UNICODE_OK else '*'

# Colors
class C:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

    # Special effects
    BLINK = '\033[5m'
    REVERSE = '\033[7m'

    # Background
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'


def check_esass_configured():
    """Check if ESASS hook is configured."""
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
                return True, "Hook configured"

        return False, "ESASS hook not in PostToolUse"
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
    seq_file = ESASS_DATA_DIR / 'state' / 'sequence_state.json'
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


def flash_sync_notification():
    """Display a brief flash notification for sync status."""
    is_configured, msg = check_esass_configured()
    events, patterns, skills = get_session_stats()

    if is_configured:
        # Green flash for synced
        print(f"\r{C.BG_GREEN}{C.WHITE}{C.BOLD} {CHECK} ESASS SYNC {C.RESET}", end='', flush=True)
        time.sleep(0.3)
        print(f"\r{C.GREEN}{CHECK} ESASS{C.RESET} {C.DIM}[{events}ev/{patterns}pat/{skills}sk]{C.RESET}   ", flush=True)
    else:
        # Yellow flash for not configured
        print(f"\r{C.BG_YELLOW}{C.WHITE}{C.BOLD} {SYNC} ESASS SETUP {C.RESET}", end='', flush=True)
        time.sleep(0.3)
        print(f"\r{C.YELLOW}{SYNC} ESASS{C.RESET} {C.DIM}[{msg}]{C.RESET}   ", flush=True)


def display_startup_banner():
    """Display the ESASS startup banner for Claude Code sessions."""
    is_configured, msg = check_esass_configured()
    events, patterns, skills = get_session_stats()

    # Compact startup banner
    print()

    if is_configured:
        # Synchronized state
        print(f"  {C.GREEN}┌{'─' * 56}┐{C.RESET}")
        print(f"  {C.GREEN}│{C.RESET} {C.BOLD}{C.GREEN}{CHECK} ESASS SYNCHRONIZED{C.RESET}                                {C.GREEN}│{C.RESET}")
        print(f"  {C.GREEN}│{C.RESET}   {C.DIM}Protection field active • Observing tool usage{C.RESET}     {C.GREEN}│{C.RESET}")

        if events > 0:
            trust = min(100, 20 + skills * 5)
            bar_width = 20
            filled = int(trust / 100 * bar_width)
            bar = f"{C.GREEN}{'█' * filled}{C.DIM}{'░' * (bar_width - filled)}{C.RESET}"
            print(f"  {C.GREEN}│{C.RESET}   Trust: [{bar}] {trust:3}%                  {C.GREEN}│{C.RESET}")
            print(f"  {C.GREEN}│{C.RESET}   {C.CYAN}{events:,}{C.RESET} events │ {C.CYAN}{patterns}{C.RESET} patterns │ {C.CYAN}{skills}{C.RESET} skills forming  {C.GREEN}│{C.RESET}")
        else:
            print(f"  {C.GREEN}│{C.RESET}   {C.DIM}Waiting for first events...{C.RESET}                        {C.GREEN}│{C.RESET}")

        print(f"  {C.GREEN}└{'─' * 56}┘{C.RESET}")
    else:
        # Not configured state
        print(f"  {C.YELLOW}┌{'─' * 56}┐{C.RESET}")
        print(f"  {C.YELLOW}│{C.RESET} {C.BOLD}{C.YELLOW}{SYNC} ESASS OBSERVER{C.RESET}                                    {C.YELLOW}│{C.RESET}")
        print(f"  {C.YELLOW}│{C.RESET}   {C.DIM}Status: {msg}{C.RESET}{' ' * (40 - len(msg))}{C.YELLOW}│{C.RESET}")
        print(f"  {C.YELLOW}│{C.RESET}   {C.DIM}Run: python esass_cli.py setup{C.RESET}                      {C.YELLOW}│{C.RESET}")
        print(f"  {C.YELLOW}└{'─' * 56}┘{C.RESET}")

    print()


def display_inline_status():
    """Display a single-line inline status (for embedding in prompts)."""
    is_configured, _ = check_esass_configured()
    events, patterns, skills = get_session_stats()

    if is_configured:
        if events > 0:
            print(f"{C.GREEN}{CHECK} ESASS{C.RESET} {C.DIM}[{events}ev/{patterns}pat/{skills}sk]{C.RESET}")
        else:
            print(f"{C.GREEN}{CHECK} ESASS{C.RESET} {C.DIM}[ready]{C.RESET}")
    else:
        print(f"{C.YELLOW}{SYNC} ESASS{C.RESET} {C.DIM}[not configured]{C.RESET}")


def send_windows_toast(title, message):
    """Send a Windows toast notification (if available)."""
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(title, message, duration=3, threaded=True)
        return True
    except ImportError:
        pass

    # Fallback: try PowerShell notification
    try:
        import subprocess
        ps_script = f'''
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        $template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
        $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
        $xml.SelectSingleNode("//text[@id='1']").InnerText = "{title}"
        $xml.SelectSingleNode("//text[@id='2']").InnerText = "{message}"
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("ESASS").Show($toast)
        '''
        subprocess.run(['powershell', '-Command', ps_script], capture_output=True, timeout=5)
        return True
    except:
        return False


def notify_sync_event(event_type="sync"):
    """Send a notification for a sync event."""
    is_configured, _ = check_esass_configured()
    events, patterns, skills = get_session_stats()

    if event_type == "startup":
        title = "ESASS Observer"
        if is_configured:
            message = f"Synchronized • {events} events, {patterns} patterns"
        else:
            message = "Not configured - run esass_cli.py setup"
    elif event_type == "sync":
        title = "ESASS Sync"
        message = f"Events: {events} | Patterns: {patterns} | Skills: {skills}"
    else:
        title = "ESASS"
        message = str(event_type)

    # Try Windows toast
    if not send_windows_toast(title, message):
        # Fallback to terminal flash
        flash_sync_notification()


# Main CLI interface
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='ESASS Notification System')
    parser.add_argument('command', nargs='?', default='startup',
                        choices=['startup', 'flash', 'inline', 'toast', 'check'],
                        help='Notification type')
    parser.add_argument('--message', '-m', help='Custom message for toast')

    args = parser.parse_args()

    if args.command == 'startup':
        display_startup_banner()
    elif args.command == 'flash':
        flash_sync_notification()
    elif args.command == 'inline':
        display_inline_status()
    elif args.command == 'toast':
        msg = args.message or "ESASS synchronized"
        notify_sync_event(msg)
    elif args.command == 'check':
        is_configured, msg = check_esass_configured()
        events, patterns, skills = get_session_stats()
        print(json.dumps({
            'configured': is_configured,
            'message': msg,
            'events': events,
            'patterns': patterns,
            'skills': skills
        }, indent=2))
