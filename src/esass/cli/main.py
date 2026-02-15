"""
CLI interface for ESASS.

Provides commands for observation, analysis, skill generation, export, and project init.
"""

from datetime import datetime, timedelta
from pathlib import Path

import click

from esass import __version__
from esass.config import get_config, get_data_dir, get_export_dir


@click.group()
@click.version_option(version=__version__)
def esass():
    """ESASS - Emergent Self-Adaptive Skill System"""
    pass


# Register the init command from its own module
from esass.cli.init_cmd import init  # noqa: E402

esass.add_command(init)


@esass.command("audit")
def audit():
    """Launch the skill auditor TUI for human-in-the-middle review."""
    try:
        from esass.tui.auditor import SkillAuditorApp
    except ImportError as e:
        click.echo(f"Error importing TUI: {e}")
        click.echo("Install TUI support: pip install esass[tui]")
        return

    app = SkillAuditorApp()
    app.run()


@esass.command("observe-start")
@click.option("--sessions", default=20, help="Sessions per day to simulate")
@click.option("--days", default=14, help="Days of history to generate")
def observe_start(sessions, days):
    """Start observation mode (generate simulated data)"""
    from esass.observation.logger import ObservationLogger
    from esass.observation.simulator import EventSimulator

    config = get_config()
    data_dir = get_data_dir(config)

    click.echo("[*] Starting ESASS observation...")
    click.echo(f"   Simulating {sessions} sessions/day over {days} days")

    simulator = EventSimulator(seed=42)
    logger = ObservationLogger(data_dir)

    logger.start_observation()

    with click.progressbar(length=sessions * days, label="Generating sessions") as bar:
        entries = simulator.generate_multiple_sessions(
            count=sessions * days, days=days
        )
        bar.update(sessions * days)

    click.echo(f"\n[*] Logging {len(entries)} events...")
    logger.log_many(entries)

    stats = logger.get_stats()
    click.echo("\n[OK] Observation started")
    click.echo(f"  Total events: {stats['total_events']}")
    click.echo(f"  Total sessions: {stats['total_sessions']}")


@esass.command("observe-stop")
def observe_stop():
    """Stop observation mode"""
    from esass.observation.logger import ObservationLogger

    config = get_config()
    data_dir = get_data_dir(config)

    logger = ObservationLogger(data_dir)
    logger.stop_observation()

    click.echo("[OK] Observation stopped")


@esass.command("analyze")
@click.option(
    "--days", default=None, type=int, help="Days of data to analyze (default: all)"
)
@click.option(
    "--enhanced/--basic",
    default=True,
    help="Use enhanced semantic detection (default: enhanced)",
)
@click.option(
    "--granularity",
    type=click.Choice(["coarse", "medium", "fine"]),
    default="medium",
    help="Pattern granularity: coarse (categories), medium (tool+context), fine (all tags)",
)
@click.option("--min-support", default=3, type=int, help="Minimum pattern occurrences")
@click.option(
    "--min-stability", default=1, type=int, help="Minimum days pattern must appear"
)
@click.option(
    "--within-session/--cross-session",
    default=True,
    help="Count patterns within same session (default) or only across sessions",
)
def analyze(days, enhanced, granularity, min_support, min_stability, within_session):
    """Analyze logs and detect patterns with semantic enrichment"""
    from esass.analysis.metrics import rank_patterns
    from esass.analysis.pattern_detector import TemporalPatternDetector
    from esass.analysis.enhanced_pattern_detector import (
        EnhancedPatternDetector,
        SemanticTagExtractor,
    )
    from esass.storage.log_store import LogStore
    from esass.storage.pattern_store import PatternStore

    config = get_config()
    data_dir = get_data_dir(config)

    mode = "enhanced semantic" if enhanced else "basic"
    click.echo(
        f"[*] Analyzing observation logs ({mode} mode, {granularity} granularity)..."
    )

    log_store = LogStore(data_dir)

    if days:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        logs = log_store.read_date_range(start_date, end_date)
        click.echo(f"   Loaded logs from last {days} days")
    else:
        logs = log_store.load_all()
        click.echo("   Loaded all logs")

    click.echo(f"   Processing {len(logs)} events...")

    if enhanced:
        detector = EnhancedPatternDetector(
            min_support=min_support,
            min_confidence=0.6,
            min_stability_days=min_stability,
            granularity=granularity,
            count_within_session=within_session,
        )
        patterns = detector.detect_patterns(logs)

        if logs and len(logs) > 0:
            sample_entry = logs[0]
            sample_tags = SemanticTagExtractor.extract_tags(sample_entry)
            sample_key = SemanticTagExtractor.create_event_key(
                sample_entry, granularity
            )
            click.echo(f"\n   Sample event extraction:")
            click.echo(f"     Raw event_type: {sample_entry.event_type}")
            click.echo(f"     Extracted tags: {sample_tags[:5]}")
            click.echo(f"     Event key: {sample_key}")
    else:
        detector = TemporalPatternDetector(
            min_support=config.pattern_detection.min_support,
            min_confidence=config.pattern_detection.min_confidence,
            min_stability_days=config.pattern_detection.min_stability_days,
        )
        patterns = detector.detect_patterns(logs)

    patterns = rank_patterns(patterns)

    pattern_store = PatternStore(data_dir)
    pattern_store.save_many(patterns)

    candidates = [p for p in patterns if p.skill_candidate]
    meaningful = [p for p in patterns if ":" in str(p.sequence)]

    click.echo("\n[OK] Analysis complete")
    click.echo(f"  Total patterns detected: {len(patterns)}")
    click.echo(f"  Semantically meaningful: {len(meaningful)}")
    click.echo(f"  Skill candidates: {len(candidates)}")

    if patterns:
        click.echo("\nTop 10 patterns by support:")
        for i, pattern in enumerate(patterns[:10], 1):
            status = "[OK]" if pattern.skill_candidate else "•"
            workflow_tags = [
                t
                for t in pattern.tags
                if t.endswith("_workflow")
                or t in ["git", "testing", "file_modification"]
            ]
            workflow_str = (
                f" [{', '.join(workflow_tags)}]" if workflow_tags else ""
            )
            click.echo(f"  {status} {i}. {pattern.description}{workflow_str}")
            click.echo(
                f"     Support: {pattern.support}, Confidence: {pattern.confidence:.0%}, Stability: {pattern.stability_days}d"
            )


@esass.command("generate-skills")
@click.option(
    "--min-support", default=5, type=int, help="Minimum pattern occurrences"
)
@click.option(
    "--min-stability", default=1, type=int, help="Minimum days pattern must appear"
)
@click.option(
    "--min-confidence", default=0.6, type=float, help="Minimum confidence score"
)
@click.option(
    "--use-enhanced/--use-stored",
    default=True,
    help="Use enhanced pattern detector",
)
def generate_skills(min_support, min_stability, min_confidence, use_enhanced):
    """Generate skill manifests from validated patterns"""
    from esass.genesis.candidate import SkillCandidacyEvaluator
    from esass.genesis.template import SkillTemplateGenerator
    from esass.storage.pattern_store import PatternStore
    from esass.storage.skill_store import SkillStore

    config = get_config()
    data_dir = get_data_dir(config)

    click.echo("[*] Generating skills from patterns...")

    pattern_store = PatternStore(data_dir)
    patterns = pattern_store.load_all()

    click.echo(f"   Loaded {len(patterns)} patterns")

    evaluator = SkillCandidacyEvaluator(
        min_support=min_support,
        min_confidence=min_confidence,
        min_stability_days=min_stability,
    )

    candidates = evaluator.filter_candidates(patterns)

    click.echo(
        f"   Found {len(candidates)} skill candidates (support>={min_support}, stability>={min_stability}d)"
    )

    if not candidates:
        click.echo("\nWARNING: No patterns meet skill candidacy criteria")
        return

    generator = SkillTemplateGenerator()
    skills = generator.generate_from_patterns(candidates)

    skill_store = SkillStore(data_dir)
    skill_store.save_many(skills)

    click.echo(f"\n[OK] Generated {len(skills)} skills")

    for i, skill in enumerate(skills[:5], 1):
        click.echo(f"  {i}. {skill.name}")
        click.echo(f"     Capabilities: {', '.join(skill.capabilities[:3])}")


@esass.command("export")
@click.option("--vault", type=click.Path(), help="Path to Obsidian vault")
def export(vault):
    """Export to Obsidian vault"""
    from esass.export.obsidian import ObsidianExporter
    from esass.storage.log_store import LogStore
    from esass.storage.pattern_store import PatternStore
    from esass.storage.skill_store import SkillStore

    config = get_config()
    data_dir = get_data_dir(config)

    if not vault:
        vault = config.export.obsidian_vault or str(get_export_dir(config))

    vault_path = Path(vault)

    click.echo(f"[*] Exporting to Obsidian vault: {vault_path}")

    log_store = LogStore(data_dir)
    pattern_store = PatternStore(data_dir)
    skill_store = SkillStore(data_dir)

    logs = log_store.load_all()
    patterns = pattern_store.load_all()
    skills = skill_store.load_all()

    click.echo(
        f"   Loaded {len(logs)} logs, {len(patterns)} patterns, {len(skills)} skills"
    )

    exporter = ObsidianExporter(vault_path)
    exporter.export_all(logs, patterns, skills)

    click.echo("\n[OK] Export complete")
    click.echo(f"  Location: {vault_path / 'ESASS'}")


@esass.command("pipeline")
@click.option("--sessions", default=20, help="Sessions per day to simulate")
@click.option("--days", default=14, help="Days of history to generate")
@click.option("--vault", type=click.Path(), help="Path to Obsidian vault")
def pipeline(sessions, days, vault):
    """Run full pipeline: observe -> analyze -> generate -> export"""
    click.echo("==> Running full ESASS pipeline\n")

    ctx = click.get_current_context()

    click.echo("=" * 60)
    click.echo("STEP 1: OBSERVATION")
    click.echo("=" * 60)
    ctx.invoke(observe_start, sessions=sessions, days=days)

    click.echo("\n" + "=" * 60)
    click.echo("STEP 2: PATTERN ANALYSIS")
    click.echo("=" * 60)
    ctx.invoke(analyze, days=None)

    click.echo("\n" + "=" * 60)
    click.echo("STEP 3: SKILL GENERATION")
    click.echo("=" * 60)
    ctx.invoke(generate_skills)

    click.echo("\n" + "=" * 60)
    click.echo("STEP 4: EXPORT TO OBSIDIAN")
    click.echo("=" * 60)
    ctx.invoke(export, vault=vault)

    click.echo("\n" + "=" * 60)
    click.echo("[OK] PIPELINE COMPLETE")
    click.echo("=" * 60)


@esass.command("stats")
def stats():
    """Show ESASS statistics"""
    from esass.storage.log_store import LogStore
    from esass.storage.pattern_store import PatternStore
    from esass.storage.skill_store import SkillStore

    config = get_config()
    data_dir = get_data_dir(config)

    log_store = LogStore(data_dir)
    pattern_store = PatternStore(data_dir)
    skill_store = SkillStore(data_dir)

    log_stats = log_store.get_stats()
    pattern_stats = pattern_store.get_stats()
    skill_stats = skill_store.get_stats()

    click.echo("=== ESASS Statistics\n")

    click.echo("Observation Logs:")
    click.echo(f"  Total entries: {log_stats.get('total_events', 0)}")
    click.echo(f"  Total sessions: {log_stats.get('total_sessions', 0)}")

    if log_stats.get("start_date") and log_stats.get("end_date"):
        click.echo(
            f"  Date range: {log_stats['start_date'][:10]} to {log_stats['end_date'][:10]}"
        )

    click.echo("\nPatterns:")
    click.echo(f"  Total patterns: {pattern_stats.get('total_patterns', 0)}")
    click.echo(f"  Skill candidates: {pattern_stats.get('skill_candidates', 0)}")

    if pattern_stats.get("avg_support"):
        click.echo(f"  Avg support: {pattern_stats['avg_support']:.1f}")
        click.echo(f"  Avg confidence: {pattern_stats['avg_confidence']:.1%}")

    click.echo("\nSkills:")
    click.echo(f"  Total skills: {skill_stats.get('total_skills', 0)}")

    if skill_stats.get("by_status"):
        click.echo("  By status:")
        for status, count in skill_stats["by_status"].items():
            click.echo(f"    {status}: {count}")


@esass.command("run", context_settings={"ignore_unknown_options": True})
@click.argument("command", nargs=-1, required=True)
def run(command):
    """Run an interactive command within the ESASS TUI wrapper."""
    try:
        from esass.tui.app import ESASSApp
    except ImportError as e:
        click.echo(f"Error importing TUI: {e}")
        click.echo("Install TUI support: pip install esass[tui]")
        return

    cmd_list = list(command)
    app = ESASSApp(command=cmd_list)
    app.run()


@esass.command("watch")
def watch():
    """Realtime monitoring of tool usage (alias for monitor)."""
    ctx = click.get_current_context()
    ctx.invoke(monitor)


@esass.command("monitor")
def monitor():
    """Realtime monitoring of tool usage."""
    from esass.analysis.realtime import Colors, RealtimeDisplay, Sym
    import json
    import time

    config = get_config()
    data_dir = get_data_dir(config)
    log_dir = data_dir / "logs"
    today = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"log_{today}.jsonl"

    log_dir.mkdir(parents=True, exist_ok=True)

    RealtimeDisplay.print_header("ESASS Realtime Monitor")
    click.echo(f"  Watching: {log_file}")
    click.echo(f"  Press {Colors.BOLD}Ctrl+C{Colors.END} to stop\n")
    click.echo(f"{Colors.DIM}{Sym.HLINE * 60}{Colors.END}")

    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            f.seek(0, 2)
            position = f.tell()
    else:
        position = 0

    event_count = 0

    try:
        while True:
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8") as f:
                    f.seek(position)
                    new_lines = f.readlines()
                    position = f.tell()

                for line in new_lines:
                    try:
                        event = json.loads(line)
                        click.echo(RealtimeDisplay.format_event(event))
                        event_count += 1
                    except Exception:
                        pass

            time.sleep(0.3)

    except KeyboardInterrupt:
        click.echo(f"\n{Colors.DIM}{Sym.HLINE * 60}{Colors.END}")
        click.echo(
            f"\n  {Colors.GREEN}{Sym.CHECK}{Colors.END} Captured {event_count} events this session"
        )


@esass.command("tail")
@click.argument("n", type=int, default=20)
def tail(n):
    """Show last N events."""
    from esass.analysis.realtime import RealtimeDisplay, Colors
    import json

    config = get_config()
    data_dir = get_data_dir(config)
    today = datetime.now().strftime("%Y%m%d")
    log_file = data_dir / "logs" / f"log_{today}.jsonl"

    if not log_file.exists():
        click.echo(f"\n{Colors.YELLOW}No events found today.{Colors.END}\n")
        return

    events = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass

    recent = events[-n:]

    RealtimeDisplay.print_header(f"Last {len(recent)} Events")

    for event in recent:
        click.echo(RealtimeDisplay.format_event(event))

    click.echo()


@esass.command("logs")
@click.option("-n", "--lines", default=50, help="Number of lines to show initially")
@click.option("-f", "--follow", is_flag=True, default=False, help="Follow log output in real-time")
@click.option("--level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]), default=None, help="Filter by minimum log level")
def logs(lines, follow, level):
    """View MCP server logs.

    Shows the local LLM MCP server log file. Use -f to follow in real-time.

    Examples:
        esass logs              # Last 50 lines
        esass logs -f           # Follow in real-time
        esass logs -n 100       # Last 100 lines
        esass logs --level ERROR  # Only errors
    """
    import time as _time

    config = get_config()
    data_dir = get_data_dir(config)
    log_file = data_dir / "logs" / "mcp_server.log"

    if not log_file.exists():
        click.echo(f"No MCP log file found at: {log_file}")
        click.echo("The MCP server writes logs here when running.")
        click.echo("Start it via Claude Code with the local-llm-mcp server configured.")
        return

    # Color map for log levels
    colors = {
        "DEBUG": "\033[90m",     # gray
        "INFO": "\033[36m",      # cyan
        "WARNING": "\033[33m",   # yellow
        "ERROR": "\033[31m",     # red
        "CRITICAL": "\033[1;31m",  # bold red
    }
    reset = "\033[0m"

    level_priority = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
    min_level = level_priority.get(level, 0) if level else 0

    def _colorize(line: str) -> str:
        for lvl, color in colors.items():
            if f"[{lvl}]" in line:
                return f"{color}{line.rstrip()}{reset}"
        return line.rstrip()

    def _passes_filter(line: str) -> bool:
        if min_level == 0:
            return True
        for lvl, priority in level_priority.items():
            if f"[{lvl}]" in line and priority >= min_level:
                return True
        return False

    # Read and display last N lines
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except Exception as e:
        click.echo(f"Error reading log file: {e}")
        return

    filtered = [l for l in all_lines if _passes_filter(l)]
    recent = filtered[-lines:]

    click.echo(f"\033[1m--- MCP Server Logs: {log_file} ---\033[0m")
    if level:
        click.echo(f"\033[90mFiltering: {level}+\033[0m")
    click.echo()

    for line in recent:
        click.echo(_colorize(line))

    if not follow:
        return

    # Follow mode - tail the file
    click.echo(f"\n\033[90m--- Following (Ctrl+C to stop) ---\033[0m\n")

    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            f.seek(0, 2)  # end of file
            while True:
                line = f.readline()
                if line:
                    if _passes_filter(line):
                        click.echo(_colorize(line))
                else:
                    _time.sleep(0.2)
    except KeyboardInterrupt:
        click.echo(f"\n\033[90m--- Stopped ---\033[0m")


@esass.command("setup")
def setup():
    """Show setup instructions (use 'esass init' for automated setup)."""
    from esass.analysis.realtime import Colors, RealtimeDisplay

    config = get_config()
    data_dir = get_data_dir(config)

    RealtimeDisplay.print_header("ESASS Setup")

    click.echo(f"""
  {Colors.BOLD}Automated Setup (recommended):{Colors.END}

     {Colors.GREEN}esass init{Colors.END}

  {Colors.BOLD}Manual Setup:{Colors.END}

  1. Add hooks to {Colors.CYAN}~/.claude/hooks.json{Colors.END}:

     {Colors.DIM}{{
       "hooks": {{
         "PostToolUse": [{{
           "command": "python -m esass.hooks.post_tool_use",
           "timeout": 5000
         }}],
         "SessionStart": [{{
           "command": "python -m esass.hooks.session_start",
           "timeout": 10000
         }}]
       }}
     }}{Colors.END}

  2. Data directory: {Colors.CYAN}{data_dir}{Colors.END}
     (Set ESASS_DATA_DIR environment variable to change)

  3. Monitor: {Colors.GREEN}esass watch{Colors.END}
""")


if __name__ == "__main__":
    esass()
