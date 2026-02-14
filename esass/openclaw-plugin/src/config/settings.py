"""
Configuration Management for ESASS × OpenClaw Integration
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class ESASSConfig:
    """ESASS observation and analysis settings"""
    enabled: bool = True
    data_dir: str = "./data/esass"
    sample_rate: float = 1.0

    # Probes
    tool_probe_enabled: bool = True
    reasoning_probe_enabled: bool = True
    decision_probe_enabled: bool = True

    # Pipeline
    buffer_size: int = 100
    flush_interval_seconds: float = 5.0


@dataclass
class OpenClawConfig:
    """OpenClaw integration settings"""
    workspace_dir: str = str(Path.home() / ".openclaw")
    skills_dir: str = "skills"
    config_file: str = "openclaw.json"

    # Gateway
    gateway_url: str = "ws://127.0.0.1:18789"
    gateway_token: Optional[str] = None


@dataclass
class ClawHubConfig:
    """ClawHub registry settings"""
    registry_url: str = "https://clawhub.com"
    token: Optional[str] = None

    # Publishing
    auto_bump: str = "patch"
    default_tags: list = field(default_factory=lambda: ["latest", "esass-generated"])


@dataclass
class LoopSettings:
    """Recursive loop timing and thresholds"""
    # Timing
    observation_window_hours: int = 24
    cycle_interval_hours: int = 6

    # Detection thresholds
    min_events_for_detection: int = 100
    min_support: int = 10
    min_confidence: float = 0.8
    min_stability_days: int = 7

    # Generation
    auto_generate: bool = True
    max_skills_per_cycle: int = 5

    # Publishing
    auto_publish: bool = True
    publish_confidence_threshold: float = 0.85
    publish_support_threshold: int = 15

    # Safety
    require_human_approval: bool = False
    rate_limit_skills_per_day: int = 10


@dataclass
class IntegrationConfig:
    """Complete integration configuration"""
    esass: ESASSConfig = field(default_factory=ESASSConfig)
    openclaw: OpenClawConfig = field(default_factory=OpenClawConfig)
    clawhub: ClawHubConfig = field(default_factory=ClawHubConfig)
    loop: LoopSettings = field(default_factory=LoopSettings)

    @classmethod
    def from_env(cls) -> "IntegrationConfig":
        """Load configuration from environment variables"""
        return cls(
            esass=ESASSConfig(
                enabled=os.environ.get("ESASS_ENABLED", "true").lower() == "true",
                data_dir=os.environ.get("ESASS_DATA_DIR", "./data/esass"),
                sample_rate=float(os.environ.get("ESASS_SAMPLE_RATE", "1.0")),
            ),
            openclaw=OpenClawConfig(
                workspace_dir=os.environ.get(
                    "OPENCLAW_WORKSPACE",
                    str(Path.home() / ".openclaw")
                ),
                gateway_url=os.environ.get(
                    "OPENCLAW_GATEWAY_URL",
                    "ws://127.0.0.1:18789"
                ),
                gateway_token=os.environ.get("OPENCLAW_GATEWAY_TOKEN"),
            ),
            clawhub=ClawHubConfig(
                registry_url=os.environ.get("CLAWHUB_REGISTRY", "https://clawhub.com"),
                token=os.environ.get("CLAWHUB_TOKEN"),
            ),
            loop=LoopSettings(
                observation_window_hours=int(
                    os.environ.get("LOOP_OBSERVATION_HOURS", "24")
                ),
                cycle_interval_hours=int(
                    os.environ.get("LOOP_CYCLE_HOURS", "6")
                ),
                auto_publish=os.environ.get(
                    "LOOP_AUTO_PUBLISH", "true"
                ).lower() == "true",
            )
        )


# Global configuration instance
_config: Optional[IntegrationConfig] = None


def get_config() -> IntegrationConfig:
    """Get global configuration"""
    global _config
    if _config is None:
        _config = IntegrationConfig.from_env()
    return _config


def set_config(config: IntegrationConfig) -> None:
    """Set global configuration"""
    global _config
    _config = config
