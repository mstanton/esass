"""
Configuration management for ESASS prototype.

Provides default configuration and loading/saving of user settings.
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
import json


@dataclass
class ObservationConfig:
    """Configuration for observation subsystem"""
    mode: str = "simulation"  # simulation | real | hybrid
    simulation_sessions_per_day: int = 20
    simulation_days: int = 14
    enabled: bool = False


@dataclass
class StorageConfig:
    """Configuration for storage layer"""
    data_dir: str = "./data"
    log_format: str = "jsonl"  # JSON Lines format
    compression: bool = False
    max_log_age_days: int = 90


@dataclass
class PatternDetectionConfig:
    """Configuration for pattern detection (§5.3, §6.2 of specification)"""
    min_support: int = 10              # Minimum instances for pattern
    min_confidence: float = 0.8        # Minimum reliability (0.0-1.0)
    min_stability_days: int = 7        # Minimum stability period
    max_gap_seconds: int = 300         # Max time between events in sequence
    max_sequence_length: int = 5       # Max events in a sequence
    min_sequence_length: int = 2       # Min events in a sequence


@dataclass
class SkillGenerationConfig:
    """Configuration for skill generation"""
    auto_generate: bool = True
    require_validation: bool = True
    max_skills_per_pattern: int = 1


@dataclass
class ExportConfig:
    """Configuration for export subsystem"""
    obsidian_vault: Optional[str] = None
    auto_export: bool = False
    export_format: str = "markdown"
    export_dir: str = "./obsidian_export"


@dataclass
class ESASSConfig:
    """
    Main configuration for ESASS prototype.

    Default settings align with specification requirements.
    """
    observation: ObservationConfig = field(default_factory=ObservationConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    pattern_detection: PatternDetectionConfig = field(default_factory=PatternDetectionConfig)
    skill_generation: SkillGenerationConfig = field(default_factory=SkillGenerationConfig)
    export: ExportConfig = field(default_factory=ExportConfig)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ESASSConfig':
        """Create from dictionary"""
        return cls(
            observation=ObservationConfig(**data.get('observation', {})),
            storage=StorageConfig(**data.get('storage', {})),
            pattern_detection=PatternDetectionConfig(**data.get('pattern_detection', {})),
            skill_generation=SkillGenerationConfig(**data.get('skill_generation', {})),
            export=ExportConfig(**data.get('export', {}))
        )

    def save(self, path: Path):
        """Save configuration to JSON file"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> 'ESASSConfig':
        """Load configuration from JSON file"""
        if not path.exists():
            # Return default config if file doesn't exist
            return cls()

        with open(path, 'r') as f:
            data = json.load(f)

        return cls.from_dict(data)

    @classmethod
    def get_default_path(cls) -> Path:
        """Get default configuration file path"""
        return Path("./config/esass_config.json")

    @classmethod
    def load_or_create_default(cls, path: Optional[Path] = None) -> 'ESASSConfig':
        """Load config from path, or create default if it doesn't exist"""
        if path is None:
            path = cls.get_default_path()

        if path.exists():
            return cls.load(path)
        else:
            # Create default config
            config = cls()
            config.save(path)
            return config


# Convenience functions

def get_config(config_path: Optional[Path] = None) -> ESASSConfig:
    """Get configuration (loads or creates default)"""
    return ESASSConfig.load_or_create_default(config_path)


def save_config(config: ESASSConfig, config_path: Optional[Path] = None):
    """Save configuration"""
    if config_path is None:
        config_path = ESASSConfig.get_default_path()
    config.save(config_path)


def get_data_dir(config: Optional[ESASSConfig] = None) -> Path:
    """Get data directory path"""
    if config is None:
        config = get_config()
    return Path(config.storage.data_dir)


def get_export_dir(config: Optional[ESASSConfig] = None) -> Path:
    """Get export directory path"""
    if config is None:
        config = get_config()
    return Path(config.export.export_dir)
