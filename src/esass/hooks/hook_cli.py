#!/usr/bin/env python3
"""
ESASS CLI - Pattern Analyzer and Realtime Monitor

A simple CLI tool for monitoring Claude Code usage and detecting patterns.

Usage:
    python esass_cli.py watch          # Realtime monitoring
    python esass_cli.py stats          # Session statistics
    python esass_cli.py patterns       # Analyze patterns
    python esass_cli.py skills         # View/generate skills
    python esass_cli.py tail [N]       # Show last N events
    python esass_cli.py setup          # Setup instructions
"""

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================================
# Configuration
# ============================================================================

ESASS_DATA_DIR = Path(os.environ.get(
    'ESASS_DATA_DIR',
    Path.home() / '.esass' / 'data'
))

# Pattern detection thresholds
MIN_PATTERN_OCCURRENCES = 3
MIN_SEQUENCE_OCCURRENCES = 5
PATTERN_CONFIDENCE_THRESHOLD = 0.6

# Check if terminal supports Unicode
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    UNICODE_SUPPORT = True
except:
    UNICODE_SUPPORT = sys.stdout.encoding.lower() in ('utf-8', 'utf8')

# Display colors (ANSI)
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'

# Symbols (with ASCII fallbacks)
class Sym:
    CHECK = '✓' if UNICODE_SUPPORT else '[OK]'
    CROSS = '✗' if UNICODE_SUPPORT else '[X]'
    BULLET = '●' if UNICODE_SUPPORT else '*'
    CIRCLE = '○' if UNICODE_SUPPORT else 'o'
    BAR_FULL = '█' if UNICODE_SUPPORT else '#'
    BAR_EMPTY = '░' if UNICODE_SUPPORT else '-'

# Tool icons
if UNICODE_SUPPORT:
    TOOL_ICONS = {
        'Read': '📖',
        'Write': '✏️',
        'Edit': '🔧',
        'Bash': '💻',
        'Grep': '🔍',
        'Glob': '📂',
        'Task': '🤖',
        'WebFetch': '🌐',
        'WebSearch': '🔎',
        'AskUserQuestion': '❓',
    }
else:
    TOOL_ICONS = {
        'Read': '[R]',
        'Write': '[W]',
        'Edit': '[E]',
        'Bash': '[$]',
        'Grep': '[G]',
        'Glob': '[F]',
        'Task': '[T]',
        'WebFetch': '[U]',
        'WebSearch': '[S]',
        'AskUserQuestion': '[?]',
    }

# ============================================================================
# Data Loading
# ============================================================================

def get_log_files(days: int = 7) -> List[Path]:
    """Get log files from the last N days."""
    log_dir = ESASS_DATA_DIR / 'logs'
    if not log_dir.exists():
        return []

    files = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
        log_file = log_dir / f'log_{date}.jsonl'
        if log_file.exists():
            files.append(log_file)

    return files

def load_events(days: int = 7) -> List[dict]:
    """Load events from log files."""
    events = []
    for log_file in get_log_files(days):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

    # Sort by timestamp
    events.sort(key=lambda e: e.get('timestamp', ''))
    return events

def get_today_log() -> Path:
    """Get today's log file path."""
    today = datetime.now().strftime('%Y%m%d')
    return ESASS_DATA_DIR / 'logs' / f'log_{today}.jsonl'

def load_sequence_state() -> dict:
    """Load sequence tracking state."""
    state_file = ESASS_DATA_DIR / 'state' / 'sequence_state.json'
    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {'recent_tools': [], 'sequences': {}}

# ============================================================================
# Pattern Analysis
# ============================================================================

class PatternAnalyzer:
    """Analyzes tool usage patterns from logged events."""

    def __init__(self, events: List[dict]):
        self.events = events
        self.tool_events = [e for e in events if e.get('event_type') == 'tool_call']

    def get_tool_frequency(self) -> Counter:
        """Count tool usage frequency."""
        return Counter(
            e.get('data', {}).get('tool_name', 'unknown')
            for e in self.tool_events
        )

    def get_category_frequency(self) -> Counter:
        """Count category frequency."""
        return Counter(
            e.get('data', {}).get('context', {}).get('category', 'unknown')
            for e in self.tool_events
        )

    def get_tag_frequency(self) -> Counter:
        """Count tag frequency."""
        tags = Counter()
        for e in self.tool_events:
            for tag in e.get('data', {}).get('context', {}).get('tags', []):
                tags[tag] += 1
        return tags

    def get_file_type_frequency(self) -> Counter:
        """Count file type frequency."""
        file_types = Counter()
        for e in self.tool_events:
            target = e.get('data', {}).get('context', {}).get('target', '')
            if target and isinstance(target, str):
                ext = Path(target).suffix.lower()
                if ext:
                    file_types[ext] += 1
        return file_types

    def detect_sequences(self, min_length: int = 2, max_length: int = 4) -> Dict[str, int]:
        """Detect common tool sequences."""
        sequences = defaultdict(int)

        tools = [
            e.get('data', {}).get('tool_name', 'unknown')
            for e in self.tool_events
        ]

        for length in range(min_length, max_length + 1):
            for i in range(len(tools) - length + 1):
                seq = tuple(tools[i:i + length])
                sequences[' -> '.join(seq)] += 1

        # Filter by minimum occurrences
        return {
            seq: count for seq, count in sequences.items()
            if count >= MIN_SEQUENCE_OCCURRENCES
        }

    def detect_workflow_patterns(self) -> List[dict]:
        """Detect higher-level workflow patterns."""
        patterns = []

        # Pattern: Read-then-Edit (file modification workflow)
        read_edit_count = 0
        for i, e in enumerate(self.tool_events[:-1]):
            if e.get('data', {}).get('tool_name') == 'Read':
                next_e = self.tool_events[i + 1]
                if next_e.get('data', {}).get('tool_name') == 'Edit':
                    # Check if same file
                    file1 = e.get('data', {}).get('context', {}).get('target', '')
                    file2 = next_e.get('data', {}).get('context', {}).get('target', '')
                    if file1 and file1 == file2:
                        read_edit_count += 1

        if read_edit_count >= MIN_PATTERN_OCCURRENCES:
            patterns.append({
                'name': 'Read-Before-Edit',
                'description': 'Always reads file before editing (safe modification pattern)',
                'occurrences': read_edit_count,
                'type': 'safety_pattern',
                'confidence': min(1.0, read_edit_count / 10)
            })

        # Pattern: Search-Read-Edit (exploration-modification workflow)
        search_read_edit = 0
        for i in range(len(self.tool_events) - 2):
            tools = [
                self.tool_events[i + j].get('data', {}).get('tool_name')
                for j in range(3)
            ]
            if tools[0] in ['Grep', 'Glob'] and tools[1] == 'Read' and tools[2] == 'Edit':
                search_read_edit += 1

        if search_read_edit >= MIN_PATTERN_OCCURRENCES:
            patterns.append({
                'name': 'Search-Read-Edit',
                'description': 'Searches codebase, reads results, then edits',
                'occurrences': search_read_edit,
                'type': 'exploration_pattern',
                'confidence': min(1.0, search_read_edit / 10)
            })

        # Pattern: Test-after-Edit (TDD-ish pattern)
        edit_test_count = 0
        for i, e in enumerate(self.tool_events[:-1]):
            if e.get('data', {}).get('tool_name') == 'Edit':
                next_e = self.tool_events[i + 1]
                if next_e.get('data', {}).get('tool_name') == 'Bash':
                    cmd = next_e.get('data', {}).get('parameters', {}).get('command', '')
                    if 'pytest' in cmd or 'test' in cmd.lower():
                        edit_test_count += 1

        if edit_test_count >= MIN_PATTERN_OCCURRENCES:
            patterns.append({
                'name': 'Edit-Then-Test',
                'description': 'Runs tests after editing code',
                'occurrences': edit_test_count,
                'type': 'quality_pattern',
                'confidence': min(1.0, edit_test_count / 10)
            })

        # Pattern: Git workflow
        git_workflow = 0
        for e in self.tool_events:
            if e.get('data', {}).get('tool_name') == 'Bash':
                cmd = e.get('data', {}).get('parameters', {}).get('command', '')
                if cmd.startswith('git '):
                    git_workflow += 1

        if git_workflow >= MIN_PATTERN_OCCURRENCES:
            patterns.append({
                'name': 'Git-Integrated',
                'description': 'Regular use of git commands for version control',
                'occurrences': git_workflow,
                'type': 'workflow_pattern',
                'confidence': min(1.0, git_workflow / 20)
            })

        return patterns

    def get_time_distribution(self) -> Dict[int, int]:
        """Get distribution of tool usage by hour."""
        hours = Counter()
        for e in self.tool_events:
            ts = e.get('timestamp', '')
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
            tools = seq.split(' -> ')
            if count >= MIN_SEQUENCE_OCCURRENCES:
                candidates.append({
                    'name': f"sequence_{len(candidates) + 1}",
                    'description': f"Automated sequence: {seq}",
                    'trigger': f"When starting {tools[0]}",
                    'actions': tools,
                    'occurrences': count,
                    'confidence': min(1.0, count / 20),
                    'type': 'sequence_skill',
                    'status': 'candidate'
                })

        # Convert workflow patterns to skill candidates
        for pattern in workflow_patterns:
            if pattern['confidence'] >= PATTERN_CONFIDENCE_THRESHOLD:
                candidates.append({
                    'name': pattern['name'].lower().replace('-', '_'),
                    'description': pattern['description'],
                    'trigger': 'Detected workflow pattern',
                    'pattern_type': pattern['type'],
                    'occurrences': pattern['occurrences'],
                    'confidence': pattern['confidence'],
                    'type': 'workflow_skill',
                    'status': 'candidate'
                })

        return candidates

# ============================================================================
# Display Functions
# ============================================================================

def print_header(text: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.END}\n")

def print_subheader(text: str):
    """Print a subsection header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}--- {text} ---{Colors.END}\n")

def print_bar(label: str, count: int, max_count: int, width: int = 30):
    """Print a bar chart row."""
    if max_count == 0:
        pct = 0
    else:
        pct = count / max_count
    bar_width = int(pct * width)
    bar = Sym.BAR_FULL * bar_width + Sym.BAR_EMPTY * (width - bar_width)
    print(f"  {label:20} {count:4} {Colors.GREEN}{bar}{Colors.END}")

def format_event(event: dict) -> str:
    """Format an event for display."""
    ts = event.get('timestamp', '')[:19]
    data = event.get('data', {})
    tool_name = data.get('tool_name', 'unknown')
    icon = TOOL_ICONS.get(tool_name, '📌')
    context = data.get('context', {})
    target = context.get('target', '')

    # Truncate target if too long
    if len(str(target)) > 50:
        target = str(target)[:47] + '...'

    return f"{Colors.DIM}[{ts}]{Colors.END} {icon} {Colors.BOLD}{tool_name:12}{Colors.END} {target}"

# ============================================================================
# CLI Commands
# ============================================================================

def cmd_watch(args):
    """Realtime monitoring of tool usage."""
    log_file = get_today_log()
    log_file.parent.mkdir(parents=True, exist_ok=True)

    print_header("ESASS Realtime Monitor")
    print(f"  Watching: {log_file}")
    print(f"  Press {Colors.BOLD}Ctrl+C{Colors.END} to stop\n")
    print(f"{Colors.DIM}{'─' * 60}{Colors.END}")

    # Track file position
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8') as f:
            f.seek(0, 2)
            position = f.tell()
    else:
        position = 0

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
                        event = json.loads(line)
                        print(format_event(event))
                        event_count += 1
                    except:
                        pass

            time.sleep(0.3)

    except KeyboardInterrupt:
        print(f"\n{Colors.DIM}{'─' * 60}{Colors.END}")
        print(f"\n  {Colors.GREEN}{Sym.CHECK}{Colors.END} Captured {event_count} events this session")
        print(f"  Run {Colors.BOLD}esass_cli.py stats{Colors.END} for analysis\n")

def cmd_stats(args):
    """Show session statistics."""
    events = load_events(args.days)

    if not events:
        print(f"\n{Colors.YELLOW}No events found in the last {args.days} days.{Colors.END}")
        print(f"Make sure the hook is configured and you've used Claude Code.\n")
        return

    analyzer = PatternAnalyzer(events)

    print_header(f"ESASS Statistics ({args.days} days)")

    # Overview
    print(f"  Total events: {Colors.BOLD}{len(events)}{Colors.END}")
    print(f"  Tool calls:   {Colors.BOLD}{len(analyzer.tool_events)}{Colors.END}")

    if events:
        first = events[0].get('timestamp', '')[:10]
        last = events[-1].get('timestamp', '')[:10]
        print(f"  Date range:   {first} to {last}")

    # Tool frequency
    print_subheader("Tool Usage")
    tool_freq = analyzer.get_tool_frequency()
    max_count = max(tool_freq.values()) if tool_freq else 1
    for tool, count in tool_freq.most_common(10):
        icon = TOOL_ICONS.get(tool, '📌')
        print_bar(f"{icon} {tool}", count, max_count)

    # Category breakdown
    print_subheader("Categories")
    cat_freq = analyzer.get_category_frequency()
    max_count = max(cat_freq.values()) if cat_freq else 1
    for cat, count in cat_freq.most_common():
        print_bar(cat, count, max_count)

    # File types
    print_subheader("File Types")
    file_freq = analyzer.get_file_type_frequency()
    if file_freq:
        max_count = max(file_freq.values())
        for ext, count in file_freq.most_common(8):
            print_bar(ext, count, max_count)
    else:
        print(f"  {Colors.DIM}No file operations recorded{Colors.END}")

    # Tags
    print_subheader("Tags")
    tag_freq = analyzer.get_tag_frequency()
    if tag_freq:
        max_count = max(tag_freq.values())
        for tag, count in tag_freq.most_common(8):
            print_bar(tag, count, max_count)
    else:
        print(f"  {Colors.DIM}No tags recorded{Colors.END}")

    print()

def cmd_patterns(args):
    """Analyze and display patterns."""
    events = load_events(args.days)

    if not events:
        print(f"\n{Colors.YELLOW}No events found.{Colors.END}\n")
        return

    analyzer = PatternAnalyzer(events)

    print_header("Pattern Analysis")

    # Sequences
    print_subheader("Detected Sequences")
    sequences = analyzer.detect_sequences()
    if sequences:
        for seq, count in sorted(sequences.items(), key=lambda x: -x[1])[:10]:
            confidence = min(1.0, count / 20)
            conf_bar = Sym.BULLET * int(confidence * 5) + Sym.CIRCLE * (5 - int(confidence * 5))
            print(f"  {Colors.GREEN}{count:3}x{Colors.END} {seq}")
            print(f"       {Colors.DIM}confidence: {conf_bar} ({confidence:.0%}){Colors.END}")
    else:
        print(f"  {Colors.DIM}No recurring sequences found (need {MIN_SEQUENCE_OCCURRENCES}+ occurrences){Colors.END}")

    # Workflow patterns
    print_subheader("Workflow Patterns")
    patterns = analyzer.detect_workflow_patterns()
    if patterns:
        for p in patterns:
            status = Colors.GREEN + Sym.CHECK if p['confidence'] >= PATTERN_CONFIDENCE_THRESHOLD else Colors.YELLOW + Sym.CIRCLE
            print(f"  {status}{Colors.END} {Colors.BOLD}{p['name']}{Colors.END}")
            print(f"     {p['description']}")
            print(f"     {Colors.DIM}occurrences: {p['occurrences']}, confidence: {p['confidence']:.0%}{Colors.END}")
            print()
    else:
        print(f"  {Colors.DIM}No workflow patterns detected yet{Colors.END}")

    # Time distribution
    print_subheader("Activity by Hour")
    time_dist = analyzer.get_time_distribution()
    if time_dist:
        max_count = max(time_dist.values())
        for hour in range(24):
            count = time_dist.get(hour, 0)
            bar_len = int((count / max_count) * 20) if max_count > 0 else 0
            bar = Sym.BAR_FULL * bar_len
            if count > 0:
                print(f"  {hour:02d}:00 {Colors.BLUE}{bar}{Colors.END} {count}")
    else:
        print(f"  {Colors.DIM}No time data available{Colors.END}")

    print()

def cmd_skills(args):
    """View and generate skill candidates."""
    events = load_events(args.days)

    if not events:
        print(f"\n{Colors.YELLOW}No events found.{Colors.END}\n")
        return

    analyzer = PatternAnalyzer(events)
    candidates = analyzer.generate_skill_candidates()

    print_header("Skill Candidates")

    if not candidates:
        print(f"  {Colors.YELLOW}No skill candidates detected yet.{Colors.END}")
        print(f"  {Colors.DIM}Continue using Claude Code to build up patterns.{Colors.END}")
        print(f"  {Colors.DIM}Need at least {MIN_SEQUENCE_OCCURRENCES} occurrences of a pattern.{Colors.END}\n")
        return

    for i, skill in enumerate(candidates, 1):
        conf = skill['confidence']
        if conf >= 0.8:
            status = f"{Colors.GREEN}[HIGH]{Colors.END}"
        elif conf >= 0.6:
            status = f"{Colors.YELLOW}[MED]{Colors.END}"
        else:
            status = f"{Colors.DIM}[LOW]{Colors.END}"

        print(f"  {Colors.BOLD}#{i} {skill['name']}{Colors.END} {status}")
        print(f"     Type: {skill['type']}")
        print(f"     {skill['description']}")
        print(f"     Confidence: {conf:.0%} ({skill['occurrences']} occurrences)")

        if 'actions' in skill:
            print(f"     Actions: {' → '.join(skill['actions'])}")

        print()

    # Save candidates if requested
    if args.save:
        skills_file = ESASS_DATA_DIR / 'skills' / 'candidates.json'
        skills_file.parent.mkdir(parents=True, exist_ok=True)

        with open(skills_file, 'w') as f:
            json.dump({
                'generated_at': datetime.now().isoformat(),
                'candidates': candidates
            }, f, indent=2)

        print(f"  {Colors.GREEN}{Sym.CHECK}{Colors.END} Saved to {skills_file}\n")

def cmd_tail(args):
    """Show last N events."""
    events = load_events(1)  # Just today

    if not events:
        print(f"\n{Colors.YELLOW}No events found today.{Colors.END}\n")
        return

    n = args.n or 20
    recent = events[-n:]

    print_header(f"Last {len(recent)} Events")

    for event in recent:
        print(format_event(event))

    print()

def cmd_setup(args):
    """Show setup instructions."""
    hook_path = Path(__file__).resolve()

    print_header("ESASS Setup")

    print(f"""
  {Colors.BOLD}1. Configure Claude Code Hook{Colors.END}

     Add this to {Colors.CYAN}~/.claude/hooks.json{Colors.END}:

     {Colors.DIM}{{
       "hooks": {{
         "PostToolUse": [{{
           "command": "python -m esass.hooks.post_tool_use",
           "timeout": 5000
         }}]
       }}
     }}{Colors.END}

  {Colors.BOLD}2. Verify Data Directory{Colors.END}

     Data will be stored in: {Colors.CYAN}{ESASS_DATA_DIR}{Colors.END}

  {Colors.BOLD}3. Start Monitoring{Colors.END}

     In a separate terminal, run:
     {Colors.GREEN}python {hook_path} watch{Colors.END}

  {Colors.BOLD}4. Use Claude Code Normally{Colors.END}

     All tool usage will be captured automatically.

  {Colors.BOLD}5. Analyze Patterns{Colors.END}

     {Colors.GREEN}python {hook_path} stats{Colors.END}     - View statistics
     {Colors.GREEN}python {hook_path} patterns{Colors.END}  - Analyze patterns
     {Colors.GREEN}python {hook_path} skills{Colors.END}    - Generate skill candidates
""")

def cmd_clear(args):
    """Clear all ESASS data."""
    import shutil

    if not args.force:
        print(f"\n{Colors.YELLOW}Warning:{Colors.END} This will delete all ESASS data.")
        print(f"Data directory: {ESASS_DATA_DIR}")
        confirm = input("\nType 'yes' to confirm: ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            return

    if ESASS_DATA_DIR.exists():
        shutil.rmtree(ESASS_DATA_DIR)
        print(f"\n{Colors.GREEN}{Sym.CHECK}{Colors.END} Cleared all data.\n")
    else:
        print(f"\n{Colors.DIM}No data to clear.{Colors.END}\n")

def cmd_test(args):
    """Test the ESASS setup by simulating events."""
    import subprocess

    print_header("ESASS Setup Test")

    # 1. Check data directory
    print(f"  {Colors.BOLD}1. Data Directory{Colors.END}")
    ESASS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    (ESASS_DATA_DIR / 'logs').mkdir(exist_ok=True)
    print(f"     {Colors.GREEN}{Sym.CHECK}{Colors.END} {ESASS_DATA_DIR}")

    # 2. Test hook script
    print(f"\n  {Colors.BOLD}2. Hook Script{Colors.END}")
    # Check hook is importable
    try:
        import esass.hooks.post_tool_use
        hook_path = Path(esass.hooks.post_tool_use.__file__)
        print(f"     {Colors.GREEN}{Sym.CHECK}{Colors.END} Found: {hook_path}")
    except ImportError:
        print(f"     {Colors.RED}{Sym.CROSS}{Colors.END} Hook module not importable")
        return

    # 3. Simulate a tool call
    print(f"\n  {Colors.BOLD}3. Simulating Tool Calls{Colors.END}")

    test_events = [
        {'tool_name': 'Read', 'tool_input': {'file_path': '/test/example.py'}, 'tool_output': 'def hello(): pass'},
        {'tool_name': 'Grep', 'tool_input': {'pattern': 'def.*hello'}, 'tool_output': 'example.py:1'},
        {'tool_name': 'Edit', 'tool_input': {'file_path': '/test/example.py', 'old_string': 'pass', 'new_string': 'print("hi")'}, 'tool_output': 'ok'},
        {'tool_name': 'Bash', 'tool_input': {'command': 'pytest tests/'}, 'tool_output': 'PASSED'},
        {'tool_name': 'Read', 'tool_input': {'file_path': '/test/example.py'}, 'tool_output': 'def hello(): print("hi")'},
    ]

    for event in test_events:
        try:
            result = subprocess.run(
                [sys.executable, str(hook_path)],
                input=json.dumps(event),
                capture_output=True,
                text=True,
                timeout=5
            )
            tool = event['tool_name']
            icon = TOOL_ICONS.get(tool, '📌')
            print(f"     {Colors.GREEN}{Sym.CHECK}{Colors.END} {icon} {tool}")
        except Exception as e:
            print(f"     {Colors.RED}{Sym.CROSS}{Colors.END} Error: {e}")

    # 4. Verify log file
    print(f"\n  {Colors.BOLD}4. Verifying Log File{Colors.END}")
    log_file = get_today_log()
    if log_file.exists():
        with open(log_file, 'r') as f:
            lines = f.readlines()
        print(f"     {Colors.GREEN}{Sym.CHECK}{Colors.END} Log file has {len(lines)} entries")
    else:
        print(f"     {Colors.RED}{Sym.CROSS}{Colors.END} Log file not created")

    # 5. Check sequence state
    print(f"\n  {Colors.BOLD}5. Checking Sequence State{Colors.END}")
    state = load_sequence_state()
    seq_count = len(state.get('sequences', {}))
    print(f"     {Colors.GREEN}{Sym.CHECK}{Colors.END} Tracking {seq_count} sequences")

    # Summary
    print(f"\n  {Colors.GREEN}{'─' * 50}{Colors.END}")
    print(f"  {Colors.BOLD}Setup test complete!{Colors.END}")
    print(f"\n  Next steps:")
    print(f"  1. Add hook to {Colors.CYAN}~/.claude/hooks.json{Colors.END}")
    print(f"  2. Run {Colors.GREEN}python esass_cli.py watch{Colors.END} in another terminal")
    print(f"  3. Use Claude Code normally\n")

# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ESASS CLI - Pattern Analyzer and Realtime Monitor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python esass_cli.py watch          Start realtime monitoring
  python esass_cli.py stats          Show session statistics
  python esass_cli.py patterns       Analyze patterns
  python esass_cli.py skills --save  Generate and save skill candidates
  python esass_cli.py tail 50        Show last 50 events
  python esass_cli.py setup          Show setup instructions
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # watch
    watch_parser = subparsers.add_parser('watch', help='Realtime monitoring')

    # stats
    stats_parser = subparsers.add_parser('stats', help='Show session statistics')
    stats_parser.add_argument('--days', type=int, default=7, help='Days to analyze')

    # patterns
    patterns_parser = subparsers.add_parser('patterns', help='Analyze patterns')
    patterns_parser.add_argument('--days', type=int, default=7, help='Days to analyze')

    # skills
    skills_parser = subparsers.add_parser('skills', help='View/generate skill candidates')
    skills_parser.add_argument('--days', type=int, default=7, help='Days to analyze')
    skills_parser.add_argument('--save', action='store_true', help='Save candidates to file')

    # tail
    tail_parser = subparsers.add_parser('tail', help='Show last N events')
    tail_parser.add_argument('n', type=int, nargs='?', default=20, help='Number of events')

    # setup
    setup_parser = subparsers.add_parser('setup', help='Show setup instructions')

    # clear
    clear_parser = subparsers.add_parser('clear', help='Clear all ESASS data')
    clear_parser.add_argument('--force', action='store_true', help='Skip confirmation')

    # test
    test_parser = subparsers.add_parser('test', help='Test ESASS setup')

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    commands = {
        'watch': cmd_watch,
        'stats': cmd_stats,
        'patterns': cmd_patterns,
        'skills': cmd_skills,
        'tail': cmd_tail,
        'setup': cmd_setup,
        'clear': cmd_clear,
        'test': cmd_test,
    }

    commands[args.command](args)

if __name__ == '__main__':
    main()
