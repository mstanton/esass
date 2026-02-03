# Changelog

All notable changes to the ESASS project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Documentation
- **Added comprehensive test documentation**: Created [TEST_RESULTS.md](TEST_RESULTS.md) with detailed analysis of integration test session (57 events captured, 8 probes active, complete event breakdowns)
- **Enhanced probe documentation**: Updated README.md, CLAUDE.md, and QUICKSTART.md with latest test results and performance metrics
- **Added event analysis**: Created [data_example/EVENT_SUMMARY.md](data_example/EVENT_SUMMARY.md) with event timeline, causality graphs, and pattern detection opportunities
- **Cross-references**: Added links between documentation files for better navigation

## [0.2.1] - 2026-02-03

### Fixed
- **Test Suite**: Fixed `test_create_default_probes` configuration issue where all 8 probe types were being enabled by default instead of the 2 specified in the test. Added explicit disabling of enhanced probes (error_recovery, strategy_shift, calibration, insight, scope_expansion) to match test expectations.
- **Configuration**: Fixed `DeprecationWarning` for invalid escape sequence in `esass_prototype/config.py` by using raw string literal for Windows path (line 53: `export_dir`).
- **Storage Layer**: Fixed timestamp handling issues in log storage:
  - Added `_parse_timestamp()` helper method in `LogStore` to handle both `datetime` objects and ISO format strings, resolving `TypeError: fromisoformat: argument must be str` error.
  - Updated `LogEntry.to_dict()` to serialize `datetime` objects to ISO format strings before JSON serialization, resolving `TypeError: Object of type datetime is not JSON serializable` error.

### Verified
- **All tests passing**: Complete test suite now passes with 41/41 tests successful
  - 27 probe system tests (esass/probes/)
  - 13 open-code-ai integration tests
  - 1 end-to-end pipeline test
- **Integration example working**: Claude Code integration example (`examples/claude_code_integration.py`) successfully runs and captures events:
  - 7 events received
  - 12 log entries generated
  - 8 probes active (ToolSequence, CausalReasoning, Tradeoff, ErrorRecovery, StrategyShift, Calibration, Insight, ScopeExpansion)
  - Events successfully written to `data_example/logs/*.jsonl` files

### Technical Details

#### Timestamp Fix
The issue occurred because `ProbeContext.timestamp` is a `datetime` object (set in `__post_init__`), but the storage layer expected ISO format strings. The fix handles both formats seamlessly:

```python
# In log_store.py
def _parse_timestamp(self, timestamp) -> datetime:
    """Parse timestamp from string or datetime object"""
    if isinstance(timestamp, datetime):
        return timestamp
    elif isinstance(timestamp, str):
        return datetime.fromisoformat(timestamp)
    else:
        raise ValueError(f"Invalid timestamp type: {type(timestamp)}")

# In models.py LogEntry.to_dict()
def to_dict(self) -> dict:
    """Convert to dictionary for JSON serialization"""
    data = asdict(self)
    # Ensure timestamp is a string for JSON serialization
    if isinstance(data['timestamp'], datetime):
        data['timestamp'] = data['timestamp'].isoformat()
    return data
```

## [0.2.0] - 2026-02-02

### Added
- **OpenClaw × ClawHub Integration**: Complete recursive learning loop implementation (1873 lines)
  - OpenClaw event bridge for capturing agent execution
  - Skill formatter for converting ESASS manifests to SKILL.md format
  - ClawHub client for publishing skills to registry
  - Recursive loop controller for orchestrating the complete learning cycle
- **Enhanced Probe System**: Added 5 new specialized probes
  - `ErrorRecoveryProbe`: Tracks error recovery patterns and strategies
  - `StrategyShiftProbe`: Captures pivot points and approach changes
  - `CalibrationProbe`: Compares predictions vs outcomes for self-improvement
  - `InsightProbe`: Detects "aha moments" and breakthroughs
  - `ScopeExpansionProbe`: Identifies complexity surprises and scope creep
- **open-code-ai Integration**: Complete integration example for open-code-ai platform
  - Action mapping (file_read → Read, file_edit → Edit, command_run → Bash)
  - 13 comprehensive integration tests
  - Example integration script with statistics

### Changed
- **Probe Count**: System now supports 8 specialized probes (previously 3)
- **Test Coverage**: Expanded test suite to 41 tests total

## [0.1.0] - 2026-01-28

### Added
- **Initial Release**: Production-ready probe system for real-time event capture
- **Core Probes**:
  - `ToolCallProbe` / `ToolSequenceDetector`: Captures tool invocations and sequences
  - `ReasoningProbe` / `CausalReasoningProbe`: Extracts hypotheses and causal patterns
  - `DecisionProbe` / `TradeoffAnalysisProbe`: Tracks decision points and tradeoffs
- **Infrastructure**:
  - `ProbeRegistry`: Event routing and probe coordination
  - `EventPipeline`: Buffered async event processing
  - Configuration system with environment variable support
- **Documentation**:
  - Complete probe system README (`esass/probes/README.md`)
  - Integration plan (26-week roadmap)
  - Implementation summary
  - Claude Code integration example
- **Test Suite**: 27 probe system tests with ~85% coverage
- **Performance**: All benchmarks exceeded
  - Event capture: ~3ms (target <10ms)
  - Throughput: ~1500/sec (target 1000/sec)
  - Memory: ~60MB (target <100MB)
  - CPU: ~2% (target <5%)

### Prototype Features
- Event observation simulation (5 common scenarios)
- Pattern detection using simplified PrefixSpan algorithm
- Skill generation from validated patterns
- Obsidian export for knowledge base integration
- CLI interface with multiple commands
- Complete learning loop demonstration

## [0.0.1] - 2026-01-25

### Added
- **Initial Prototype**: Proof of concept for ESASS learning loop
- **Core Models**: LogEntry, PatternDefinition, SkillManifest
- **Storage Layer**: File-based JSONL and JSON storage
- **Event Simulator**: Synthetic event generation for testing
- **Pattern Detection**: Temporal pattern mining
- **Skill Generation**: Template-based skill creation
- **Full Specification**: 1271-line technical specification document
- **Architecture Documentation**: Evolution system design

---

## Upgrade Notes

### Migrating to 0.2.1

If you're upgrading from an earlier version:

1. **No breaking changes** - All APIs remain compatible
2. **Run tests** to verify your installation: `pytest tests/ -v`
3. **Try the integration example**: `python -m examples.claude_code_integration`
4. **Check configuration**: Enhanced probes are enabled by default, configure via environment variables if needed

### Configuration

To disable specific probes:

```bash
export ESASS_ERROR_RECOVERY_PROBE_ENABLED=false
export ESASS_STRATEGY_SHIFT_PROBE_ENABLED=false
export ESASS_CALIBRATION_PROBE_ENABLED=false
export ESASS_INSIGHT_PROBE_ENABLED=false
export ESASS_SCOPE_EXPANSION_PROBE_ENABLED=false
```

---

## Links

- **Repository**: [github.com/mstanton/esass](https://github.com/mstanton/esass)
- **Documentation**: See README.md, QUICKSTART.md, and docs in esass/probes/
- **Issues**: Report bugs and request features via GitHub Issues
