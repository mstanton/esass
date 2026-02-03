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
class ErrorRecoveryProbeConfig(ProbeConfig):
    """Configuration for error recovery probe"""
    max_recovery_window_seconds: int = 300


@dataclass
class StrategyShiftProbeConfig(ProbeConfig):
    """Configuration for strategy shift probe"""
    max_strategy_duration_seconds: int = 600


@dataclass
class CalibrationProbeConfig(ProbeConfig):
    """Configuration for calibration probe"""
    verification_window_seconds: int = 300


@dataclass
class InsightProbeConfig(ProbeConfig):
    """Configuration for insight probe"""
    min_insight_confidence: float = 0.7


@dataclass
class ScopeExpansionProbeConfig(ProbeConfig):
    """Configuration for scope expansion probe"""
    pass  # Uses default ProbeConfig


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
    # Core probe configurations
    tool_probe: ToolProbeConfig = field(default_factory=ToolProbeConfig)
    reasoning_probe: ReasoningProbeConfig = field(default_factory=ReasoningProbeConfig)
    decision_probe: DecisionProbeConfig = field(default_factory=DecisionProbeConfig)

    # Enhanced probe configurations
    error_recovery_probe: ErrorRecoveryProbeConfig = field(default_factory=ErrorRecoveryProbeConfig)
    strategy_shift_probe: StrategyShiftProbeConfig = field(default_factory=StrategyShiftProbeConfig)
    calibration_probe: CalibrationProbeConfig = field(default_factory=CalibrationProbeConfig)
    insight_probe: InsightProbeConfig = field(default_factory=InsightProbeConfig)
    scope_expansion_probe: ScopeExpansionProbeConfig = field(default_factory=ScopeExpansionProbeConfig)

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

        # Error recovery probe
        config.error_recovery_probe.enabled = cls._get_bool_env(
            'ESASS_ERROR_RECOVERY_PROBE_ENABLED', config.error_recovery_probe.enabled
        )
        config.error_recovery_probe.max_recovery_window_seconds = cls._get_int_env(
            'ESASS_MAX_RECOVERY_WINDOW', config.error_recovery_probe.max_recovery_window_seconds
        )

        # Strategy shift probe
        config.strategy_shift_probe.enabled = cls._get_bool_env(
            'ESASS_STRATEGY_SHIFT_PROBE_ENABLED', config.strategy_shift_probe.enabled
        )
        config.strategy_shift_probe.max_strategy_duration_seconds = cls._get_int_env(
            'ESASS_MAX_STRATEGY_DURATION', config.strategy_shift_probe.max_strategy_duration_seconds
        )

        # Calibration probe
        config.calibration_probe.enabled = cls._get_bool_env(
            'ESASS_CALIBRATION_PROBE_ENABLED', config.calibration_probe.enabled
        )
        config.calibration_probe.verification_window_seconds = cls._get_int_env(
            'ESASS_VERIFICATION_WINDOW', config.calibration_probe.verification_window_seconds
        )

        # Insight probe
        config.insight_probe.enabled = cls._get_bool_env(
            'ESASS_INSIGHT_PROBE_ENABLED', config.insight_probe.enabled
        )
        config.insight_probe.min_insight_confidence = cls._get_float_env(
            'ESASS_MIN_INSIGHT_CONFIDENCE', config.insight_probe.min_insight_confidence
        )

        # Scope expansion probe
        config.scope_expansion_probe.enabled = cls._get_bool_env(
            'ESASS_SCOPE_EXPANSION_PROBE_ENABLED', config.scope_expansion_probe.enabled
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
    from esass.probes.error_recovery_probe import ErrorRecoveryProbe
    from esass.probes.strategy_shift_probe import StrategyShiftProbe
    from esass.probes.calibration_probe import CalibrationProbe
    from esass.probes.insight_probe import InsightProbe
    from esass.probes.scope_expansion_probe import ScopeExpansionProbe

    probes = []

    # Core probes

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

    # Enhanced probes

    # Error recovery probe
    if config.error_recovery_probe.enabled:
        probe = ErrorRecoveryProbe(
            enabled=config.error_recovery_probe.enabled,
            max_recovery_window_seconds=config.error_recovery_probe.max_recovery_window_seconds
        )
        probes.append(probe)

    # Strategy shift probe
    if config.strategy_shift_probe.enabled:
        probe = StrategyShiftProbe(
            enabled=config.strategy_shift_probe.enabled,
            max_strategy_duration_seconds=config.strategy_shift_probe.max_strategy_duration_seconds
        )
        probes.append(probe)

    # Calibration probe
    if config.calibration_probe.enabled:
        probe = CalibrationProbe(
            enabled=config.calibration_probe.enabled,
            verification_window_seconds=config.calibration_probe.verification_window_seconds
        )
        probes.append(probe)

    # Insight probe
    if config.insight_probe.enabled:
        probe = InsightProbe(
            enabled=config.insight_probe.enabled,
            min_insight_confidence=config.insight_probe.min_insight_confidence
        )
        probes.append(probe)

    # Scope expansion probe
    if config.scope_expansion_probe.enabled:
        probe = ScopeExpansionProbe(
            enabled=config.scope_expansion_probe.enabled
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
