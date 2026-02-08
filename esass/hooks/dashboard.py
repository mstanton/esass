#!/usr/bin/env python3
"""
ESASS Real-Time Dashboard
=========================
Live gauges and pattern visualization for Claude Code sessions.

Shows:
- Real-time event stream
- Tool usage gauges
- Pattern formation indicators
- Skill candidate tracker
- Session health metrics
"""

import json
import os
import sys
import time
from collections import Counter, deque
from datetime import datetime, timedelta
from pathlib import Path

# Enable UTF-8 and ANSI on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
except:
    pass

# ============================================================================
# Configuration
# ============================================================================

ESASS_DATA_DIR = Path(os.environ.get('ESASS_DATA_DIR', Path.home() / '.esass' / 'data'))
LOG_DIR = ESASS_DATA_DIR / 'logs'
REFRESH_INTERVAL = 0.5  # seconds

# Unicode support check
UNICODE_OK = sys.stdout.encoding and sys.stdout.encoding.lower() in ('utf-8', 'utf8')

# Characters
BAR_FULL = '█' if UNICODE_OK else '#'
BAR_EMPTY = '░' if UNICODE_OK else '-'
ARROW_UP = '↑' if UNICODE_OK else '^'
ARROW_DOWN = '↓' if UNICODE_OK else 'v'
ARROW_RIGHT = '→' if UNICODE_OK else '->'
BULLET = '●' if UNICODE_OK else '*'
CIRCLE = '○' if UNICODE_OK else 'o'
CHECK = '✓' if UNICODE_OK else '[OK]'
CROSS = '✗' if UNICODE_OK else '[X]'

# Colors
class C:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'
    CLEAR_LINE = '\033[K'
    CLEAR_SCREEN = '\033[2J'
    HOME = '\033[H'

# Tool config
TOOL_ICONS = {
    'Read': '[R]', 'Write': '[W]', 'Edit': '[E]', 'Bash': '[$]',
    'Grep': '[G]', 'Glob': '[F]', 'Task': '[T]', 'WebFetch': '[U]',
    'WebSearch': '[S]', 'AskUserQuestion': '[?]',
}

TOOL_COLORS = {
    'Read': C.CYAN, 'Write': C.GREEN, 'Edit': C.YELLOW, 'Bash': C.MAGENTA,
    'Grep': C.BLUE, 'Glob': C.BLUE, 'Task': C.RED,
}

# ============================================================================
# Dashboard State
# ============================================================================

class DashboardState:
    def __init__(self, max_events=10):
        self.recent_events = deque(maxlen=max_events)
        self.tool_counts = Counter()
        self.category_counts = Counter()
        self.sequences = Counter()
        self.recent_tools = deque(maxlen=10)
        self.session_start = datetime.now()
        self.total_events = 0
        self.events_per_minute = 0
        self.last_event_time = None
        self.pattern_confidence = {}

    def add_event(self, event):
        self.recent_events.append(event)
        self.total_events += 1
        self.last_event_time = datetime.now()

        data = event.get('data', {})
        tool = data.get('tool_name', 'unknown')
        category = data.get('context', {}).get('category', 'unknown')

        self.tool_counts[tool] += 1
        self.category_counts[category] += 1

        # Track sequences
        self.recent_tools.append(tool)
        if len(self.recent_tools) >= 2:
            seq2 = f"{self.recent_tools[-2]} {ARROW_RIGHT} {self.recent_tools[-1]}"
            self.sequences[seq2] += 1
        if len(self.recent_tools) >= 3:
            seq3 = f"{self.recent_tools[-3]} {ARROW_RIGHT} {self.recent_tools[-2]} {ARROW_RIGHT} {self.recent_tools[-1]}"
            self.sequences[seq3] += 1

        # Update pattern confidence
        for seq, count in self.sequences.items():
            if count >= 3:
                self.pattern_confidence[seq] = min(1.0, count / 10)

# ============================================================================
# Rendering
# ============================================================================

def render_gauge(value, max_value, width=20, label=""):
    """Render a horizontal gauge bar."""
    if max_value == 0:
        pct = 0
    else:
        pct = min(1.0, value / max_value)

    filled = int(pct * width)
    empty = width - filled

    # Color based on percentage
    if pct >= 0.8:
        color = C.RED
    elif pct >= 0.5:
        color = C.YELLOW
    else:
        color = C.GREEN

    bar = f"{color}{BAR_FULL * filled}{C.DIM}{BAR_EMPTY * empty}{C.RESET}"
    return f"{label:12} [{bar}] {value:3}/{max_value}"


def render_mini_gauge(value, max_value, width=10):
    """Render a small inline gauge."""
    if max_value == 0:
        pct = 0
    else:
        pct = min(1.0, value / max_value)
    filled = int(pct * width)
    return BAR_FULL * filled + BAR_EMPTY * (width - filled)


def render_confidence_indicator(confidence):
    """Render confidence as filled circles."""
    filled = int(confidence * 5)
    return BULLET * filled + CIRCLE * (5 - filled)


def format_event_compact(event):
    """Format event for dashboard display."""
    ts = event.get('timestamp', '')
    time_only = ts[11:19] if len(ts) > 11 else ts[:8]

    data = event.get('data', {})
    tool = data.get('tool_name', '?')
    target = data.get('context', {}).get('target', '')

    icon = TOOL_ICONS.get(tool, '[?]')
    color = TOOL_COLORS.get(tool, C.WHITE)

    if len(str(target)) > 35:
        target = str(target)[:32] + '...'

    return f"{C.DIM}{time_only}{C.RESET} {color}{icon}{C.RESET} {tool:8} {target}"


def clear_screen():
    """Clear terminal and move cursor home."""
    print(C.CLEAR_SCREEN + C.HOME, end='')


def render_dashboard(state: DashboardState):
    """Render the full dashboard."""
    clear_screen()

    # Header
    print(f"{C.BOLD}{C.CYAN}{'═' * 70}")
    print(f"  ESASS REAL-TIME DASHBOARD                    {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'═' * 70}{C.RESET}")
    print()

    # Session metrics
    uptime = datetime.now() - state.session_start
    uptime_str = str(uptime).split('.')[0]
    events_rate = state.total_events / max(1, uptime.total_seconds() / 60)

    print(f"  {C.BOLD}Session Metrics{C.RESET}")
    print(f"  ├─ Uptime:      {uptime_str}")
    print(f"  ├─ Total Events:{state.total_events:5}")
    print(f"  ├─ Rate:        {events_rate:.1f} events/min")
    if state.last_event_time:
        ago = (datetime.now() - state.last_event_time).total_seconds()
        print(f"  └─ Last Event:  {ago:.1f}s ago")
    else:
        print(f"  └─ Last Event:  waiting...")
    print()

    # Tool Usage Gauges
    print(f"  {C.BOLD}Tool Usage Gauges{C.RESET}")
    max_count = max(state.tool_counts.values()) if state.tool_counts else 1
    for tool, count in state.tool_counts.most_common(6):
        icon = TOOL_ICONS.get(tool, '[?]')
        color = TOOL_COLORS.get(tool, C.WHITE)
        gauge = render_mini_gauge(count, max_count, 15)
        print(f"  {color}{icon}{C.RESET} {tool:10} {C.GREEN}{gauge}{C.RESET} {count:3}")
    if not state.tool_counts:
        print(f"  {C.DIM}No tool usage yet...{C.RESET}")
    print()

    # Pattern Formation
    print(f"  {C.BOLD}Pattern Formation{C.RESET}")
    if state.pattern_confidence:
        for seq, conf in sorted(state.pattern_confidence.items(), key=lambda x: -x[1])[:5]:
            indicator = render_confidence_indicator(conf)
            count = state.sequences[seq]
            status = f"{C.GREEN}{CHECK}{C.RESET}" if conf >= 0.5 else f"{C.YELLOW}{CIRCLE}{C.RESET}"
            print(f"  {status} {indicator} {seq} ({count}x)")
    else:
        print(f"  {C.DIM}Building patterns... (need 3+ occurrences){C.RESET}")
    print()

    # Emerging Sequences
    print(f"  {C.BOLD}Emerging Sequences{C.RESET}")
    emerging = [(s, c) for s, c in state.sequences.items() if c < 3 and ARROW_RIGHT in s]
    if emerging:
        for seq, count in sorted(emerging, key=lambda x: -x[1])[:4]:
            progress = render_mini_gauge(count, 3, 5)
            print(f"  {C.DIM}{progress}{C.RESET} {seq} ({count}/3)")
    else:
        print(f"  {C.DIM}Waiting for tool sequences...{C.RESET}")
    print()

    # Recent Events Stream
    print(f"  {C.BOLD}Recent Events{C.RESET}")
    print(f"  {C.DIM}{'─' * 60}{C.RESET}")
    if state.recent_events:
        for event in list(state.recent_events)[-8:]:
            print(f"  {format_event_compact(event)}")
    else:
        print(f"  {C.DIM}Waiting for events...{C.RESET}")
    print(f"  {C.DIM}{'─' * 60}{C.RESET}")
    print()

    # Footer
    print(f"  {C.DIM}Press Ctrl+C to exit | Log: {LOG_DIR}{C.RESET}")


# ============================================================================
# Main Loop
# ============================================================================

def get_today_log():
    return LOG_DIR / f"log_{datetime.now().strftime('%Y%m%d')}.jsonl"


def run_dashboard():
    """Main dashboard loop."""
    state = DashboardState()
    log_file = get_today_log()
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Get initial position
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8') as f:
            # Load existing events
            for line in f:
                try:
                    event = json.loads(line.strip())
                    state.add_event(event)
                except:
                    pass
            position = f.tell()
    else:
        position = 0
        log_file.touch()

    try:
        while True:
            # Check for new events
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    f.seek(position)
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            state.add_event(event)
                        except:
                            pass
                    position = f.tell()

            # Render dashboard
            render_dashboard(state)

            time.sleep(REFRESH_INTERVAL)

    except KeyboardInterrupt:
        clear_screen()
        print(f"\n{C.GREEN}Dashboard stopped.{C.RESET}")
        print(f"Total events captured: {state.total_events}")
        print(f"Patterns detected: {len(state.pattern_confidence)}")


if __name__ == '__main__':
    run_dashboard()
