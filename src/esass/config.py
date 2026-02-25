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
from typing import Dict, List, Optional


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


@dataclass
class SemanticExtractionConfig:
    tool_categories: Dict[str, str] = field(
        default_factory=lambda: {
            "Read": "file_read",
            "Write": "file_write",
            "Edit": "file_edit",
            "Glob": "file_search",
            "Grep": "content_search",
            "Bash": "command",
            "Task": "delegation",
            "WebFetch": "web",
            "WebSearch": "web",
            "AskUserQuestion": "interaction",
        }
    )
    file_type_semantics: Dict[str, str] = field(
        default_factory=lambda: {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".json": "config",
            ".yaml": "config",
            ".yml": "config",
            ".md": "docs",
            ".txt": "text",
            ".sh": "script",
            ".ps1": "script",
        }
    )
    command_patterns: Dict[str, str] = field(
        default_factory=lambda: {
            r"git\s+status": "git_status",
            r"git\s+add": "git_add",
            r"git\s+commit": "git_commit",
            r"git\s+push": "git_push",
            r"git\s+pull": "git_pull",
            r"git\s+diff": "git_diff",
            r"git\s+log": "git_log",
            r"pytest|python\s+-m\s+pytest": "test_run",
            r"npm\s+test|yarn\s+test": "test_run",
            r"pip\s+install": "dependency",
            r"npm\s+install|yarn\s+add": "dependency",
            r"python|node|ruby": "execution",
            r"docker": "container",
            r"kubectl": "kubernetes",
        }
    )
    noise_tags: List[str] = field(
        default_factory=lambda: [
            "boundary_action",
            "hook_error",
            "hook_success",
            "unknown",
            "none",
            "null",
            "",
        ]
    )


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
    semantic_extraction: SemanticExtractionConfig = field(
        default_factory=SemanticExtractionConfig
    )

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
            skill_generation=SkillGenerationConfig(**data.get("skill_generation", {})),
            export=ExportConfig(**data.get("export", {})),
            probes=ProbeSystemConfig(**data.get("probes", {})),
            local_llm=LocalLLMConfig(**data.get("local_llm", {})),
            semantic_extraction=SemanticExtractionConfig(
                **data.get("semantic_extraction", {})
            ),
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


def get_global_data_dir() -> Path:
    """Return the global data directory (~/.esass/data/)."""
    return Path.home() / ".esass" / "data"


_GLOBAL_CONFIG_DEFAULTS = {
    "observation": {"enabled": True, "mode": "live"},
    "storage": {
        "log_format": "jsonl",
        "max_log_age_days": 90,
    },
    "pattern_detection": {
        "min_support": 10,
        "min_confidence": 0.8,
        "min_stability_days": 7,
    },
    "local_llm": {
        "enabled": True,
        "ollama_model": "gemma3:4b",
        "hf_model": "mistralai/Mistral-7B-Instruct-v0.3",
        "hf_token": "",
    },
    "mcp_env": {
        "OLLAMA_MODEL": "gemma3:4b",
        "HF_TOKEN": "",
    },
}


def ensure_global_config() -> Path:
    """Create ~/.esass/config.yaml with sensible defaults if it doesn't exist.

    Returns the path to the global config file.
    """
    global_dir = Path.home() / ".esass"
    global_dir.mkdir(parents=True, exist_ok=True)

    config_file = global_dir / "config.yaml"
    if config_file.exists():
        return config_file

    # Create global data dirs
    data_dir = global_dir / "data"
    for subdir in ["logs", "state", "patterns", "skills", "mcp"]:
        (data_dir / subdir).mkdir(parents=True, exist_ok=True)

    with open(config_file, "w") as f:
        yaml.dump(_GLOBAL_CONFIG_DEFAULTS, f, default_flow_style=False, sort_keys=False)

    return config_file


def load_global_mcp_env() -> dict:
    """Load MCP environment variables from the global config.

    Returns a dict of env var name -> value suitable for .mcp.json.
    """
    global_config = Path.home() / ".esass" / "config.yaml"
    mcp_env = dict(_GLOBAL_CONFIG_DEFAULTS.get("mcp_env", {}))

    if global_config.exists():
        try:
            with open(global_config, "r") as f:
                data = yaml.safe_load(f) or {}
            stored = data.get("mcp_env", {})
            if stored:
                mcp_env.update(stored)
            # Also pull from local_llm section
            llm = data.get("local_llm", {})
            if llm.get("ollama_model"):
                mcp_env.setdefault("OLLAMA_MODEL", llm["ollama_model"])
            if llm.get("hf_token"):
                mcp_env.setdefault("HF_TOKEN", llm["hf_token"])
        except Exception:
            pass

    # Environment variables take precedence
    for key in ["OLLAMA_MODEL", "HF_TOKEN", "OLLAMA_ENDPOINT"]:
        env_val = os.environ.get(key)
        if env_val:
            mcp_env[key] = env_val

    # Remove empty values
    return {k: v for k, v in mcp_env.items() if v}
