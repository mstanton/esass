
import pytest

from esass_prototype.analysis.pattern_detector import TemporalPatternDetector
from esass_prototype.export.obsidian import ObsidianExporter
from esass_prototype.genesis.template import SkillTemplateGenerator
from esass_prototype.observation.logger import ObservationLogger
from esass_prototype.observation.simulator import EventSimulator
from esass_prototype.storage.log_store import LogStore
from esass_prototype.storage.pattern_store import PatternStore
from esass_prototype.storage.skill_store import SkillStore


@pytest.fixture
def temp_data_dir(tmp_path):
    """Fixture to provide a temporary directory for data storage."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir

@pytest.fixture
def temp_export_dir(tmp_path):
    """Fixture to provide a temporary directory for exports."""
    export_dir = tmp_path / "obsidian_export"
    export_dir.mkdir()
    return export_dir

def test_full_pipeline_execution(temp_data_dir, temp_export_dir):
    """
    Test the complete ESASS pipeline from simulation to export.
    This replaces the ad-hoc test_pipeline.py script.
    """
    # 1. Generate Simulated Data
    simulator = EventSimulator(seed=42)
    entries = simulator.generate_multiple_sessions(count=10, days=3)
    assert len(entries) > 0, "Simulation should generate events"

    # 2. Log Events
    logger = ObservationLogger(temp_data_dir)
    logger.start_observation()
    logger.log_many(entries)
    
    stats = logger.get_stats()
    assert stats['total_events'] == len(entries)
    
    # 3. Detect Patterns
    log_store = LogStore(temp_data_dir)
    logs = log_store.load_all()
    assert len(logs) == len(entries)

    detector = TemporalPatternDetector(
        min_support=2,  # Lower threshold for smaller test set
        min_confidence=0.5,
        min_stability_days=0
    )
    patterns = detector.detect_patterns(logs)
    
    # Save patterns
    pattern_store = PatternStore(temp_data_dir)
    pattern_store.save_many(patterns)
    
    # 4. Generate Skills
    # 4. Generate Skills
    # candidate evaluation mocked for test simplicity
    
    # Treat all as candidates for this test to ensure flow works
    candidates = [p for p in patterns]
    
    generator = SkillTemplateGenerator()
    skills = generator.generate_from_patterns(candidates)
    
    skill_store = SkillStore(temp_data_dir)
    skill_store.save_many(skills)
    
    # 5. Export to Obsidian
    exporter = ObsidianExporter(temp_export_dir)
    exporter.export_all(logs, patterns, skills)
    
    assert (temp_export_dir / "ESASS" / "README.md").exists()
