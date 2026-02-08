#!/usr/bin/env python3
"""
ESASS Unified Dashboard
=======================
Real-time observer combining event stream, gauges, and protection field visualization.

Features:
- Protection gradient field visualization
- Real-time event stream
- Tool usage gauges
- Pattern formation tracker
- Skill crystallization progress
- Field health metrics
"""

import json
import math
import os
import sys
import time
from collections import Counter, deque
from datetime import datetime, timedelta
from pathlib import Path

# Non-blocking keyboard input (Windows/Unix)
try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False
    import select

# Enable UTF-8 and ANSI on Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
except Exception:
    pass

# ============================================================================
# Configuration
# ============================================================================

ESASS_DATA_DIR = Path(os.environ.get("ESASS_DATA_DIR", Path.home() / ".esass" / "data"))
LOG_DIR = ESASS_DATA_DIR / "logs"
CLAUDE_CONFIG_DIR = Path.home() / ".claude"
REFRESH_RATE = 0.5

# Unicode detection
UNICODE_OK = sys.stdout.encoding and sys.stdout.encoding.lower() in ("utf-8", "utf8")

# ============================================================================
# Keyboard Input (ENHANCEMENT.md Phase 3.1)
# ============================================================================


def get_key_press():
    """
    Non-blocking keyboard input.

    Returns:
        str or None: The key pressed, or None if no key available
    """
    if HAS_MSVCRT:
        # Windows
        if msvcrt.kbhit():
            key = msvcrt.getch()
            try:
                return key.decode('utf-8').upper()
            except (UnicodeDecodeError, AttributeError):
                return None
        return None
    else:
        # Unix/Linux
        import tty
        import termios
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())
            rlist, _, _ = select.select([sys.stdin], [], [], 0)
            if rlist:
                return sys.stdin.read(1).upper()
            return None
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


# ============================================================================
# Sparklines (ENHANCEMENT.md Phase 3.2)
# ============================================================================


class Sparkline:
    """ASCII sparkline generator for trend visualization."""

    # Unicode sparkline blocks (8 levels)
    BLOCKS = "▁▂▃▄▅▆▇█" if UNICODE_OK else "_.-=+*#@"

    @classmethod
    def render(cls, values, width=15, color=None):
        """
        Render a sparkline from a list of values.

        Args:
            values: List of numeric values
            width: Target width (values will be bucketed)
            color: Optional ANSI color code

        Returns:
            str: Sparkline string
        """
        if not values:
            return " " * width

        # Bucket values if needed
        if len(values) > width:
            bucket_size = len(values) // width
            bucketed = []
            for i in range(width):
                start = i * bucket_size
                end = start + bucket_size
                bucket = values[start:end]
                bucketed.append(sum(bucket) / len(bucket) if bucket else 0)
            values = bucketed
        elif len(values) < width:
            # Pad with zeros on the left
            values = [0] * (width - len(values)) + list(values)

        # Normalize to 0-7 range
        min_val = min(values) if values else 0
        max_val = max(values) if values else 1
        range_val = max_val - min_val if max_val != min_val else 1

        result = ""
        for v in values:
            normalized = int(((v - min_val) / range_val) * 7)
            normalized = max(0, min(7, normalized))
            result += cls.BLOCKS[normalized]

        if color:
            return f"{color}{result}{C.RESET}"
        return result

    @classmethod
    def render_with_label(cls, values, label, width=15, color=None):
        """Render sparkline with a label."""
        sparkline = cls.render(values, width, color)
        if values:
            current = values[-1]
            return f"{label}: {sparkline} {current:.0f}"
        return f"{label}: {sparkline} --"


# Characters
class Sym:
    BLOCK_FULL = "█" if UNICODE_OK else "#"
    BLOCK_MED = "▓" if UNICODE_OK else "="
    BLOCK_LIGHT = "░" if UNICODE_OK else "-"
    BULLET = "●" if UNICODE_OK else "*"
    CIRCLE = "○" if UNICODE_OK else "o"
    ARROW = "→" if UNICODE_OK else "->"
    CHECK = "✓" if UNICODE_OK else "+"
    CROSS = "✗" if UNICODE_OK else "x"
    UP = "↑" if UNICODE_OK else "^"
    DOWN = "↓" if UNICODE_OK else "v"
    DOT = "·" if UNICODE_OK else "."


# Colors
class C:
    BLACK = "\033[30m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    # Cursor control - no flicker
    HOME = "\033[H"  # Move cursor to home (top-left)
    CLEAR_LINE = "\033[K"  # Clear from cursor to end of line
    CLEAR_SCREEN = "\033[2J"  # Full clear (only use once at start)
    HIDE_CURSOR = "\033[?25l"  # Hide cursor
    SHOW_CURSOR = "\033[?25h"  # Show cursor

    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

    # Enhanced alert effects (ENHANCEMENT.md Phase 3.3)
    BLINK = "\033[5m"  # Blinking text
    REVERSE = "\033[7m"  # Reverse video
    BG_BRIGHT_RED = "\033[101m"  # Bright red background


# ============================================================================
# Sync Status Check
# ============================================================================


def check_sync_status():
    """Check if ESASS is properly configured and synchronized."""
    hooks_file = CLAUDE_CONFIG_DIR / "hooks.json"

    if not hooks_file.exists():
        return False, "No hooks.json"

    try:
        with open(hooks_file, "r") as f:
            config = json.load(f)

        hooks = config.get("hooks", {})
        post_tool_use = hooks.get("PostToolUse", [])

        for hook in post_tool_use:
            cmd = hook.get("command", "")
            if "esass" in cmd.lower():
                return True, "Synchronized"

        return False, "Hook not found"
    except Exception as e:
        return False, f"Error: {e}"


# Tool display config
TOOL_ICONS = {
    "Read": "R",
    "Write": "W",
    "Edit": "E",
    "Bash": "$",
    "Grep": "G",
    "Glob": "F",
    "Task": "T",
    "WebFetch": "U",
    "WebSearch": "S",
    "AskUserQuestion": "?",
    "NotebookEdit": "N",
}

TOOL_COLORS = {
    "Read": C.CYAN,
    "Write": C.GREEN,
    "Edit": C.YELLOW,
    "Bash": C.MAGENTA,
    "Grep": C.BLUE,
    "Glob": C.BLUE,
    "Task": C.RED,
}

# ============================================================================
# State Management
# ============================================================================


class ESASSState:
    """Unified state for the ESASS dashboard."""

    def __init__(self):
        self.recent_events = deque(maxlen=50)
        self.tool_counts = Counter()
        self.category_counts = Counter()
        self.sequences = Counter()
        self.recent_tools = deque(maxlen=10)
        self.skill_candidates = []
        self.alerts = deque(maxlen=20)
        self.boundary_stats = Counter()  # counts actions per zone

        self.session_start = datetime.now()
        self.total_events = 0
        self.alert_count = 0
        self.last_event_time = None
        self.file_position = 0

        # Field metrics
        self.trust_radius = 0.1
        self.field_health = "initializing"

        # Time-series data for sparklines (ENHANCEMENT.md Phase 3.2)
        self.error_history = deque(maxlen=30)  # Errors per 30-second bucket
        self.success_history = deque(maxlen=30)  # Successes per 30-second bucket
        self.event_rate_history = deque(maxlen=30)  # Events per 30-second bucket
        self._last_bucket_time = datetime.now()
        self._current_bucket_errors = 0
        self._current_bucket_successes = 0
        self._current_bucket_events = 0

        # Display settings (ENHANCEMENT.md Phase 3.1)
        self.show_history = True
        self.flash_alerts = True
        self._flash_state = False  # For blinking effect

        # Load initial state
        self._load_sequence_state()
        self._load_events()

    def _load_sequence_state(self):
        """Load sequence tracking state."""
        seq_file = ESASS_DATA_DIR / "state" / "sequence_state.json"
        if seq_file.exists():
            try:
                with open(seq_file, "r") as f:
                    data = json.load(f)
                    self.sequences = Counter(data.get("sequences", {}))
            except Exception:
                pass

    def _load_events(self):
        """Load today's events."""
        log_file = self._get_log_file()
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            self._process_event(event, initial=True)
                        except Exception:
                            pass
                    self.file_position = f.tell()
            except Exception:
                pass

    def _get_log_file(self):
        return LOG_DIR / f"log_{datetime.now().strftime('%Y%m%d')}.jsonl"

    def _process_event(self, event, initial=False):
        """Process a single event."""
        self.recent_events.append(event)
        self.total_events += 1
        if not initial:
            self.last_event_time = datetime.now()

        data = event.get("event_data", event.get("data", {}))
        event_type = event.get("event_type")

        # Track alerts and errors
        if event_type == "reliability_alert":
            self.alerts.append(event)
            self.alert_count += 1
            self._current_bucket_errors += 1

        if event_type == "error" or data.get("success") is False:
            self._current_bucket_errors += 1
        elif data.get("success") is True:
            self._current_bucket_successes += 1

        self._current_bucket_events += 1

        # Track boundary actions
        if event_type == "boundary_action":
            zone = data.get("zone", "EXPLORATION")
            self.boundary_stats[zone] += 1

        tool = data.get("tool_name", "unknown")
        category = event.get("tags", [["unknown"]])[0] if "tags" in event else "unknown"
        # Override category for tool calls if context exists
        if "context" in data:
            category = data.get("context", {}).get("category", category)

        self.tool_counts[tool] += 1
        self.category_counts[category] += 1

        # Track sequences
        if tool != "unknown":
            self.recent_tools.append(tool)
            if len(self.recent_tools) >= 2:
                seq = f"{self.recent_tools[-2]} {Sym.ARROW} {self.recent_tools[-1]}"
                self.sequences[seq] += 1

    def _update_time_buckets(self):
        """Update time-series buckets for sparklines."""
        now = datetime.now()
        if (now - self._last_bucket_time).total_seconds() >= 30:
            # Save current bucket
            self.error_history.append(self._current_bucket_errors)
            self.success_history.append(self._current_bucket_successes)
            self.event_rate_history.append(self._current_bucket_events)

            # Reset for new bucket
            self._current_bucket_errors = 0
            self._current_bucket_successes = 0
            self._current_bucket_events = 0
            self._last_bucket_time = now

    def handle_key(self, key):
        """
        Handle keyboard input.

        Keys:
            H - Toggle historical alerts display
            S - Save snapshot to markdown
            C - Clear event buffer
        """
        if key == 'H':
            self.show_history = not self.show_history
            return f"History display {'ON' if self.show_history else 'OFF'}"
        elif key == 'S':
            filename = self._save_snapshot()
            return f"Snapshot saved to {filename}"
        elif key == 'C':
            self.recent_events.clear()
            return "Event buffer cleared"
        return None

    def _save_snapshot(self):
        """Save current dashboard state to markdown file."""
        filename = f"esass_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = ESASS_DATA_DIR / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# ESASS Dashboard Snapshot\\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\\n\\n")

            f.write(f"## Summary\\n")
            f.write(f"- **Total Events:** {self.total_events}\\n")
            f.write(f"- **Alert Count:** {self.alert_count}\\n")
            f.write(f"- **Field Health:** {self.field_health}\\n")
            f.write(f"- **Trust Radius:** {self.trust_radius:.0%}\\n\\n")

            f.write(f"## Tool Usage\\n")
            for tool, count in self.tool_counts.most_common(10):
                f.write(f"- {tool}: {count}\\n")
            f.write("\\n")

            f.write(f"## Patterns Detected\\n")
            for seq, count in self.sequences.most_common(10):
                f.write(f"- {seq}: {count}x\\n")
            f.write("\\n")

            f.write(f"## Recent Alerts\\n")
            for alert in list(self.alerts)[-10:]:
                data = alert.get("event_data", alert.get("data", {}))
                f.write(f"- {data.get('alert_type', 'unknown')}: {data.get('message', '')}\\n")

        return str(filepath)

    def update(self):
        """Check for new events and update state."""
        log_file = self._get_log_file()
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    f.seek(self.file_position)
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            self._process_event(event)
                        except Exception:
                            pass
                    self.file_position = f.tell()
            except Exception:
                pass

        # Reload sequence state periodically
        self._load_sequence_state()

        # Update skill candidates
        self._update_skills()

        # Update field metrics
        self._update_field_metrics()

        # Update time-series data for sparklines
        self._update_time_buckets()

        # Toggle flash state for blinking alerts
        self._flash_state = not self._flash_state

    def _update_skills(self):
        """Update skill candidates from sequences."""
        self.skill_candidates = []
        for seq, count in self.sequences.most_common(15):
            if count >= 3:
                confidence = min(1.0, count / 20)
                zone = (
                    "trusted"
                    if confidence >= 0.7
                    else ("learning" if confidence >= 0.3 else "exploration")
                )
                self.skill_candidates.append(
                    {
                        "sequence": seq,
                        "count": count,
                        "confidence": confidence,
                        "zone": zone,
                    }
                )

    def _update_field_metrics(self):
        """Update field health and trust radius."""
        if not self.skill_candidates:
            self.trust_radius = 0.1
            self.field_health = (
                "observing" if self.total_events > 10 else "initializing"
            )
        else:
            confs = [s["confidence"] for s in self.skill_candidates]
            avg_conf = sum(confs) / len(confs)
            self.trust_radius = min(1.0, avg_conf + 0.1)

            if self.trust_radius < 0.3:
                self.field_health = "learning"
            elif self.trust_radius < 0.6:
                self.field_health = "expanding"
            else:
                self.field_health = "stable"

    @property
    def zone_distribution(self):
        zones = {"exploration": 0, "learning": 0, "trusted": 0}
        for skill in self.skill_candidates:
            zones[skill["zone"]] += 1
        return zones

    @property
    def events_per_minute(self):
        elapsed = (datetime.now() - self.session_start).total_seconds() / 60
        return self.total_events / max(0.1, elapsed)


# ============================================================================
# Rendering Functions
# ============================================================================


def render_field(state: ESASSState, width=30, height=9):
    """Render the protection field visualization."""
    center_x = width // 2
    center_y = height // 2

    radius = state.trust_radius
    core_r = 1.5
    trusted_r = 2 + radius * 2
    learning_r = trusted_r + 1.5
    exploration_r = learning_r + 2

    lines = []
    for y in range(height):
        line = ""
        for x in range(width):
            dx = (x - center_x) / 2
            dy = y - center_y
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < core_r:
                line += f"{C.WHITE}{Sym.BLOCK_FULL}"
            elif dist < trusted_r:
                line += f"{C.GREEN}{Sym.BLOCK_MED}"
            elif dist < learning_r:
                line += f"{C.YELLOW}{Sym.BLOCK_LIGHT}"
            elif dist < exploration_r:
                line += f"{C.BLUE}{Sym.DOT}"
            else:
                line += " "
        lines.append(line + C.RESET)

    return lines


def render_gauge(value, max_val, width=15, color=C.GREEN):
    """Render a horizontal gauge bar."""
    if max_val == 0:
        pct = 0
    else:
        pct = min(1.0, value / max_val)
    filled = int(pct * width)
    return f"{color}{Sym.BLOCK_FULL * filled}{C.DIM}{Sym.BLOCK_LIGHT * (width - filled)}{C.RESET}"


def render_confidence(conf):
    """Render confidence as dots."""
    filled = int(conf * 5)
    return f"{C.GREEN}{Sym.BULLET * filled}{C.DIM}{Sym.CIRCLE * (5 - filled)}{C.RESET}"


def format_event_line(event, max_width=60):
    """Format event for display."""
    ts = event.get("timestamp", "")
    time_only = ts[11:19] if len(ts) > 11 else "??:??:??"

    data = event.get("event_data", event.get("data", {}))
    event_type = event.get("event_type")

    # Specialized ALERT formatting
    if event_type == "reliability_alert":
        msg = f"ALERT: {data.get('alert_type', 'failure')}"
        return (
            f"{C.DIM}{time_only}{C.RESET} {C.RED}[!]{C.RESET} "
            f"{C.BOLD}{C.BG_RED}{C.WHITE} {msg:30} {C.RESET}"
        )

    if event_type == "boundary_action":
        zone = data.get("zone", "EXPLORE")
        tool = data.get("tool", "?")
        risk = data.get("risk_level", "low")
        icon = TOOL_ICONS.get(tool, "B")
        color = {
            "CORE": C.WHITE,
            "TRUSTED": C.GREEN,
            "LEARNING": C.YELLOW,
            "EXPLORATION": C.BLUE,
        }.get(zone, C.WHITE)

        # Enhanced highlighting for CORE zone with write operations (Phase 3.3)
        if zone == "CORE" and tool in ["Write", "Edit", "Delete"] and risk == "high":
            # Critical boundary violation - flash effect
            return (
                f"{C.DIM}{time_only}{C.RESET} {C.BG_BRIGHT_RED}{C.WHITE}{C.BOLD}[!]{icon}]{C.RESET} "
                f"{C.REVERSE}{C.RED} CORE VIOLATION {C.RESET} {data.get('file_path', '')[:25]}"
            )

        return (
            f"{C.DIM}{time_only}{C.RESET} {color}[{icon}]{C.RESET} "
            f"{C.BOLD}{color}{zone:11}{C.RESET} {data.get('file_path', '')[:30]}"
        )

    # Standard tool call formatting
    tool = data.get("tool_name", "?")
    if tool == "?" and data.get("tool"):
        tool = data.get("tool")

    context = data.get("context", {})
    category = context.get("category", "call")[:10]
    target = str(context.get("target", ""))
    if not target and "file_path" in data:
        target = data.get("file_path")
    if not target and "error_message" in data:
        target = data.get("error_message")

    icon = TOOL_ICONS.get(tool, "?")
    color = {
        "tool_usage": TOOL_COLORS.get(tool, C.WHITE),
        "tool_call": TOOL_COLORS.get(tool, C.WHITE),
        "error": C.RED,
    }.get(event_type, C.WHITE)

    # Column alignment
    return (
        f"{C.DIM}{time_only}{C.RESET} {color}[{icon}]{tool:5}{C.RESET} "
        f"{C.DIM}{category:<10}{C.RESET} {target[: max_width - 35]}"
    )


# ============================================================================
# Main Dashboard
# ============================================================================


def print_line(text=""):
    """Print a line and clear to end (prevents artifacts)."""
    print(f"{text}{C.CLEAR_LINE}")


def render_dashboard(state: ESASSState, first_render=False, status_message=None):
    """Render the complete unified dashboard."""
    # First render clears screen, subsequent just move cursor home
    if first_render:
        print(C.CLEAR_SCREEN, end="")
    print(C.HOME + C.HIDE_CURSOR, end="")

    # Get terminal width (default 100)
    try:
        import shutil

        term_width = shutil.get_terminal_size().columns
    except Exception:
        term_width = 100

    # Check sync status
    is_synced, sync_msg = check_sync_status()
    if is_synced:
        sync_indicator = f"{C.GREEN}{Sym.CHECK} SYNCHRONIZED{C.RESET}"
    else:
        sync_indicator = f"{C.YELLOW}{Sym.CIRCLE} {sync_msg}{C.RESET}"

    # Header
    print_line(f"{C.BOLD}{C.CYAN}{'═' * term_width}")
    title = "ESASS UNIFIED DASHBOARD"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Calculate padding accounting for sync indicator
    sync_display = f"[{sync_indicator}{C.CYAN}]"
    padding = (
        term_width - len(title) - len(timestamp) - 30
    )  # rough estimate for ANSI codes
    print_line(f"  {title}  {sync_display}{' ' * max(1, padding)}{timestamp}")
    print_line(f"{'═' * term_width}{C.RESET}")

    # Status message line (for keyboard feedback)
    if status_message:
        print_line(f"  {C.BG_GREEN}{C.WHITE} {status_message} {C.RESET}")
    else:
        print_line()

    # Prepare field visualization
    field_lines = render_field(state)

    # Calculate layout
    field_width = 32
    event_width = min(50, term_width - field_width - 10)

    # Row 1: Field + Event Stream Header
    print_line(
        f"  {C.BOLD}Protection Field{C.RESET}"
        + " " * (field_width - 14)
        + f"{C.BOLD}Live Event Stream{C.RESET}"
    )
    print_line()

    # Get recent events
    recent = list(state.recent_events)[-len(field_lines) :]

    # Render field and events side by side
    for i, field_line in enumerate(field_lines):
        event_line = ""
        if i < len(recent):
            event_line = format_event_line(recent[-(i + 1)], event_width)
        print_line(f"  {field_line}  │  {event_line}")

    print_line()

    # Legend
    print_line(
        f"  {C.DIM}[{C.WHITE}{Sym.BLOCK_FULL}{C.DIM}Core {C.GREEN}{Sym.BLOCK_MED}{C.DIM}Trusted {C.YELLOW}{Sym.BLOCK_LIGHT}{C.DIM}Learning {C.BLUE}{Sym.DOT}{C.DIM}Explore]{C.RESET}"
    )
    print_line()

    # Divider
    print_line(f"  {C.DIM}{'─' * (term_width - 4)}{C.RESET}")
    print_line()

    # Row 2: Metrics Panel
    col_width = (term_width - 10) // 3

    # Column 1: Field Metrics
    uptime = str(datetime.now() - state.session_start).split(".")[0]
    health_colors = {
        "initializing": C.DIM,
        "observing": C.BLUE,
        "learning": C.YELLOW,
        "expanding": C.GREEN,
        "stable": C.CYAN,
    }
    health_color = health_colors.get(state.field_health, C.WHITE)

    col1 = [
        f"{C.BOLD}Field Status{C.RESET}",
        f"",
        f"Health:  {health_color}{state.field_health.upper()}{C.RESET}",
        f"Trust:   {render_gauge(state.trust_radius, 1.0, 10)} {state.trust_radius:.0%}",
        f"Uptime:  {uptime}",
        f"Events:  {state.total_events} ({state.events_per_minute:.1f}/min)",
    ]

    # Column 2: Tool Usage
    col2 = [f"{C.BOLD}Tool Usage{C.RESET}", ""]
    max_tool = max(state.tool_counts.values()) if state.tool_counts else 1
    for tool, count in state.tool_counts.most_common(4):
        icon = TOOL_ICONS.get(tool, "?")
        color = TOOL_COLORS.get(tool, C.WHITE)
        gauge = render_gauge(count, max_tool, 8, color)
        col2.append(f"{color}[{icon}]{C.RESET} {tool:6} {gauge} {count:2}")

    # Column 3: System Health with Sparklines (Phase 3.2)
    col3 = [f"{C.BOLD}System Health{C.RESET}", ""]
    if state.alert_count > 0:
        col3.append(f"Alerts:  {C.RED}{Sym.CROSS} {state.alert_count}{C.RESET}")
    else:
        col3.append(f"Alerts:  {C.GREEN}{Sym.CHECK} NONE{C.RESET}")

    # Sparklines for trends
    error_spark = Sparkline.render(list(state.error_history), width=10, color=C.RED)
    success_spark = Sparkline.render(list(state.success_history), width=10, color=C.GREEN)
    col3.append(f"Errors:  {error_spark}")
    col3.append(f"Success: {success_spark}")

    # Recent Alert with flash effect
    if state.alerts:
        last_event_data = state.alerts[-1].get(
            "event_data", state.alerts[-1].get("data", {})
        )
        last_alert = last_event_data.get("alert_type", "failure")
        # Flash effect for recent alerts
        if state._flash_state and state.flash_alerts:
            col3.append(f"Last:    {C.BG_RED}{C.WHITE}{last_alert[:15]}{C.RESET}")
        else:
            col3.append(f"Last:    {C.RED}{last_alert[:15]}{C.RESET}")
    else:
        col3.append(f"Last:    {C.DIM}none{C.RESET}")

    # Print columns side by side
    max_rows = max(len(col1), len(col2), len(col3))
    for i in range(max_rows):
        c1 = col1[i] if i < len(col1) else ""
        c2 = col2[i] if i < len(col2) else ""
        c3 = col3[i] if i < len(col3) else ""

        # Pad columns (rough approximation - ANSI codes mess with length)
        # Using fixed widths for cleaner layout
        p1 = c1 + " " * max(
            0,
            35 - len(str(c1).replace("\033", ""))
            if "\033" in str(c1)
            else 35 - len(str(c1)),
        )
        p2 = c2 + " " * max(
            0,
            30 - len(str(c2).replace("\033", ""))
            if "\033" in str(c2)
            else 30 - len(str(c2)),
        )
        print_line(f"  {p1} {p2} {c3}")

    print_line()
    print_line(f"  {C.DIM}{'─' * (term_width - 4)}{C.RESET}")
    print_line()

    # Row 3: Pattern Formation
    print_line(f"  {C.BOLD}Pattern Formation & Skill Crystallization{C.RESET}")
    print_line()

    if state.skill_candidates:
        # Show skills in columns
        skills_per_row = 2
        for i in range(0, min(6, len(state.skill_candidates)), skills_per_row):
            row = ""
            for j in range(skills_per_row):
                if i + j < len(state.skill_candidates):
                    skill = state.skill_candidates[i + j]
                    conf = skill["confidence"]
                    zone = skill["zone"]
                    zone_colors = {
                        "trusted": C.GREEN,
                        "learning": C.YELLOW,
                        "exploration": C.BLUE,
                    }
                    zc = zone_colors[zone]

                    seq = skill["sequence"][:25]
                    conf_dots = render_confidence(conf)

                    row += f"  {zc}{Sym.BULLET}{C.RESET} {conf_dots} {seq:25} ({skill['count']:2}x)    "
            print_line(row)
    else:
        print_line(
            f"  {C.DIM}Observing patterns... skills will crystallize as confidence grows{C.RESET}"
        )

    print_line()
    print_line(f"  {C.DIM}{'─' * (term_width - 4)}{C.RESET}")
    print_line()

    # Row 4: Raw Event Stream (last 15 events)
    print_line(
        f"  {C.BOLD}Raw Event Stream{C.RESET} {C.DIM}(latest {min(15, len(state.recent_events))} of {state.total_events} events){C.RESET}"
    )
    print_line()

    # Get terminal height to determine how many events to show
    try:
        import shutil

        term_height = shutil.get_terminal_size().lines
        # Calculate available lines (rough estimate: header ~4, field ~12, metrics ~8, skills ~6, footer ~2)
        available_lines = max(5, min(15, term_height - 35))
    except Exception:
        available_lines = 10

    events_to_show = list(state.recent_events)[-available_lines:]

    if events_to_show:
        # Header row
        print_line(
            f"  {C.DIM}{'TIME':<10} {'TOOL':<8} {'CATEGORY':<15} {'TARGET':<40}{C.RESET}"
        )
        print_line(f"  {C.DIM}{'─' * 10} {'─' * 8} {'─' * 15} {'─' * 40}{C.RESET}")

        for event in reversed(events_to_show):
            print_line(f"  {format_event_line(event, term_width - 15)}")
    else:
        print_line(f"  {C.DIM}No events captured yet...{C.RESET}")

    print_line()

    # Footer with keyboard shortcuts (Phase 3.1)
    last_event_ago = ""
    if state.last_event_time:
        ago = (datetime.now() - state.last_event_time).total_seconds()
        last_event_ago = f" │ Last: {ago:.0f}s ago"

    shortcuts = f"[H]istory:[{'ON' if state.show_history else 'OFF'}] [S]napshot [C]lear"
    print_line(
        f"  {C.DIM}{shortcuts}{last_event_ago} │ {len(events_to_show)}/{len(state.recent_events)} events │ Ctrl+C to exit{C.RESET}"
    )

    # Show cursor at end
    print(C.SHOW_CURSOR, end="", flush=True)


# ============================================================================
# Main Loop
# ============================================================================


def main():
    """Main dashboard loop with keyboard handling."""
    state = ESASSState()
    status_message = None
    status_message_time = None

    print(f"{C.CYAN}Starting ESASS Unified Dashboard...{C.RESET}")
    time.sleep(0.5)

    first_render = True
    try:
        while True:
            # Handle keyboard input (Phase 3.1)
            key = get_key_press()
            if key:
                result = state.handle_key(key)
                if result:
                    status_message = result
                    status_message_time = datetime.now()

            # Clear status message after 3 seconds
            if status_message_time and (datetime.now() - status_message_time).total_seconds() > 3:
                status_message = None
                status_message_time = None

            state.update()
            render_dashboard(state, first_render=first_render, status_message=status_message)
            first_render = False
            time.sleep(REFRESH_RATE)

    except KeyboardInterrupt:
        print(C.SHOW_CURSOR + C.CLEAR_SCREEN, end="")
        print(f"\n{C.GREEN}{Sym.CHECK} Dashboard stopped{C.RESET}")
        print(f"  Total events: {state.total_events}")
        print(f"  Patterns tracked: {len(state.sequences)}")
        print(f"  Skills forming: {len(state.skill_candidates)}")
        print()


if __name__ == "__main__":
    main()
