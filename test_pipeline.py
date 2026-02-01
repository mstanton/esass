"""
Test script for ESASS prototype pipeline.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from esass_prototype.config import ESASSConfig
from esass_prototype.observation.simulator import EventSimulator
from esass_prototype.observation.logger import ObservationLogger
from esass_prototype.storage.log_store import LogStore
from esass_prototype.storage.pattern_store import PatternStore
from esass_prototype.storage.skill_store import SkillStore
from esass_prototype.analysis.pattern_detector import TemporalPatternDetector
from esass_prototype.genesis.candidate import SkillCandidacyEvaluator
from esass_prototype.genesis.template import SkillTemplateGenerator
from esass_prototype.export.obsidian import ObsidianExporter


def test_pipeline():
    """Test full ESASS pipeline"""

    print("=" * 60)
    print("ESASS PROTOTYPE - FULL PIPELINE TEST")
    print("=" * 60)

    # Configuration
    data_dir = Path("./data")
    export_dir = Path("./obsidian_export")

    # Step 1: Generate simulated data
    print("\n[1/4] GENERATING SIMULATED DATA...")
    simulator = EventSimulator(seed=42)
    entries = simulator.generate_multiple_sessions(count=35, days=7)
    print(f"[OK] Generated {len(entries)} events across 35 sessions")

    # Step 2: Log entries
    print("\n[2/4] LOGGING EVENTS...")
    logger = ObservationLogger(data_dir)
    logger.start_observation()
    logger.log_many(entries)
    stats = logger.get_stats()
    print(f"[OK] Logged {stats['total_events']} events, {stats['total_sessions']} sessions")

    # Step 3: Detect patterns
    print("\n[3/4] DETECTING PATTERNS...")
    log_store = LogStore(data_dir)
    logs = log_store.load_all()

    detector = TemporalPatternDetector(
        min_support=10,
        min_confidence=0.8,
        min_stability_days=7
    )

    patterns = detector.detect_patterns(logs)
    print(f"[OK] Detected {len(patterns)} patterns")

    # Save patterns
    pattern_store = PatternStore(data_dir)
    pattern_store.save_many(patterns)

    # Show top patterns
    candidates = [p for p in patterns if p.skill_candidate]
    print(f"  - Skill candidates: {len(candidates)}")

    if patterns:
        print("\n  Top patterns:")
        for i, pattern in enumerate(patterns[:3], 1):
            status = "[OK]" if pattern.skill_candidate else "•"
            print(f"  {status} {i}. {pattern.description[:60]}...")
            print(f"     Support: {pattern.support}, Confidence: {pattern.confidence:.0%}, Stability: {pattern.stability_days}d")

    # Step 4: Generate skills
    print("\n[4/4] GENERATING SKILLS...")
    evaluator = SkillCandidacyEvaluator()
    candidates = evaluator.filter_candidates(patterns)

    if candidates:
        generator = SkillTemplateGenerator()
        skills = generator.generate_from_patterns(candidates)

        skill_store = SkillStore(data_dir)
        skill_store.save_many(skills)

        print(f"[OK] Generated {len(skills)} skills from {len(candidates)} candidate patterns")

        if skills:
            print("\n  Generated skills:")
            for i, skill in enumerate(skills[:3], 1):
                print(f"  {i}. {skill.name}")
                caps = ', '.join(skill.capabilities[:3])
                print(f"     Capabilities: {caps}")
    else:
        print("⚠ No patterns met skill candidacy criteria")
        skills = []

    # Step 5: Export to Obsidian
    print("\n[5/5] EXPORTING TO OBSIDIAN...")
    exporter = ObsidianExporter(export_dir)
    exporter.export_all(logs, patterns, skills)
    print(f"[OK] Exported to {export_dir / 'ESASS'}")

    # Final summary
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE [SUCCESS]")
    print("=" * 60)
    print(f"Total events: {len(logs)}")
    print(f"Total patterns: {len(patterns)}")
    print(f"Skill candidates: {len([p for p in patterns if p.skill_candidate])}")
    print(f"Generated skills: {len(skills)}")
    print(f"\nResults exported to: {export_dir / 'ESASS' / 'README.md'}")
    print("=" * 60)


if __name__ == "__main__":
    test_pipeline()
