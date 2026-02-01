"""
Configuration system for ESASS probes.

Manages probe settings with environment variable overrides.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ProbeConfig:
    """Base configuration for probes"""
    enabled: bool = True
    min_interval_seconds: float = 0.0


@dataclass
class ToolProbeConfig(ProbeConfig):
    """Configuration for tool call probe"""
    observe_tools: Optional[List[str]] = None
    sanitize_parameters: bool = True
    track_sequences: bool = True
    sequence_window_size: int = 5


@dataclass
class ReasoningProbeConfig(ProbeConfig):
    """Configuration for reasoning probe"""
    min_confidence: float = 0.0
    extract_evidence: bool = True
    detect_causal: bool = True


@dataclass
class DecisionProbeConfig(ProbeConfig):
    """Configuration for decision probe"""
    min_options: int = 1
    detect_tradeoffs: bool = True


@dataclass
class PipelineConfig:
    """Configuration for event pipeline"""
    buffer_size: int = 100
    flush_interval: float = 5.0
    max_queue_size: int = 10000
    sample_rate: float = 1.0
    use_priority: bool = False


@dataclass
class StorageConfig:
    """Configuration for event storage"""
    data_dir: Path = field(default_factory=lambda: Path('./data'))
    log_format: str = 'jsonl'
    retention_days: int = 90
    compress_old_logs: bool = True


@dataclass
class ESASSProbeSystemConfig:
    """
    Complete configuration for ESASS probe system.

    Supports environment variable overrides using ESASS_ prefix.
    """
    # Probe configurations
    tool_probe: ToolProbeConfig = field(default_factory=ToolProbeConfig)
    reasoning_probe: ReasoningProbeConfig = field(default_factory=ReasoningProbeConfig)
    decision_probe: DecisionProbeConfig = field(default_factory=DecisionProbeConfig)

    # Pipeline configuration
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)

    # Storage configuration
    storage: StorageConfig = field(default_factory=StorageConfig)

    # Global settings
    enabled: bool = True
    auto_register_probes: bool = True
    log_level: str = 'INFO'

    @classmethod
    def from_env(cls) -> 'ESASSProbeSystemConfig':
        """
        Create configuration from environment variables.

        Environment variables:
            ESASS_ENABLED: Enable/disable entire system
            ESASS_DATA_DIR: Data directory path
            ESASS_BUFFER_SIZE: Pipeline buffer size
            ESASS_FLUSH_INTERVAL: Flush interval in seconds
            ESASS_LOG_LEVEL: Logging level
            ESASS_TOOL_PROBE_ENABLED: Enable tool probe
            ESASS_REASONING_PROBE_ENABLED: Enable reasoning probe
            ESASS_DECISION_PROBE_ENABLED: Enable decision probe
            ESASS_MIN_CONFIDENCE: Minimum confidence for reasoning events
            ESASS_SAMPLE_RATE: Event sampling rate (0.0-1.0)

        Returns:
            Configuration with environment overrides
        """
        config = cls()

        # Global settings
        config.enabled = cls._get_bool_env('ESASS_ENABLED', config.enabled)
        config.log_level = os.getenv('ESASS_LOG_LEVEL', config.log_level)
        config.auto_register_probes = cls._get_bool_env(
            'ESASS_AUTO_REGISTER', config.auto_register_probes
        )

        # Storage
        data_dir = os.getenv('ESASS_DATA_DIR')
        if data_dir:
            config.storage.data_dir = Path(data_dir)

        config.storage.retention_days = cls._get_int_env(
            'ESASS_RETENTION_DAYS', config.storage.retention_days
        )

        # Pipeline
        config.pipeline.buffer_size = cls._get_int_env(
            'ESASS_BUFFER_SIZE', config.pipeline.buffer_size
        )
        config.pipeline.flush_interval = cls._get_float_env(
            'ESASS_FLUSH_INTERVAL', config.pipeline.flush_interval
        )
        config.pipeline.max_queue_size = cls._get_int_env(
            'ESASS_MAX_QUEUE_SIZE', config.pipeline.max_queue_size
        )
        config.pipeline.sample_rate = cls._get_float_env(
            'ESASS_SAMPLE_RATE', config.pipeline.sample_rate
        )
        config.pipeline.use_priority = cls._get_bool_env(
            'ESASS_USE_PRIORITY', config.pipeline.use_priority
        )

        # Tool probe
        config.tool_probe.enabled = cls._get_bool_env(
            'ESASS_TOOL_PROBE_ENABLED', config.tool_probe.enabled
        )
        config.tool_probe.track_sequences = cls._get_bool_env(
            'ESASS_TRACK_SEQUENCES', config.tool_probe.track_sequences
        )

        # Reasoning probe
        config.reasoning_probe.enabled = cls._get_bool_env(
            'ESASS_REASONING_PROBE_ENABLED', config.reasoning_probe.enabled
        )
        config.reasoning_probe.min_confidence = cls._get_float_env(
            'ESASS_MIN_CONFIDENCE', config.reasoning_probe.min_confidence
        )
        config.reasoning_probe.detect_causal = cls._get_bool_env(
            'ESASS_DETECT_CAUSAL', config.reasoning_probe.detect_causal
        )

        # Decision probe
        config.decision_probe.enabled = cls._get_bool_env(
            'ESASS_DECISION_PROBE_ENABLED', config.decision_probe.enabled
        )
        config.decision_probe.min_options = cls._get_int_env(
            'ESASS_MIN_OPTIONS', config.decision_probe.min_options
        )

        return config

    @staticmethod
    def _get_bool_env(key: str, default: bool) -> bool:
        """Get boolean from environment variable"""
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')

    @staticmethod
    def _get_int_env(key: str, default: int) -> int:
        """Get integer from environment variable"""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    @staticmethod
    def _get_float_env(key: str, default: float) -> float:
        """Get float from environment variable"""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def to_dict(self) -> dict:
        """Convert configuration to dictionary"""
        from dataclasses import asdict
        return asdict(self)


def configure_logging(config: ESASSProbeSystemConfig) -> None:
    """
    Configure logging based on config.

    Args:
        config: Probe system configuration
    """
    import logging

    level = getattr(logging, config.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Set specific logger levels
    logging.getLogger('esass.probes').setLevel(level)


def create_default_probes(config: ESASSProbeSystemConfig) -> List:
    """
    Create default probe instances from configuration.

    Args:
        config: Probe system configuration

    Returns:
        List of configured probe instances
    """
    from esass.probes.decision_probe import DecisionProbe, TradeoffAnalysisProbe
    from esass.probes.reasoning_probe import CausalReasoningProbe, ReasoningProbe
    from esass.probes.tool_probe import ToolCallProbe, ToolSequenceDetector

    probes = []

    # Tool probe
    if config.tool_probe.enabled:
        if config.tool_probe.track_sequences:
            probe = ToolSequenceDetector(
                enabled=config.tool_probe.enabled,
                sequence_window_size=config.tool_probe.sequence_window_size
            )
        else:
            probe = ToolCallProbe(
                enabled=config.tool_probe.enabled,
                observe_tools=config.tool_probe.observe_tools
            )
        probes.append(probe)

    # Reasoning probe
    if config.reasoning_probe.enabled:
        if config.reasoning_probe.detect_causal:
            probe = CausalReasoningProbe(
                enabled=config.reasoning_probe.enabled,
                min_confidence=config.reasoning_probe.min_confidence,
                extract_evidence=config.reasoning_probe.extract_evidence
            )
        else:
            probe = ReasoningProbe(
                enabled=config.reasoning_probe.enabled,
                min_confidence=config.reasoning_probe.min_confidence,
                extract_evidence=config.reasoning_probe.extract_evidence
            )
        probes.append(probe)

    # Decision probe
    if config.decision_probe.enabled:
        if config.decision_probe.detect_tradeoffs:
            probe = TradeoffAnalysisProbe(
                enabled=config.decision_probe.enabled,
                min_options=config.decision_probe.min_options
            )
        else:
            probe = DecisionProbe(
                enabled=config.decision_probe.enabled,
                min_options=config.decision_probe.min_options
            )
        probes.append(probe)

    return probes


def create_pipeline(config: ESASSProbeSystemConfig):
    """
    Create event pipeline from configuration.

    Args:
        config: Probe system configuration

    Returns:
        Configured EventPipeline instance
    """
    from esass.probes.pipeline import (
        AsyncEventPipeline,
        EventPipeline,
        PriorityEventPipeline,
    )

    if config.pipeline.use_priority:
        pipeline_class = PriorityEventPipeline
    elif config.pipeline.sample_rate < 1.0:
        pipeline_class = AsyncEventPipeline
    else:
        pipeline_class = EventPipeline

    return pipeline_class(
        data_dir=config.storage.data_dir,
        buffer_size=config.pipeline.buffer_size,
        flush_interval=config.pipeline.flush_interval,
        max_queue_size=config.pipeline.max_queue_size,
        **({'sample_rate': config.pipeline.sample_rate}
           if config.pipeline.sample_rate < 1.0 else {})
    )


def initialize_system(config: Optional[ESASSProbeSystemConfig] = None):
    """
    Initialize complete ESASS probe system.

    Args:
        config: Optional configuration (uses environment if None)

    Returns:
        Tuple of (registry, pipeline, config)
    """
    from esass.probes.registry import ProbeRegistry

    # Load or create config
    if config is None:
        config = ESASSProbeSystemConfig.from_env()

    if not config.enabled:
        import logging
        logging.info("ESASS probe system disabled by configuration")
        return None, None, config

    # Configure logging
    configure_logging(config)

    # Create pipeline
    pipeline = create_pipeline(config)

    # Create registry
    registry = ProbeRegistry(event_pipeline=pipeline)

    # Create and register probes
    if config.auto_register_probes:
        probes = create_default_probes(config)
        registry.register_all(probes)

    registry.start()

    import logging
    logging.info(f"ESASS probe system initialized with {len(registry.probes)} probes")

    return registry, pipeline, config
