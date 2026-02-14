"""
Centralized configuration for ESASS.

Config loading chain:
    $ESASS_CONFIG env var -> .esass/config.yaml (project) -> ~/.esass/config.yaml (global) -> defaults

Environment variable overrides:
    ESASS_DATA_DIR   - Data storage directory
    ESASS_CONFIG     - Path to config file
    ESASS_LOG_LEVEL  - Logging level
"""

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import yaml


# --- Subsystem configs (from esass_prototype/config.py) ---


@dataclass
class ObservationConfig:
    mode: str = "simulation"
    simulation_sessions_per_day: int = 20
    simulation_days: int = 14
    enabled: bool = False


@dataclass
class StorageConfig:
    data_dir: str = ""
    log_format: str = "jsonl"
    compression: bool = False
    max_log_age_days: int = 90

    def __post_init__(self):
        if not self.data_dir:
            self.data_dir = os.environ.get(
                "ESASS_DATA_DIR", str(Path.cwd() / ".esass" / "data")
            )


@dataclass
class PatternDetectionConfig:
    min_support: int = 10
    min_confidence: float = 0.8
    min_stability_days: int = 7
    max_gap_seconds: int = 300
    max_sequence_length: int = 5
    min_sequence_length: int = 2


@dataclass
class SkillGenerationConfig:
    auto_generate: bool = True
    require_validation: bool = True
    max_skills_per_pattern: int = 1


@dataclass
class ExportConfig:
    obsidian_vault: Optional[str] = None
    auto_export: bool = False
    export_format: str = "markdown"
    export_dir: str = "./obsidian_export"


@dataclass
class ProbeSystemConfig:
    enabled: bool = True
    data_dir: str = "./data"
    buffer_size: int = 100
    flush_interval: float = 5.0
    sample_rate: float = 1.0


# --- MCP / Local LLM config (from local-llm-mcp/config.py) ---


@dataclass
class LocalLLMConfig:
    enabled: bool = True
    debug: bool = False
    ollama_endpoint: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    ollama_timeout_seconds: int = 60
    hf_model: str = "mistralai/Mistral-7B-Instruct-v0.3"
    hf_token: str = ""
    hf_timeout_seconds: int = 60
    enable_pattern_analysis: bool = True
    max_local_tokens: int = 2048
    fallback_on_error: bool = True


# --- Main config ---


@dataclass
class ESASSConfig:
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
    local_llm: LocalLLMConfig = field(default_factory=LocalLLMConfig)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ESASSConfig":
        return cls(
            observation=ObservationConfig(**data.get("observation", {})),
            storage=StorageConfig(**data.get("storage", {})),
            pattern_detection=PatternDetectionConfig(
                **data.get("pattern_detection", {})
            ),
            skill_generation=SkillGenerationConfig(
                **data.get("skill_generation", {})
            ),
            export=ExportConfig(**data.get("export", {})),
            probes=ProbeSystemConfig(**data.get("probes", {})),
            local_llm=LocalLLMConfig(**data.get("local_llm", {})),
        )


def _find_config_file() -> Optional[Path]:
    """Find config file using the auto-detection chain."""
    # 1. Explicit env var
    env_path = os.environ.get("ESASS_CONFIG")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    # 2. Project-local config
    project_config = Path.cwd() / ".esass" / "config.yaml"
    if project_config.exists():
        return project_config

    # 3. Global config
    global_config = Path.home() / ".esass" / "config.yaml"
    if global_config.exists():
        return global_config

    return None


_config: Optional[ESASSConfig] = None


def load_config(force_reload: bool = False) -> ESASSConfig:
    """Load config from file or return cached instance."""
    global _config
    if _config is not None and not force_reload:
        return _config

    config_file = _find_config_file()
    if config_file:
        with open(config_file, "r") as f:
            data = yaml.safe_load(f) or {}
        _config = ESASSConfig.from_dict(data)
    else:
        _config = ESASSConfig()

    # Apply env var overrides
    data_dir = os.environ.get("ESASS_DATA_DIR")
    if data_dir:
        _config.storage.data_dir = data_dir

    return _config


# Aliases for backward compatibility
def get_config() -> ESASSConfig:
    return load_config()


def get_data_dir(config: Optional[ESASSConfig] = None) -> Path:
    if config is None:
        config = get_config()
    return Path(config.storage.data_dir)


def get_export_dir(config: Optional[ESASSConfig] = None) -> Path:
    if config is None:
        config = get_config()
    return Path(config.export.export_dir)
