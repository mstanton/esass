"""
CLI interface for ESASS prototype.

Provides commands for observation, analysis, skill generation, and export.
"""

import click
from pathlib import Path
from datetime import datetime, timedelta

from esass_prototype.config import get_config, get_data_dir, get_export_dir
from esass_prototype.observation.simulator import EventSimulator
from esass_prototype.observation.logger import ObservationLogger
from esass_prototype.storage.log_store import LogStore
from esass_prototype.storage.pattern_store import PatternStore
from esass_prototype.storage.skill_store import SkillStore
from esass_prototype.analysis.pattern_detector import TemporalPatternDetector
from esass_prototype.analysis.metrics import rank_patterns
from esass_prototype.genesis.candidate import SkillCandidacyEvaluator
from esass_prototype.genesis.template import SkillTemplateGenerator
from esass_prototype.export.obsidian import ObsidianExporter


@click.group()
@click.version_option(version="0.1.0")
def esass():
    """ESASS Prototype - Emergent Self-Adaptive Skill System"""
    pass


@esass.command("observe-start")
@click.option('--sessions', default=20, help='Sessions per day to simulate')
@click.option('--days', default=14, help='Days of history to generate')
def observe_start(sessions, days):
    """Start observation mode (generate simulated data)"""
    config = get_config()
    data_dir = get_data_dir(config)

    click.echo("[*] Starting ESASS observation...")
    click.echo(f"   Simulating {sessions} sessions/day over {days} days")

    # Initialize components
    simulator = EventSimulator(seed=42)
    logger = ObservationLogger(data_dir)

    # Start observation
    logger.start_observation()

    # Generate simulated sessions
    with click.progressbar(
        length=sessions * days,
        label='Generating sessions'
    ) as bar:
        entries = simulator.generate_multiple_sessions(
            count=sessions * days,
            days=days
        )
        bar.update(sessions * days)

    # Log entries
    click.echo(f"\n[*] Logging {len(entries)} events...")
    logger.log_many(entries)

    # Show stats
    stats = logger.get_stats()
    click.echo(f"\n[OK] Observation started")
    click.echo(f"  Total events: {stats['total_events']}")
    click.echo(f"  Total sessions: {stats['total_sessions']}")


@esass.command("observe-stop")
def observe_stop():
    """Stop observation mode"""
    config = get_config()
    data_dir = get_data_dir(config)

    logger = ObservationLogger(data_dir)
    logger.stop_observation()

    click.echo("[OK] Observation stopped")


@esass.command("analyze")
@click.option('--days', default=None, type=int, help='Days of data to analyze (default: all)')
def analyze(days):
    """Analyze logs and detect patterns"""
    config = get_config()
    data_dir = get_data_dir(config)

    click.echo("[*] Analyzing observation logs...")

    # Load logs
    log_store = LogStore(data_dir)

    if days:
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        logs = log_store.load_by_date_range(start_date, end_date)
        click.echo(f"   Loaded logs from last {days} days")
    else:
        logs = log_store.load_all()
        click.echo(f"   Loaded all logs")

    click.echo(f"   Processing {len(logs)} events...")

    # Detect patterns
    detector = TemporalPatternDetector(
        min_support=config.pattern_detection.min_support,
        min_confidence=config.pattern_detection.min_confidence,
        min_stability_days=config.pattern_detection.min_stability_days
    )

    patterns = detector.detect_patterns(logs)

    # Rank patterns
    patterns = rank_patterns(patterns)

    # Save patterns
    pattern_store = PatternStore(data_dir)
    pattern_store.save_many(patterns)

    # Report
    candidates = [p for p in patterns if p.skill_candidate]

    click.echo(f"\n[OK] Analysis complete")
    click.echo(f"  Total patterns detected: {len(patterns)}")
    click.echo(f"  Skill candidates: {len(candidates)}")

    if patterns:
        click.echo(f"\nTop 5 patterns by support:")
        for i, pattern in enumerate(patterns[:5], 1):
            status = "[OK]" if pattern.skill_candidate else "•"
            click.echo(f"  {status} {i}. {pattern.description}")
            click.echo(f"     Support: {pattern.support}, Confidence: {pattern.confidence:.0%}, Stability: {pattern.stability_days}d")


@esass.command("generate-skills")
def generate_skills():
    """Generate skill manifests from validated patterns"""
    config = get_config()
    data_dir = get_data_dir(config)

    click.echo("[*] Generating skills from patterns...")

    # Load patterns
    pattern_store = PatternStore(data_dir)
    patterns = pattern_store.load_all()

    click.echo(f"   Loaded {len(patterns)} patterns")

    # Evaluate candidacy
    evaluator = SkillCandidacyEvaluator(
        min_support=config.pattern_detection.min_support,
        min_confidence=config.pattern_detection.min_confidence,
        min_stability_days=config.pattern_detection.min_stability_days
    )

    candidates = evaluator.filter_candidates(patterns)

    click.echo(f"   Found {len(candidates)} skill candidates")

    if not candidates:
        click.echo("\nWARNING: No patterns meet skill candidacy criteria")
        return

    # Generate skills
    generator = SkillTemplateGenerator()
    skills = generator.generate_from_patterns(candidates)

    # Save skills
    skill_store = SkillStore(data_dir)
    skill_store.save_many(skills)

    click.echo(f"\n[OK] Generated {len(skills)} skills")

    for i, skill in enumerate(skills[:5], 1):
        click.echo(f"  {i}. {skill.name}")
        click.echo(f"     Capabilities: {', '.join(skill.capabilities[:3])}")


@esass.command("export")
@click.option('--vault', type=click.Path(), help='Path to Obsidian vault')
def export(vault):
    """Export to Obsidian vault"""
    config = get_config()
    data_dir = get_data_dir(config)

    # Determine vault path
    if not vault:
        vault = config.export.obsidian_vault or str(get_export_dir(config))

    vault_path = Path(vault)

    click.echo(f"[*] Exporting to Obsidian vault: {vault_path}")

    # Load all data
    log_store = LogStore(data_dir)
    pattern_store = PatternStore(data_dir)
    skill_store = SkillStore(data_dir)

    logs = log_store.load_all()
    patterns = pattern_store.load_all()
    skills = skill_store.load_all()

    click.echo(f"   Loaded {len(logs)} logs, {len(patterns)} patterns, {len(skills)} skills")

    # Export
    exporter = ObsidianExporter(vault_path)
    exporter.export_all(logs, patterns, skills)

    click.echo(f"\n[OK] Export complete")
    click.echo(f"  Location: {vault_path / 'ESASS'}")


@esass.command("pipeline")
@click.option('--sessions', default=20, help='Sessions per day to simulate')
@click.option('--days', default=14, help='Days of history to generate')
@click.option('--vault', type=click.Path(), help='Path to Obsidian vault')
def pipeline(sessions, days, vault):
    """Run full pipeline: observe -> analyze -> generate -> export"""
    click.echo("==> Running full ESASS pipeline\n")

    # Step 1: Observe
    click.echo("=" * 60)
    click.echo("STEP 1: OBSERVATION")
    click.echo("=" * 60)
    ctx = click.get_current_context()
    ctx.invoke(observe_start, sessions=sessions, days=days)

    # Step 2: Analyze
    click.echo("\n" + "=" * 60)
    click.echo("STEP 2: PATTERN ANALYSIS")
    click.echo("=" * 60)
    ctx.invoke(analyze, days=None)

    # Step 3: Generate skills
    click.echo("\n" + "=" * 60)
    click.echo("STEP 3: SKILL GENERATION")
    click.echo("=" * 60)
    ctx.invoke(generate_skills)

    # Step 4: Export
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
    config = get_config()
    data_dir = get_data_dir(config)

    # Get stats from all stores
    log_store = LogStore(data_dir)
    pattern_store = PatternStore(data_dir)
    skill_store = SkillStore(data_dir)

    log_stats = log_store.get_stats()
    pattern_stats = pattern_store.get_stats()
    skill_stats = skill_store.get_stats()

    click.echo("=== ESASS Statistics\n")

    click.echo("Observation Logs:")
    click.echo(f"  Total entries: {log_stats.get('total_entries', 0)}")
    click.echo(f"  Total sessions: {log_stats.get('total_sessions', 0)}")

    if log_stats.get('date_range'):
        click.echo(f"  Date range: {log_stats['date_range']['start'][:10]} to {log_stats['date_range']['end'][:10]}")

    click.echo(f"\nPatterns:")
    click.echo(f"  Total patterns: {pattern_stats.get('total_patterns', 0)}")
    click.echo(f"  Skill candidates: {pattern_stats.get('skill_candidates', 0)}")

    if pattern_stats.get('avg_support'):
        click.echo(f"  Avg support: {pattern_stats['avg_support']:.1f}")
        click.echo(f"  Avg confidence: {pattern_stats['avg_confidence']:.1%}")

    click.echo(f"\nSkills:")
    click.echo(f"  Total skills: {skill_stats.get('total_skills', 0)}")

    if skill_stats.get('by_status'):
        click.echo(f"  By status:")
        for status, count in skill_stats['by_status'].items():
            click.echo(f"    {status}: {count}")


if __name__ == '__main__':
    esass()
