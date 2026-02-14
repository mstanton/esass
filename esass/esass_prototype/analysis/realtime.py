"""
Realtime analysis and display module for ESASS.
"""

import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Check if terminal supports Unicode
try:
    if sys.stdout.encoding:
        UNICODE_SUPPORT = sys.stdout.encoding.lower() in ("utf-8", "utf8")
    else:
        UNICODE_SUPPORT = True  # Assumption for modern terminals
except:
    UNICODE_SUPPORT = False


# Display colors (ANSI)
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


# Symbols (with ASCII fallbacks)
class Sym:
    CHECK = "✓" if UNICODE_SUPPORT else "[OK]"
    CROSS = "✗" if UNICODE_SUPPORT else "[X]"
    BULLET = "●" if UNICODE_SUPPORT else "*"
    CIRCLE = "○" if UNICODE_SUPPORT else "o"
    BAR_FULL = "█" if UNICODE_SUPPORT else "#"
    BAR_EMPTY = "░" if UNICODE_SUPPORT else "-"
    HLINE = "─" if UNICODE_SUPPORT else "-"


# Tool icons
if UNICODE_SUPPORT:
    TOOL_ICONS = {
        "Read": "📖",
        "Write": "✏️",
        "Edit": "🔧",
        "Bash": "💻",
        "Grep": "🔍",
        "Glob": "📂",
        "Task": "🤖",
        "WebFetch": "🌐",
        "WebSearch": "🔎",
        "AskUserQuestion": "❓",
    }
else:
    TOOL_ICONS = {
        "Read": "[R]",
        "Write": "[W]",
        "Edit": "[E]",
        "Bash": "[$]",
        "Grep": "[G]",
        "Glob": "[F]",
        "Task": "[T]",
        "WebFetch": "[U]",
        "WebSearch": "[S]",
        "AskUserQuestion": "[?]",
    }

# Pattern detection thresholds
MIN_PATTERN_OCCURRENCES = 3
MIN_SEQUENCE_OCCURRENCES = 5
PATTERN_CONFIDENCE_THRESHOLD = 0.6


class PatternAnalyzer:
    """Analyzes tool usage patterns from logged events."""

    def __init__(self, events: List[dict]):
        self.events = events
        self.tool_events = [e for e in events if e.get("event_type") == "tool_call"]

    def get_tool_frequency(self) -> Counter:
        """Count tool usage frequency."""
        return Counter(
            e.get("data", {}).get("tool_name", "unknown") for e in self.tool_events
        )

    def get_category_frequency(self) -> Counter:
        """Count category frequency."""
        return Counter(
            e.get("data", {}).get("context", {}).get("category", "unknown")
            for e in self.tool_events
        )

    def get_tag_frequency(self) -> Counter:
        """Count tag frequency."""
        tags = Counter()
        for e in self.tool_events:
            for tag in e.get("data", {}).get("context", {}).get("tags", []):
                tags[tag] += 1
        return tags

    def get_file_type_frequency(self) -> Counter:
        """Count file type frequency."""
        file_types = Counter()
        for e in self.tool_events:
            target = e.get("data", {}).get("context", {}).get("target", "")
            if target and isinstance(target, str):
                ext = Path(target).suffix.lower()
                if ext:
                    file_types[ext] += 1
        return file_types

    def detect_sequences(
        self, min_length: int = 2, max_length: int = 4
    ) -> Dict[str, int]:
        """Detect common tool sequences."""
        sequences = defaultdict(int)

        tools = [
            e.get("data", {}).get("tool_name", "unknown") for e in self.tool_events
        ]

        for length in range(min_length, max_length + 1):
            for i in range(len(tools) - length + 1):
                seq = tuple(tools[i : i + length])
                sequences[" -> ".join(seq)] += 1

        # Filter by minimum occurrences
        return {
            seq: count
            for seq, count in sequences.items()
            if count >= MIN_SEQUENCE_OCCURRENCES
        }

    def detect_workflow_patterns(self) -> List[dict]:
        """Detect higher-level workflow patterns."""
        patterns = []

        # Pattern: Read-then-Edit (file modification workflow)
        read_edit_count = 0
        for i, e in enumerate(self.tool_events[:-1]):
            if e.get("data", {}).get("tool_name") == "Read":
                next_e = self.tool_events[i + 1]
                if next_e.get("data", {}).get("tool_name") == "Edit":
                    # Check if same file
                    file1 = e.get("data", {}).get("context", {}).get("target", "")
                    file2 = next_e.get("data", {}).get("context", {}).get("target", "")
                    if file1 and file1 == file2:
                        read_edit_count += 1

        if read_edit_count >= MIN_PATTERN_OCCURRENCES:
            patterns.append(
                {
                    "name": "Read-Before-Edit",
                    "description": "Always reads file before editing (safe modification pattern)",
                    "occurrences": read_edit_count,
                    "type": "safety_pattern",
                    "confidence": min(1.0, read_edit_count / 10),
                }
            )

        # Pattern: Search-Read-Edit (exploration-modification workflow)
        search_read_edit = 0
        for i in range(len(self.tool_events) - 2):
            tools = [
                self.tool_events[i + j].get("data", {}).get("tool_name")
                for j in range(3)
            ]
            if (
                tools[0] in ["Grep", "Glob"]
                and tools[1] == "Read"
                and tools[2] == "Edit"
            ):
                search_read_edit += 1

        if search_read_edit >= MIN_PATTERN_OCCURRENCES:
            patterns.append(
                {
                    "name": "Search-Read-Edit",
                    "description": "Searches codebase, reads results, then edits",
                    "occurrences": search_read_edit,
                    "type": "exploration_pattern",
                    "confidence": min(1.0, search_read_edit / 10),
                }
            )

        # Pattern: Test-after-Edit (TDD-ish pattern)
        edit_test_count = 0
        for i, e in enumerate(self.tool_events[:-1]):
            if e.get("data", {}).get("tool_name") == "Edit":
                next_e = self.tool_events[i + 1]
                if next_e.get("data", {}).get("tool_name") == "Bash":
                    cmd = (
                        next_e.get("data", {}).get("parameters", {}).get("command", "")
                    )
                    if "pytest" in cmd or "test" in cmd.lower():
                        edit_test_count += 1

        if edit_test_count >= MIN_PATTERN_OCCURRENCES:
            patterns.append(
                {
                    "name": "Edit-Then-Test",
                    "description": "Runs tests after editing code",
                    "occurrences": edit_test_count,
                    "type": "quality_pattern",
                    "confidence": min(1.0, edit_test_count / 10),
                }
            )

        # Pattern: Git workflow
        git_workflow = 0
        for e in self.tool_events:
            if e.get("data", {}).get("tool_name") == "Bash":
                cmd = e.get("data", {}).get("parameters", {}).get("command", "")
                if cmd.startswith("git "):
                    git_workflow += 1

        if git_workflow >= MIN_PATTERN_OCCURRENCES:
            patterns.append(
                {
                    "name": "Git-Integrated",
                    "description": "Regular use of git commands for version control",
                    "occurrences": git_workflow,
                    "type": "workflow_pattern",
                    "confidence": min(1.0, git_workflow / 20),
                }
            )

        return patterns

    def get_time_distribution(self) -> Dict[int, int]:
        """Get distribution of tool usage by hour."""
        hours = Counter()
        for e in self.tool_events:
            ts = e.get("timestamp", "")
            if ts:
                try:
                    hour = datetime.fromisoformat(ts).hour
                    hours[hour] += 1
                except:
                    pass
        return dict(hours)

    def generate_skill_candidates(self) -> List[dict]:
        """Generate potential skill definitions from patterns."""
        candidates = []

        sequences = self.detect_sequences()
        workflow_patterns = self.detect_workflow_patterns()

        # Convert high-frequency sequences to skill candidates
        for seq, count in sorted(sequences.items(), key=lambda x: -x[1])[:5]:
            tools = seq.split(" -> ")
            if count >= MIN_SEQUENCE_OCCURRENCES:
                candidates.append(
                    {
                        "name": f"sequence_{len(candidates) + 1}",
                        "description": f"Automated sequence: {seq}",
                        "trigger": f"When starting {tools[0]}",
                        "actions": tools,
                        "occurrences": count,
                        "confidence": min(1.0, count / 20),
                        "type": "sequence_skill",
                        "status": "candidate",
                    }
                )

        # Convert workflow patterns to skill candidates
        for pattern in workflow_patterns:
            if pattern["confidence"] >= PATTERN_CONFIDENCE_THRESHOLD:
                candidates.append(
                    {
                        "name": pattern["name"].lower().replace("-", "_"),
                        "description": pattern["description"],
                        "trigger": "Detected workflow pattern",
                        "pattern_type": pattern["type"],
                        "occurrences": pattern["occurrences"],
                        "confidence": pattern["confidence"],
                        "type": "workflow_skill",
                        "status": "candidate",
                    }
                )

        return candidates


class RealtimeDisplay:
    """Helper class for printing formatted realtime data."""

    @staticmethod
    def print_header(text: str):
        """Print a section header."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{text.center(60)}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.END}\n")

    @staticmethod
    def print_subheader(text: str):
        """Print a subsection header."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}--- {text} ---{Colors.END}\n")

    @staticmethod
    def print_bar(label: str, count: int, max_count: int, width: int = 30):
        """Print a bar chart row."""
        if max_count == 0:
            pct = 0
        else:
            pct = count / max_count
        bar_width = int(pct * width)
        bar = Sym.BAR_FULL * bar_width + Sym.BAR_EMPTY * (width - bar_width)
        print(f"  {label:20} {count:4} {Colors.GREEN}{bar}{Colors.END}")

    @staticmethod
    def format_event(event: dict) -> str:
        """Format an event for display."""
        ts = event.get("timestamp", "")[:19]
        data = event.get("data", {})
        tool_name = data.get("tool_name", "unknown")
        icon = TOOL_ICONS.get(tool_name, "📌")
        context = data.get("context", {})
        target = context.get("target", "")

        # Truncate target if too long
        if len(str(target)) > 50:
            target = str(target)[:47] + "..."

        return f"{Colors.DIM}[{ts}]{Colors.END} {icon} {Colors.BOLD}{tool_name:12}{Colors.END} {target}"
