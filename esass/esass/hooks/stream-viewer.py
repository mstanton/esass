#!/usr/bin/env python3
"""
ESASS Raw Event Stream Viewer
=============================
A lightweight viewer for Claude Code agent event streams.

Usage:
    python stream-viewer.py              # Live stream (default)
    python stream-viewer.py --raw        # Raw JSON output
    python stream-viewer.py --tail 50    # Last 50 events
    python stream-viewer.py --compact    # Compact single-line format
    python stream-viewer.py --filter Read # Filter by tool name
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ============================================================================
# Configuration
# ============================================================================

ESASS_DATA_DIR = Path(os.environ.get('ESASS_DATA_DIR', Path.home() / '.esass' / 'data'))
LOG_DIR = ESASS_DATA_DIR / 'logs'

# Try to enable ANSI colors and UTF-8 on Windows
try:
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
except:
    pass

# Enable UTF-8 output
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# Check Unicode support
UNICODE_OK = sys.stdout.encoding and sys.stdout.encoding.lower() in ('utf-8', 'utf8')
BAR_CHAR = '█' if UNICODE_OK else '#'

# Colors
class C:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[0;37m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

# Disable colors if not TTY or --no-color
if not sys.stdout.isatty() or '--no-color' in sys.argv:
    for attr in dir(C):
        if not attr.startswith('_'):
            setattr(C, attr, '')

# Tool display config
TOOL_ICONS = {
    'Read': '[R]', 'Write': '[W]', 'Edit': '[E]', 'Bash': '[$]',
    'Grep': '[G]', 'Glob': '[F]', 'Task': '[T]', 'WebFetch': '[U]',
    'WebSearch': '[S]', 'AskUserQuestion': '[?]', 'NotebookEdit': '[N]',
}

TOOL_COLORS = {
    'Read': C.CYAN, 'Write': C.GREEN, 'Edit': C.YELLOW, 'Bash': C.MAGENTA,
    'Grep': C.BLUE, 'Glob': C.BLUE, 'Task': C.RED, 'WebFetch': C.WHITE,
    'WebSearch': C.WHITE,
}

# ============================================================================
# Core Functions
# ============================================================================

def get_today_log() -> Path:
    """Get today's log file path."""
    today = datetime.now().strftime('%Y%m%d')
    return LOG_DIR / f'log_{today}.jsonl'


def format_event(event: dict, mode: str = 'compact') -> str:
    """Format a single event for display."""
    if mode == 'raw':
        return json.dumps(event)

    # Extract fields
    ts = event.get('timestamp', '')[:19]
    data = event.get('data', {})
    tool_name = data.get('tool_name', 'unknown')
    context = data.get('context', {})
    category = context.get('category', '')
    target = context.get('target', '')
    action = context.get('action', '')
    tags = context.get('tags', [])
    result = data.get('result_preview', '')

    # Get display elements
    icon = TOOL_ICONS.get(tool_name, '[?]')
    color = TOOL_COLORS.get(tool_name, C.WHITE)

    # Truncate long values
    if len(str(target)) > 60:
        target = str(target)[:57] + '...'
    if len(str(result)) > 80:
        result = str(result)[:77] + '...'

    if mode == 'compact':
        time_only = ts[11:19] if len(ts) > 11 else ts
        return f"{C.DIM}{time_only}{C.RESET} {color}{icon}{C.RESET} {C.BOLD}{tool_name:12}{C.RESET} {target}"

    elif mode == 'full':
        lines = [
            f"{C.DIM}[{ts}]{C.RESET}",
            f"  {color}{icon}{C.RESET} {C.BOLD}{tool_name}{C.RESET}",
        ]
        if category:
            lines.append(f"  {C.DIM}Category:{C.RESET} {category}")
        if target:
            lines.append(f"  {C.DIM}Target:{C.RESET}   {target}")
        if action:
            lines.append(f"  {C.DIM}Action:{C.RESET}   {action}")
        if tags:
            lines.append(f"  {C.DIM}Tags:{C.RESET}     {', '.join(tags)}")
        if result:
            lines.append(f"  {C.DIM}Result:{C.RESET}   {result}")
        lines.append('')
        return '\n'.join(lines)

    elif mode == 'json-pretty':
        return json.dumps(event, indent=2)

    return json.dumps(event)


def matches_filter(event: dict, tool_filter: str = None, category_filter: str = None) -> bool:
    """Check if event matches filters."""
    if tool_filter:
        tool_name = event.get('data', {}).get('tool_name', '')
        if tool_filter.lower() not in tool_name.lower():
            return False
    if category_filter:
        category = event.get('data', {}).get('context', {}).get('category', '')
        if category_filter.lower() not in category.lower():
            return False
    return True


# ============================================================================
# Commands
# ============================================================================

def cmd_stream(args):
    """Live stream events as they arrive."""
    log_file = get_today_log()
    log_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"{C.BOLD}{C.CYAN}")
    print("=" * 60)
    print("           ESASS Raw Event Stream Viewer")
    print("=" * 60)
    print(f"{C.RESET}")
    print(f"  Log:    {C.CYAN}{log_file}{C.RESET}")
    print(f"  Mode:   {C.YELLOW}{args.mode}{C.RESET}")
    if args.filter:
        print(f"  Filter: {C.GREEN}{args.filter}{C.RESET}")
    print(f"  Press {C.BOLD}Ctrl+C{C.RESET} to stop")
    print()
    print(f"{C.DIM}{'─' * 60}{C.RESET}")

    # Get initial file position
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8') as f:
            f.seek(0, 2)
            position = f.tell()
    else:
        position = 0
        log_file.touch()

    event_count = 0

    try:
        while True:
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    f.seek(position)
                    new_lines = f.readlines()
                    position = f.tell()

                for line in new_lines:
                    try:
                        event = json.loads(line.strip())
                        if matches_filter(event, args.filter, args.category):
                            print(format_event(event, args.mode))
                            event_count += 1
                    except json.JSONDecodeError:
                        pass

            time.sleep(0.2)

    except KeyboardInterrupt:
        print()
        print(f"{C.DIM}{'─' * 60}{C.RESET}")
        print(f"  {C.GREEN}Captured {event_count} events{C.RESET}")


def cmd_tail(args):
    """Show last N events."""
    log_file = get_today_log()

    print(f"{C.BOLD}{C.CYAN}")
    print("=" * 60)
    print(f"              Last {args.count} Events")
    print("=" * 60)
    print(f"{C.RESET}")

    if not log_file.exists():
        print(f"{C.YELLOW}No events found for today.{C.RESET}")
        return

    events = []
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                if matches_filter(event, args.filter, args.category):
                    events.append(event)
            except json.JSONDecodeError:
                pass

    if not events:
        print(f"{C.YELLOW}No matching events found.{C.RESET}")
        return

    for event in events[-args.count:]:
        print(format_event(event, args.mode))


def cmd_dump(args):
    """Dump all raw events."""
    log_file = get_today_log()

    if not log_file.exists():
        print("No events for today", file=sys.stderr)
        sys.exit(1)

    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                if matches_filter(event, args.filter, args.category):
                    print(json.dumps(event))
            except json.JSONDecodeError:
                pass


def cmd_stats(args):
    """Show event statistics."""
    log_file = get_today_log()

    print(f"{C.BOLD}{C.CYAN}")
    print("=" * 60)
    print("              Event Statistics")
    print("=" * 60)
    print(f"{C.RESET}")

    if not log_file.exists():
        print(f"{C.YELLOW}No events found for today.{C.RESET}")
        return

    tools = {}
    categories = {}
    total = 0

    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                total += 1

                tool = event.get('data', {}).get('tool_name', 'unknown')
                tools[tool] = tools.get(tool, 0) + 1

                cat = event.get('data', {}).get('context', {}).get('category', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1
            except json.JSONDecodeError:
                pass

    print(f"  {C.BOLD}Total Events:{C.RESET} {total}")
    print()

    print(f"  {C.BOLD}Tools:{C.RESET}")
    for tool, count in sorted(tools.items(), key=lambda x: -x[1]):
        icon = TOOL_ICONS.get(tool, '[?]')
        color = TOOL_COLORS.get(tool, C.WHITE)
        bar = BAR_CHAR * min(count, 30)
        print(f"    {color}{icon}{C.RESET} {tool:15} {count:3} {C.GREEN}{bar}{C.RESET}")

    print()
    print(f"  {C.BOLD}Categories:{C.RESET}")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        bar = BAR_CHAR * min(count, 30)
        print(f"    {cat:20} {count:3} {C.BLUE}{bar}{C.RESET}")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ESASS Raw Event Stream Viewer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      Live stream with compact format
  %(prog)s --raw                Live stream raw JSON
  %(prog)s --full               Live stream with full details
  %(prog)s tail 50              Last 50 events
  %(prog)s tail 20 --full       Last 20 with full details
  %(prog)s --filter Bash        Only Bash tool events
  %(prog)s dump | jq .          Pipe to jq for processing
  %(prog)s stats                Show statistics
        """
    )

    # Commands
    subparsers = parser.add_subparsers(dest='command')

    # Global options (before subcommand)
    parser.add_argument('--raw', '-r', action='store_const', const='raw', dest='mode',
                        help='Output raw JSON')
    parser.add_argument('--compact', '-c', action='store_const', const='compact', dest='mode',
                        help='Compact single-line format (default)')
    parser.add_argument('--full', '-v', action='store_const', const='full', dest='mode',
                        help='Full multi-line format with all details')
    parser.add_argument('--json', '-j', action='store_const', const='json-pretty', dest='mode',
                        help='Pretty-printed JSON')
    parser.add_argument('--filter', '-f', type=str, metavar='TOOL',
                        help='Filter by tool name')
    parser.add_argument('--category', type=str, metavar='CAT',
                        help='Filter by category')
    parser.add_argument('--no-color', action='store_true',
                        help='Disable colored output')
    parser.set_defaults(mode='compact')

    # Subcommands with shared options
    tail_parser = subparsers.add_parser('tail', help='Show last N events')
    tail_parser.add_argument('count', type=int, nargs='?', default=20,
                             help='Number of events (default: 20)')
    tail_parser.add_argument('--raw', '-r', action='store_const', const='raw', dest='mode')
    tail_parser.add_argument('--compact', '-c', action='store_const', const='compact', dest='mode')
    tail_parser.add_argument('--full', '-v', action='store_const', const='full', dest='mode')
    tail_parser.add_argument('--filter', '-f', type=str, metavar='TOOL')
    tail_parser.add_argument('--category', type=str, metavar='CAT')
    tail_parser.set_defaults(mode='compact')

    dump_parser = subparsers.add_parser('dump', help='Dump all raw events')
    dump_parser.add_argument('--filter', '-f', type=str, metavar='TOOL')
    dump_parser.add_argument('--category', type=str, metavar='CAT')

    stats_parser = subparsers.add_parser('stats', help='Show statistics')

    args = parser.parse_args()

    # Default to stream if no command
    if args.command is None:
        cmd_stream(args)
    elif args.command == 'tail':
        cmd_tail(args)
    elif args.command == 'dump':
        cmd_dump(args)
    elif args.command == 'stats':
        cmd_stats(args)


if __name__ == '__main__':
    main()
