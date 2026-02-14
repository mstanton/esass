"""
Configuration management for ESASS prototype.
"""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional
import os


@dataclass
class ObservationConfig:
    """Configuration for observation subsystem"""

    mode: str = "simulation"
    simulation_sessions_per_day: int = 20
    simulation_days: int = 14
    enabled: bool = False


@dataclass
class StorageConfig:
    """Configuration for storage layer"""

    data_dir: str = field(
        default_factory=lambda: os.environ.get(
            "ESASS_DATA_DIR", str(Path.home() / ".esass" / "data")
        )
    )
    log_format: str = "jsonl"
    compression: bool = False
    max_log_age_days: int = 90


@dataclass
class PatternDetectionConfig:
    """Configuration for pattern detection"""

    min_support: int = 10
    min_confidence: float = 0.8
    min_stability_days: int = 7
    max_gap_seconds: int = 300
    max_sequence_length: int = 5
    min_sequence_length: int = 2


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
class ProbeSystemConfig:
    """Configuration bridge to esass core probe system (esass.probes.config)."""

    enabled: bool = True
    data_dir: str = "./data"
    buffer_size: int = 100
    flush_interval: float = 5.0
    sample_rate: float = 1.0


@dataclass
class ESASSConfig:
    """Main configuration for ESASS prototype"""

    observation: ObservationConfig = field(default_factory=ObservationConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    pattern_detection: PatternDetectionConfig = field(
        default_factory=PatternDetectionConfig
    )
    skill_generation: SkillGenerationConfig = field(
        default_factory=SkillGenerationConfig
    )
    export: ExportConfig = field(default_factory=ExportConfig)
    probes: ProbeSystemConfig = field(default_factory=ProbeSystemConfig)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ESASSConfig":
        """Create from dictionary"""
        return cls(
            observation=ObservationConfig(**data.get("observation", {})),
            storage=StorageConfig(**data.get("storage", {})),
            pattern_detection=PatternDetectionConfig(
                **data.get("pattern_detection", {})
            ),
            skill_generation=SkillGenerationConfig(**data.get("skill_generation", {})),
            export=ExportConfig(**data.get("export", {})),
            probes=ProbeSystemConfig(**data.get("probes", {})),
        )


def get_config() -> ESASSConfig:
    """Get default configuration"""
    return ESASSConfig()


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
