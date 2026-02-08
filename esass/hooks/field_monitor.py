#!/usr/bin/env python3
"""
ESASS Field Monitor
===================
Visualizes the protection gradient and skill formation field.

Shows:
- Trust radius expanding/contracting
- Zone distribution (Exploration → Learning → Trusted → Core)
- Skill crystallization progress
- Field health and dynamics
"""

import json
import math
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

# Configuration
ESASS_DATA_DIR = Path(os.environ.get('ESASS_DATA_DIR', Path.home() / '.esass' / 'data'))
LOG_DIR = ESASS_DATA_DIR / 'logs'

# Unicode support
UNICODE_OK = sys.stdout.encoding and sys.stdout.encoding.lower() in ('utf-8', 'utf8')

# Characters
BLOCK_FULL = '█' if UNICODE_OK else '#'
BLOCK_MED = '▓' if UNICODE_OK else '='
BLOCK_LIGHT = '░' if UNICODE_OK else '-'
BULLET = '●' if UNICODE_OK else '*'
CIRCLE = '○' if UNICODE_OK else 'o'
ARROW = '→' if UNICODE_OK else '->'

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
    CLEAR = '\033[2J\033[H'


class FieldState:
    """Tracks the state of the ESASS protection field."""

    def __init__(self):
        self.total_events = 0
        self.sequences = Counter()
        self.tool_counts = Counter()
        self.confidence_history = deque(maxlen=100)
        self.skill_candidates = []
        self.start_time = datetime.now()

    def load_from_files(self):
        """Load state from ESASS data files."""
        # Load sequence state
        seq_file = ESASS_DATA_DIR / 'state' / 'sequence_state.json'
        if seq_file.exists():
            try:
                with open(seq_file, 'r') as f:
                    data = json.load(f)
                    self.sequences = Counter(data.get('sequences', {}))
            except:
                pass

        # Load today's events
        today = datetime.now().strftime('%Y%m%d')
        log_file = LOG_DIR / f'log_{today}.jsonl'
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            self.total_events += 1
                            tool = event.get('data', {}).get('tool_name', 'unknown')
                            self.tool_counts[tool] += 1
                        except:
                            pass
            except:
                pass

        # Calculate skill candidates
        self._calculate_skills()

    def _calculate_skills(self):
        """Calculate skill candidates from sequences."""
        self.skill_candidates = []
        for seq, count in self.sequences.most_common(10):
            if count >= 3:
                confidence = min(1.0, count / 20)
                zone = self._get_zone(confidence)
                self.skill_candidates.append({
                    'sequence': seq,
                    'count': count,
                    'confidence': confidence,
                    'zone': zone
                })

    def _get_zone(self, confidence):
        """Determine which zone a confidence level falls into."""
        if confidence >= 0.7:
            return 'trusted'
        elif confidence >= 0.3:
            return 'learning'
        else:
            return 'exploration'

    @property
    def trust_radius(self):
        """Calculate the overall trust radius (0-1)."""
        if not self.skill_candidates:
            return 0.1
        avg_conf = sum(s['confidence'] for s in self.skill_candidates) / len(self.skill_candidates)
        return min(1.0, avg_conf + 0.1)

    @property
    def zone_distribution(self):
        """Get distribution of skills across zones."""
        zones = {'exploration': 0, 'learning': 0, 'trusted': 0}
        for skill in self.skill_candidates:
            zones[skill['zone']] += 1
        return zones

    @property
    def field_health(self):
        """Calculate field health status."""
        if self.total_events < 10:
            return 'initializing'
        elif len(self.skill_candidates) == 0:
            return 'observing'
        elif self.trust_radius < 0.3:
            return 'learning'
        elif self.trust_radius < 0.6:
            return 'expanding'
        else:
            return 'stable'


def render_field_visualization(state: FieldState):
    """Render ASCII art field visualization."""
    radius = state.trust_radius
    zones = state.zone_distribution

    # Create concentric circle visualization
    width = 50
    height = 15
    center_x = width // 2
    center_y = height // 2

    # Zone radii based on trust
    core_r = 2
    trusted_r = 3 + int(radius * 3)
    learning_r = trusted_r + 2
    exploration_r = learning_r + 3

    lines = []
    for y in range(height):
        line = ""
        for x in range(width):
            dx = (x - center_x) / 2  # Adjust for character aspect ratio
            dy = y - center_y
            dist = math.sqrt(dx*dx + dy*dy)

            if dist < core_r:
                line += f"{C.WHITE}{BLOCK_FULL}{C.RESET}"
            elif dist < trusted_r:
                line += f"{C.GREEN}{BLOCK_MED}{C.RESET}"
            elif dist < learning_r:
                line += f"{C.YELLOW}{BLOCK_LIGHT}{C.RESET}"
            elif dist < exploration_r:
                line += f"{C.BLUE}.{C.RESET}"
            else:
                line += " "
        lines.append(line)

    return lines


def render_dashboard(state: FieldState):
    """Render the full field monitor dashboard."""
    print(C.CLEAR, end='')

    # Header
    print(f"{C.BOLD}{C.CYAN}{'═' * 70}")
    print(f"  ESASS PROTECTION FIELD MONITOR              {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'═' * 70}{C.RESET}")
    print()

    # Field visualization
    field_lines = render_field_visualization(state)

    # Stats panel (right side)
    stats = [
        f"{C.BOLD}Field Metrics{C.RESET}",
        f"",
        f"Trust Radius: {state.trust_radius:.0%}",
        f"Total Events: {state.total_events}",
        f"Patterns:     {len(state.sequences)}",
        f"Skills:       {len(state.skill_candidates)}",
        f"",
        f"{C.BOLD}Zone Distribution{C.RESET}",
        f"",
        f"{C.GREEN}Trusted:{C.RESET}     {state.zone_distribution['trusted']}",
        f"{C.YELLOW}Learning:{C.RESET}    {state.zone_distribution['learning']}",
        f"{C.BLUE}Exploration:{C.RESET} {state.zone_distribution['exploration']}",
        f"",
        f"{C.BOLD}Field Status{C.RESET}",
        f"",
    ]

    # Health indicator
    health = state.field_health
    health_colors = {
        'initializing': C.DIM,
        'observing': C.BLUE,
        'learning': C.YELLOW,
        'expanding': C.GREEN,
        'stable': C.CYAN
    }
    stats.append(f"{health_colors.get(health, C.WHITE)}{health.upper()}{C.RESET}")

    # Print field and stats side by side
    print(f"  {C.BOLD}Protection Gradient{C.RESET}")
    print()
    for i, line in enumerate(field_lines):
        stat = stats[i] if i < len(stats) else ""
        print(f"  {line}    {stat}")
    print()

    # Legend
    print(f"  {C.DIM}Legend: {C.WHITE}{BLOCK_FULL}{C.RESET}=Core  {C.GREEN}{BLOCK_MED}{C.RESET}=Trusted  {C.YELLOW}{BLOCK_LIGHT}{C.RESET}=Learning  {C.BLUE}.{C.RESET}=Exploration{C.RESET}")
    print()

    # Trust radius gauge
    bar_width = 50
    filled = int(state.trust_radius * bar_width)
    bar = f"{C.GREEN}{BLOCK_FULL * filled}{C.DIM}{BLOCK_LIGHT * (bar_width - filled)}{C.RESET}"
    print(f"  {C.BOLD}Trust Radius{C.RESET}")
    print(f"  [{bar}] {state.trust_radius:.0%}")
    print()

    # Skill formation tracker
    print(f"  {C.BOLD}Skill Formation{C.RESET}")
    print(f"  {C.DIM}{'─' * 60}{C.RESET}")

    if state.skill_candidates:
        for skill in state.skill_candidates[:6]:
            conf = skill['confidence']
            zone = skill['zone']
            zone_color = {'trusted': C.GREEN, 'learning': C.YELLOW, 'exploration': C.BLUE}[zone]

            # Progress bar
            prog_width = 20
            prog_filled = int(conf * prog_width)
            prog_bar = BULLET * prog_filled + CIRCLE * (prog_width - prog_filled)

            seq = skill['sequence'][:30]
            print(f"  {zone_color}{prog_bar}{C.RESET} {conf:4.0%} {seq}")
    else:
        print(f"  {C.DIM}Observing patterns... skills will emerge{C.RESET}")

    print(f"  {C.DIM}{'─' * 60}{C.RESET}")
    print()

    # Activity indicator
    uptime = datetime.now() - state.start_time
    print(f"  {C.DIM}Uptime: {str(uptime).split('.')[0]} | Press Ctrl+C to exit{C.RESET}")


def main():
    """Main monitoring loop."""
    state = FieldState()

    try:
        while True:
            state.load_from_files()
            render_dashboard(state)
            time.sleep(1.0)

    except KeyboardInterrupt:
        print(f"\n{C.GREEN}Field monitor stopped.{C.RESET}")


if __name__ == '__main__':
    main()
