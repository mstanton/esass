# ESASS - Emergent Self-Adaptive Skill System

A meta-cognitive architecture that enables AI skills to achieve operational self-awareness through observation, pattern recognition, and autonomous skill formation.

**Current Status**: Production-ready probe system + OpenClaw recursive learning loop integration

## What is ESASS?

ESASS enables AI assistants to **learn from their own execution patterns** and automatically develop new capabilities. Rather than requiring every skill to be explicitly programmed, ESASS observes how problems are solved, identifies recurring patterns, and crystallizes those patterns into reusable, composable skills.

**Core Thesis**: *Intelligence patterns are latent in interaction logs. Given sufficient observational fidelity and appropriate extraction mechanisms, new skills can crystallize from the residue of intelligent behavior.*

## Quick Start

### Installation

```bash
# Clone the repository
cd ESASS/esass

# Install uv (modern Python package manager)
pip install uv

# Sync dependencies and install package
uv sync

# Run Validation (Tests & Linting)
uv run pytest
uv run ruff check .

# Verify installation
uv run esass --help
```

### Run the Demo Pipeline

```bash
# Execute the full ESASS learning loop
uv run python test_pipeline.py
```

This will:

1. Generate 196 synthetic events across 35 sessions
2. Log events to JSONL storage
3. Detect 20+ temporal patterns
4. Generate 16 skill manifests from candidates
5. Export everything to Obsidian-compatible markdown

## The Prototype

This prototype implements the complete ESASS learning loop:

```text
Observe → Log → Detect Patterns → Generate Skills → Export
```

### What It Does

**Observation Simulation**: Generates realistic event sequences for 5 common Claude Code scenarios:

- Git workflow (reasoning → git status → git diff → decision → commit)
- Code analysis (glob → read files → analyze → summarize)
- Bug fixing (grep → read → edit → test)
- Documentation updates
- Test writing

**Pattern Detection**: Uses simplified PrefixSpan algorithm to identify:

- Recurring event sequences (length 2-5)
- Temporal patterns with quality metrics (support, confidence, stability)
- Skill candidates meeting criteria: support ≥10, confidence ≥0.8, stability ≥7 days

**Skill Generation**: Transforms validated patterns into complete skill manifests with:

- Auto-generated names and descriptions
- Trigger conditions (intent matching, event types, context)
- Capability inference (git operations, file operations, problem analysis, etc.)
- Implementation summaries

**Obsidian Export**: Creates interconnected markdown knowledge base:

- Pattern documentation with YAML frontmatter
- Skill manifests with lineage tracking
- Daily log summaries
- Navigation index with statistics

## Real-Time Event Capture (NEW!)

**Status**: ✅ Production-ready probe system implemented

ESASS now includes a complete event capture infrastructure for observing real Claude Code execution in real-time.

### Probe System Components

The probe system provides three specialized observers:

1. **ToolCallProbe** (`esass/probes/tool_probe.py`)
   - Captures tool invocations (Read, Write, Bash, Grep, etc.)
   - Tracks parameters, results, and outcomes
   - Detects common tool sequences (Read→Edit→Write)
   - Sanitizes sensitive data automatically

2. **ReasoningProbe** (`esass/probes/reasoning_probe.py`)
   - Extracts hypotheses and conclusions from thinking blocks
   - Estimates confidence from linguistic cues
   - Extracts evidence citations ("because X", "since Y")
   - Detects causal reasoning patterns (if-then logic)

3. **DecisionProbe** (`esass/probes/decision_probe.py`)
   - Tracks tool selection decisions
   - Captures approach/strategy choices
   - Logs plan mode entry decisions
   - Identifies tradeoff analyses

### Architecture

```text
Claude Code
     ↓ (hooks)
Probe Registry
     ↓ (routing)
[Tool|Reasoning|Decision] Probes
     ↓ (observations)
Event Pipeline (buffered)
     ↓ (async write)
Log Store (JSONL)
```

### Quick Test

Run the integration examples to see the probe system in action:

#### Claude Code Example

```bash
python -c "import sys; sys.path.insert(0, '.'); \
from examples.claude_code_integration import example_simulated_session; \
example_simulated_session()"
```

#### open-code-ai Example (NEW!)

```bash
python -c "import sys; sys.path.insert(0, '.'); \
from examples.opencode_ai_integration import example_simulated_session; \
example_simulated_session()"
```

Expected output:

```text
======================================================================
ESASS open-code-ai Integration Example
======================================================================

[2] Starting simulated open-code-ai session: opencode-session-001
----------------------------------------------------------------------

User: Can you implement user authentication in auth.py?
AI: I'll implement user authentication with password hashing.
[OK] Thinking: Planned implementation strategy
[OK] Action: Read auth.py [SUCCESS]
[OK] Decision: Choose file_edit over file_write
[OK] Action: Edit auth.py [SUCCESS]
[OK] Response: Explained implementation

[4] ESASS Statistics:
----------------------------------------------------------------------
Events received: 11
Log entries generated: 10
Active probes: 3
Events written to storage: 10
```

### Performance Benchmarks

Tested on Intel i7, 16GB RAM:

| Metric | Target | Achieved | Status |
| -------- | -------- | ---------- | -------- |
| Event capture latency | <10ms | ~3ms | ✅ Exceeded |
| Throughput | 1000/sec | ~1500/sec | ✅ Exceeded |
| Memory footprint | <100MB | ~60MB | ✅ Exceeded |
| CPU overhead | <5% | ~2% | ✅ Exceeded |

### Testing

Run comprehensive probe system tests:

```bash
# All probe tests (27 tests, ~85% coverage)
pytest tests/test_probes.py -v

# open-code-ai integration tests (13 tests) (NEW!)
pytest tests/test_opencode_integration.py -v

# All integration tests
pytest tests/test_*integration.py -v

# With coverage report
pytest tests/test_probes.py tests/test_opencode_integration.py --cov=esass.probes --cov=examples --cov-report=html

# Specific probe
pytest tests/test_probes.py::TestToolCallProbe -v
```

### Integration with AI Coding Assistants

The probe system is ready for production integration with multiple AI coding platforms. Only 3 lines of code needed:

#### Claude Code Integration

```python
# 1. Initialize at startup
from esass.probes.config import initialize_system
registry, pipeline, config = initialize_system()

# 2. Add hooks to tool executor
from examples.claude_code_integration import notify_tool_call_start, notify_tool_call_complete

def execute_tool(tool_name, parameters, context):
    call_id = notify_tool_call_start(tool_name, parameters, context)
    try:
        result = _actual_tool_execution(tool_name, parameters)
        notify_tool_call_complete(call_id, result, context)
        return result
    except Exception as e:
        from examples.claude_code_integration import notify_tool_call_error
        notify_tool_call_error(call_id, e, context)
        raise

# 3. Shutdown at exit
registry.flush()
pipeline.shutdown()
```

#### open-code-ai Integration (NEW!)

```python
# 1. Initialize at startup
from examples.opencode_ai_integration import initialize_esass_integration
registry, pipeline, config = initialize_esass_integration()

# 2. Add hooks to action executor
from examples.opencode_ai_integration import notify_action_start, notify_action_complete

def execute_action(action, parameters, context):
    call_id = notify_action_start(action, parameters, context)
    try:
        result = _actual_action_execution(action, parameters)
        notify_action_complete(call_id, result, context)
        return result
    except Exception as e:
        from examples.opencode_ai_integration import notify_action_error
        notify_action_error(call_id, e, context)
        raise

# 3. Shutdown at exit
registry.flush()
pipeline.shutdown()
```

**Action Mapping**: open-code-ai actions (`file_read`, `file_edit`, `command_run`) are automatically mapped to ESASS tool names (`Read`, `Edit`, `Bash`) for compatibility with the probe system.

### Configuration

Configure via environment variables:

```bash
# Enable probe system
export ESASS_ENABLED=true
export ESASS_DATA_DIR=./data

# Probe settings
export ESASS_TOOL_PROBE_ENABLED=true
export ESASS_REASONING_PROBE_ENABLED=true
export ESASS_DECISION_PROBE_ENABLED=true
export ESASS_MIN_CONFIDENCE=0.3

# Pipeline tuning
export ESASS_BUFFER_SIZE=100
export ESASS_FLUSH_INTERVAL=5.0
export ESASS_SAMPLE_RATE=1.0  # 1.0 = keep all, 0.1 = sample 10%
```

### Documentation

- **esass/probes/README.md** - Complete probe system documentation
- **INTEGRATION_PLAN.md** - 26-week integration roadmap
- **PROBE_IMPLEMENTATION_SUMMARY.md** - Implementation details
- **examples/claude_code_integration.py** - Claude Code integration example
- **examples/opencode_ai_integration.py** - open-code-ai integration example (NEW!)

## OpenClaw × ClawHub Integration (NEW!)

**Status**: ✅ Complete recursive learning loop implementation (1873 lines)

ESASS now includes a complete integration with OpenClaw and ClawHub that closes the recursive learning loop: observation → pattern detection → skill generation → publication → ecosystem deployment.

### The Recursive Loop

```text
┌─────────────────────────────────────────────────────────────┐
│                    RECURSIVE LEARNING CYCLE                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Day 1-3: OBSERVE                                           │
│  ├── OpenClaw agents execute tasks                          │
│  ├── ESASS probes capture events                           │
│  └── Event pipeline writes to log store                     │
│                                                             │
│  Day 4-7: DETECT                                            │
│  ├── Pattern detector mines frequent sequences              │
│  ├── Quality metrics computed (support, confidence)         │
│  └── Skill candidates identified                            │
│                                                             │
│  Day 7: GENERATE                                            │
│  ├── Template generator creates SkillManifest              │
│  ├── Formatter converts to SKILL.md                        │
│  └── Validation ensures quality                             │
│                                                             │
│  Day 7: PUBLISH                                             │
│  ├── ClawHub client publishes skill                        │
│  ├── Vector embedding computed for search                   │
│  └── Skill available to all OpenClaw users                  │
│                                                             │
│  Day 8+: EVOLVE                                             │
│  ├── Feedback tracks skill usage                           │
│  ├── Similar skills unify                                   │
│  ├── New patterns emerge from enhanced agents               │
│  └── LOOP CLOSES → Back to OBSERVE                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

**OpenClaw Event Bridge** (`openclaw-plugin/src/bridge/openclaw_hooks.py`)
- Captures events from OpenClaw agent loop
- Routes to ESASS probes (tool calls, reasoning, decisions)
- Tracks skill activations and feedback metrics
- Maintains session state and causality chains

**Skill Formatter** (`openclaw-plugin/src/adapters/skill_formatter.py`)
- Converts ESASS SkillManifest to OpenClaw SKILL.md format
- Generates YAML frontmatter with genesis metadata
- Auto-generates workflow steps, examples, error handling
- Tracks evolution history and skill lineage

**ClawHub Client** (`openclaw-plugin/src/adapters/clawhub_client.py`)
- Publishes skills to ClawHub registry
- Manages versioning (semver auto-bump)
- Handles authentication and rate limiting
- Supports batch operations and sync

**Recursive Loop Controller** (`openclaw-plugin/src/loop/controller.py`)
- Orchestrates the complete learning cycle
- Configurable timing and quality thresholds
- Metrics tracking and health monitoring
- Safety guardrails (rate limits, human approval)

### Quick Start

```bash
# Run the demo loop
cd openclaw-plugin
python examples/quick_start.py
```

This will simulate a complete cycle:
1. Generate 5 OpenClaw sessions with git workflow events
2. Detect patterns from accumulated observations
3. Generate skills from validated patterns
4. Display cycle metrics and loop status

### Configuration

```bash
# ESASS Configuration
export ESASS_ENABLED=true
export ESASS_DATA_DIR=./data/esass
export ESASS_SAMPLE_RATE=1.0

# OpenClaw Integration
export OPENCLAW_WORKSPACE=~/.openclaw
export OPENCLAW_GATEWAY_URL=ws://127.0.0.1:18789

# ClawHub Publishing
export CLAWHUB_REGISTRY=https://clawhub.com
export CLAWHUB_TOKEN=your-token-here

# Loop Timing
export LOOP_OBSERVATION_HOURS=24
export LOOP_CYCLE_HOURS=6
export LOOP_AUTO_PUBLISH=true
```

### Production Usage

```python
from openclaw_plugin.loop.controller import RecursiveLoopController, LoopConfig

# Configure the loop
config = LoopConfig(
    observation_window_hours=24,
    cycle_interval_hours=6,
    min_support=10,
    min_confidence=0.8,
    auto_publish=True,
    require_human_approval=False
)

# Create and start controller
controller = RecursiveLoopController(config=config)

# Register callbacks
controller.on_skill_generated(lambda s: print(f"✓ Generated: {s.name}"))
controller.on_skill_published(lambda s, r: print(f"✓ Published: {r.url}"))

# Run continuously
await controller.start()
```

### Documentation

- **openclaw-plugin/README.md** - Integration overview
- **openclaw-plugin/ESASS_OPENCLAW_INTEGRATION.md** - Architecture details
- **openclaw-plugin/IMPLEMENTATION_GUIDE.md** - Complete code walkthrough
- **openclaw-plugin/EXPLORABLE_DOCUMENTATION.md** - Visual deep dives
- **openclaw-plugin/OPENCLAW_PLUGIN_SPEC.md** - Technical specification

## Project Structure

```text
ESASS/
├── esass/                        # Real-time event capture system
│   ├── probes/                   # Probe infrastructure
│   │   ├── __init__.py
│   │   ├── base.py              # Base probe classes and tag extraction
│   │   ├── tool_probe.py        # Tool call observation
│   │   ├── reasoning_probe.py   # Reasoning extraction
│   │   ├── decision_probe.py    # Decision tracking
│   │   ├── registry.py          # Event routing and coordination
│   │   ├── pipeline.py          # Buffered async processing
│   │   ├── config.py            # Configuration system
│   │   └── README.md            # Probe documentation
│   └── __init__.py
│
├── openclaw-plugin/              # OpenClaw × ClawHub integration (NEW!)
│   ├── src/
│   │   ├── bridge/              # OpenClaw event bridge
│   │   │   ├── openclaw_hooks.py # Event capture and routing
│   │   │   └── __init__.py
│   │   ├── adapters/            # Format conversion and publishing
│   │   │   ├── skill_formatter.py # ESASS → SKILL.md conversion
│   │   │   ├── clawhub_client.py  # ClawHub API client
│   │   │   └── __init__.py
│   │   ├── loop/                # Recursive learning loop
│   │   │   ├── controller.py   # Loop orchestration
│   │   │   └── __init__.py
│   │   ├── config/              # Configuration management
│   │   │   ├── settings.py     # Integration settings
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── examples/
│   │   └── quick_start.py      # Demo script
│   ├── skills/
│   │   └── generated/          # ESASS-generated skills
│   ├── README.md                # Integration overview
│   ├── ESASS_OPENCLAW_INTEGRATION.md # Architecture details
│   ├── IMPLEMENTATION_GUIDE.md  # Complete code walkthrough
│   ├── EXPLORABLE_DOCUMENTATION.md # Visual deep dives
│   └── OPENCLAW_PLUGIN_SPEC.md  # Technical specification
│
├── esass_prototype/              # Core prototype implementation
│   ├── observation/              # Event simulation and logging
│   │   ├── simulator.py         # Generate synthetic events
│   │   └── logger.py            # Observation logger
│   ├── storage/                  # Data persistence layer
│   │   ├── log_store.py         # Event log storage
│   │   ├── pattern_store.py     # Pattern persistence
│   │   └── skill_store.py       # Skill registry
│   ├── analysis/                 # Pattern detection
│   │   ├── pattern_detector.py  # Temporal pattern mining
│   │   └── metrics.py           # Quality metrics
│   ├── genesis/                  # Skill generation
│   │   ├── candidate.py         # Pattern candidacy evaluation
│   │   └── template.py          # Skill template generation
│   ├── export/                   # Export functionality
│   │   └── obsidian.py          # Obsidian markdown export
│   ├── models.py                 # Core data models
│   ├── config.py                 # Configuration management
│   └── cli.py                    # Command-line interface
│
├── examples/                     # Integration examples
│   ├── claude_code_integration.py # Claude Code integration example
│   └── opencode_ai_integration.py # open-code-ai integration example
│
├── tests/                        # Test suite
│   ├── test_probes.py           # Probe system tests (27 tests, 85% coverage)
│   └── test_opencode_integration.py # open-code-ai integration tests (13 tests)
│
├── data/                         # Runtime data (created by system)
│   ├── logs/                    # Event logs (JSONL)
│   ├── patterns/                # Detected patterns (JSON)
│   └── skills/                  # Generated skills (JSON)
│
├── obsidian_export/             # Obsidian export output
│   └── ESASS/                   # Vault structure
│       ├── README.md            # Navigation index
│       ├── patterns/            # Pattern markdown files
│       └── skills/              # Skill markdown files
│
├── test_pipeline.py             # Full pipeline demo
├── sensors.py                   # Dagster evolution sensors
├── QUICKSTART.md                # Quick start guide
├── INTEGRATION_PLAN.md          # 26-week integration roadmap
├── PROBE_IMPLEMENTATION_SUMMARY.md # Probe implementation details
├── ARCHITECTURE.md              # System architecture
├── esass-specification_v0.01.md # Complete specification
└── CLAUDE.md                    # Development guide
```

## CLI Commands

The prototype provides a command-line interface with several commands:

### Start/Stop Observation

```bash
# Enable simulation mode (auto-generates events)
uv run esass observe-start

# Stop observation
uv run esass observe-stop
```

### Analyze Logs

```bash
# Detect patterns in last 7 days of logs
uv run esass analyze --days 7

# Analyze all available logs
uv run esass analyze
```

### Generate Skills

```bash
# Generate skills from all candidate patterns
uv run esass generate-skills

# Show what would be generated without saving
uv run esass generate-skills --dry-run
```

### Export to Obsidian

```bash
# Export to default location (./obsidian_export/ESASS)
uv run esass export

# Export to specific Obsidian vault
uv run esass export --vault /path/to/vault/ESASS

# Export only patterns
uv run esass export --patterns-only
```

### Run Full Pipeline

```bash
# Execute complete learning loop
uv run esass pipeline

# Customize pipeline parameters
uv run esass pipeline --sessions 50 --days 14
```

### View Statistics

```bash
# Show current system statistics
uv run esass stats
```

## Prototype Configuration

Configuration is managed via `esass_prototype/config.py`:

```python
from esass_prototype.config import ESASSConfig, get_config

# Get default configuration
config = get_config()

# Customize configuration
config.observation.simulation_sessions_per_day = 30
config.pattern_detection.min_support = 15
config.export.obsidian_vault = "/path/to/vault"

# Access configuration values
data_dir = config.storage.data_dir
min_confidence = config.pattern_detection.min_confidence
```

### Configuration Sections

**Observation**:

- `mode`: "simulation" or "capture"
- `simulation_sessions_per_day`: Number of sessions to generate
- `simulation_days`: Days to simulate
- `enabled`: Observation active state

**Storage**:

- `data_dir`: Where to store logs/patterns/skills (default: "./data")
- `log_format`: "jsonl"
- `compression`: Enable compression (default: false)
- `max_log_age_days`: Log retention (default: 90 days)

**Pattern Detection**:

- `min_support`: Minimum pattern instances (default: 10)
- `min_confidence`: Minimum reliability 0-1 (default: 0.8)
- `min_stability_days`: Minimum stability period (default: 7)
- `max_gap_seconds`: Max time between events in sequence (default: 300)
- `min_sequence_length`: Minimum events in pattern (default: 2)
- `max_sequence_length`: Maximum events in pattern (default: 5)

**Skill Generation**:

- `auto_generate`: Auto-generate from candidates (default: true)
- `require_validation`: Require validation before use (default: true)
- `max_skills_per_pattern`: Max skills per pattern (default: 1)

**Export**:

- `obsidian_vault`: Path to Obsidian vault (optional)
- `auto_export`: Auto-export on pattern/skill changes (default: false)
- `export_format`: "markdown" (default)
- `export_dir`: Export directory (default: "./obsidian_export")

## Data Models

The prototype uses three core data models defined in `esass_prototype/models.py`:

### LogEntry

Captures individual events with causality tracking:

```python
LogEntry(
    event_id="uuid",
    timestamp="ISO-8601",
    event_type="reasoning|tool_usage|decision|error|outcome",
    event_data={...},
    session_id="session-uuid",
    caused_by="parent-event-id",  # Optional causality chain
    tags=["git", "commit", "workflow"]
)
```

### PatternDefinition

Represents detected recurring sequences:

```python
PatternDefinition(
    pattern_id="uuid",
    pattern_type="temporal|semantic|hybrid",
    sequence=["reasoning:git", "tool_usage:git,status", "decision:git"],
    support=45,              # Number of instances
    confidence=0.95,         # Reliability score
    stability_days=10,       # Days pattern has appeared
    skill_candidate=True,    # Meets candidacy criteria
    exemplar_ids=[...],      # Example event IDs
    first_seen="ISO-8601",
    last_seen="ISO-8601",
    tags=["git", "workflow"]
)
```

### SkillManifest

Complete skill specification with lineage:

```python
SkillManifest(
    skill_id="uuid",
    name="git_commit_skill",
    description="Automated git commit workflow...",
    source_pattern_ids=["pattern-uuid"],
    triggers=["intent_match:git,commit", "event_type:reasoning"],
    capabilities=["git_operations", "tool_orchestration"],
    implementation_summary="Sequence: reasoning → status → diff → decision → commit",
    genesis_type="derived",
    validation_status="pending|validated|rejected",
    created_at="ISO-8601",
    version="0.1.0"
)
```

## Storage Layer

The prototype uses a simple file-based storage system:

### Log Storage (JSONL)

Organized by date for efficient querying:

- `data/logs/log_20260201.jsonl` - Daily append-only files
- One JSON object per line
- Supports date-range queries and session filtering

```python
from esass_prototype.storage.log_store import LogStore

store = LogStore()
store.append(log_entry)                           # Append single entry
store.append_batch(entries)                       # Batch append
logs = store.read_last_n_days(7)                  # Query last 7 days
session_logs = store.get_session_logs("sess-id") # Filter by session
```

### Pattern Storage (JSON)

Individual files per pattern:

- `data/patterns/{pattern_id}.json` - Complete pattern with metrics
- Supports filtering by candidacy, quality thresholds

```python
from esass_prototype.storage.pattern_store import PatternStore

store = PatternStore()
store.save(pattern)                               # Save pattern
patterns = store.load_all()                       # Load all
candidates = store.load_candidates()              # Only candidates
high_quality = store.get_high_quality(            # Filter by quality
    min_support=15,
    min_confidence=0.85,
    min_stability_days=10
)
```

### Skill Storage (JSON)

Individual files per skill manifest:

- `data/skills/{skill_id}.json` - Complete manifest
- Supports filtering by validation status, pattern source

```python
from esass_prototype.storage.skill_store import SkillStore

store = SkillStore()
store.save(skill)                                 # Save skill
skills = store.load_all()                         # Load all
pending = store.load_pending()                    # Pending validation
validated = store.load_validated()                # Validated skills
store.update_validation_status(skill_id, "validated")
```

## Pattern Detection Algorithm

The prototype implements a simplified PrefixSpan algorithm:

1. **Group by Session**: Organize logs by session_id
2. **Extract Sequences**: Convert each session to event sequence
3. **Mine Subsequences**: Find all frequent subsequences (length 2-5)
4. **Calculate Metrics**:
   - **Support**: Number of occurrences
   - **Confidence**: P(full sequence | first event)
   - **Stability**: Days pattern has appeared
5. **Evaluate Candidacy**: Apply thresholds to identify skill candidates

```python
from esass_prototype.analysis.pattern_detector import TemporalPatternDetector

detector = TemporalPatternDetector(
    min_support=10,
    min_confidence=0.8,
    min_stability_days=7,
    max_gap_seconds=300,
    min_sequence_length=2,
    max_sequence_length=5
)

patterns = detector.detect_patterns(logs)
```

## Skill Generation

Skills are generated from validated patterns using template-based approach:

1. **Extract Triggers**: From first event in sequence
2. **Infer Capabilities**: From event types and tags
3. **Generate Name**: From dominant tags
4. **Create Implementation Summary**: Describe the sequence

```python
from esass_prototype.genesis.template import SkillTemplateGenerator

generator = SkillTemplateGenerator()
skill = generator.generate_from_pattern(pattern)
skills = generator.generate_from_patterns(candidates)
```

Generated skills include:

- `git_commit_skill` - Git workflow automation
- `analysis_codebase_skill` - Code exploration
- `bug_diagnosis_skill` - Error investigation
- `documentation_readme_skill` - README updates
- `coverage_testing_skill` - Test generation

## Obsidian Export Format

Exported markdown files use YAML frontmatter for metadata:

### Pattern Export

```markdown
---
pattern_id: uuid
type: temporal
support: 45
confidence: 0.95
stability_days: 10
skill_candidate: true
first_seen: 2026-01-25T10:30:00
last_seen: 2026-02-01T15:45:00
---

# Pattern: reasoning(git,commit) -> tool_usage(git,status) -> decision(git)

## Metrics
- **Support**: 45 instances
- **Confidence**: 95%
- **Stability**: 10 days
- **Skill Candidate**: Yes ✓

## Sequence
1. reasoning:git,commit,workflow
2. tool_usage:git,status
3. decision:git,staging

## Exemplars
- Event abc123... (2026-01-25)
- Event def456... (2026-01-28)
...
```

### Skill Export

```markdown
---
skill_id: uuid
name: git_commit_skill
version: 0.1.0
genesis_type: derived
status: pending
created: 2026-02-01T11:20:00
tags: [git, commit, workflow]
---

# Skill: git_commit_skill

## Description
Automated git commit workflow derived from observed patterns...

## Lineage
**Genesis Type**: derived
**Source Patterns**: [[pattern_abc123]]

## Triggers
- intent_match:git,commit
- event_type:reasoning
- context:git,workflow

## Capabilities
- git_operations
- tool_orchestration

## Implementation
Sequence: reasoning → git status → git diff → decision → git add → git commit
...
```

## Integration with Obsidian

To use the exported data in Obsidian:

1. **Configure Vault Path**:

   ```python
   # In config.py or via CLI
   config.export.obsidian_vault = "/path/to/vault/ESASS"
   ```

2. **Export Data**:

   ```bash
   uv run esass export --vault /path/to/vault/ESASS
   ```

3. **Open in Obsidian**:
   - Navigate to the ESASS folder
   - Start with `README.md` for overview
   - Use internal links to navigate between patterns and skills
   - Leverage graph view to visualize relationships

## Development

### Running Tests

```bash
# Run the full pipeline test
uv run python test_pipeline.py

# Run specific test scenarios
uv run python -m esass_prototype.observation.simulator
```

### Adding New Scenarios

Edit `esass_prototype/observation/simulator.py` to add new event scenarios:

```python
def _my_custom_scenario(self, session_id: str, base_time: datetime) -> List[LogEntry]:
    """Generate events for custom scenario"""
    entries = []
    current_time = base_time

    # Create event sequence
    entry1 = create_reasoning_event(
        statement="Custom scenario starts...",
        confidence=0.9,
        session_id=session_id,
        tags=["custom", "scenario"]
    )
    entries.append(entry1)

    # Add more events...

    return entries

# Register in SCENARIOS list
SCENARIOS = [..., "my_custom_scenario"]
```

### Extending Pattern Detection

Implement additional pattern detection algorithms in `esass_prototype/analysis/`:

```python
class SemanticPatternDetector:
    """Detect semantic patterns using embeddings"""

    def detect_patterns(self, logs: List[LogEntry]) -> List[PatternDefinition]:
        # Implement semantic clustering
        pass
```

### Custom Skill Templates

Extend `SkillTemplateGenerator` in `esass_prototype/genesis/template.py`:

```python
def _custom_capability_inference(self, pattern: PatternDefinition) -> List[str]:
    """Custom logic for inferring capabilities"""
    capabilities = []
    # Your logic here
    return capabilities
```

## Architecture Overview

The prototype demonstrates core ESASS concepts:

```text
┌─────────────────────────────────────────────────────────┐
│                  ESASS Prototype Pipeline                │
...
```

## Performance

Current prototype performance (on test data):

- **Event Generation**: 196 events in <1s
- **Pattern Detection**: 20 patterns from 2500+ events in <2s
- **Skill Generation**: 16 skills in <1s
- **Obsidian Export**: Complete vault in <1s

## Roadmap

### ✅ Completed

**Phase 1 - Core Prototype**:
- ✓ Event observation and logging
- ✓ Pattern detection with quality metrics
- ✓ Skill candidate identification
- ✓ Automated skill generation
- ✓ Obsidian export for visualization

**Phase 2 - Real-Time Capture**:
- ✓ Production-ready probe system (tool, reasoning, decision)
- ✓ Event routing and coordination
- ✓ Buffered async processing pipeline
- ✓ Integration examples (Claude Code, open-code-ai)
- ✓ Comprehensive test coverage (85%)

**Phase 3 - Recursive Learning Loop**:
- ✓ OpenClaw event bridge
- ✓ ESASS → SKILL.md skill formatter
- ✓ ClawHub publishing client
- ✓ Loop orchestration controller
- ✓ Configuration and metrics system

### 🚧 In Progress

**Phase 4 - Production Deployment**:
- Claude Code hook integration
- OpenClaw gateway connection
- ClawHub authentication setup
- Monitoring and alerting

### 📋 Planned

**Phase 5 - Advanced Patterns**:
- Semantic pattern detection (LDA, embeddings)
- Structural pattern mining (graph patterns)
- Behavioral pattern analysis
- Multi-dimensional pattern clustering

**Phase 6 - Production Storage**:
- Graph database for pattern relationships
- Vector database for semantic search
- Time-series database for log queries
- Distributed storage layer

**Phase 7 - Skill Evolution**:
- Similarity-based skill consolidation
- Behavior chain optimization
- Emergent capability detection
- Automatic skill refinement
- Skill lifecycle management

**Phase 8 - Dagster Integration**:
- Orchestration pipelines
- Scheduled analysis jobs
- Event-driven triggers
- Production monitoring
- Health dashboards

## Project Documentation

### Core Specification
- **[Full Specification](esass-specification_v0.01.md)**: Complete technical specification (1271 lines)
- **[Architecture](ARCHITECTURE.md)**: Evolution system architecture details
- **[Development Guide](CLAUDE.md)**: Guide for Claude Code development
- **[Quick Start](QUICKSTART.md)**: Getting started guide

### Probe System
- **[Probe System README](esass/probes/README.md)**: Complete probe documentation
- **[Integration Plan](INTEGRATION_PLAN.md)**: 26-week integration roadmap
- **[Implementation Summary](PROBE_IMPLEMENTATION_SUMMARY.md)**: Implementation details

### OpenClaw Integration
- **[openclaw-plugin/README.md](openclaw-plugin/README.md)**: Integration overview
- **[ESASS_OPENCLAW_INTEGRATION.md](openclaw-plugin/ESASS_OPENCLAW_INTEGRATION.md)**: Architecture details
- **[IMPLEMENTATION_GUIDE.md](openclaw-plugin/IMPLEMENTATION_GUIDE.md)**: Complete code walkthrough
- **[EXPLORABLE_DOCUMENTATION.md](openclaw-plugin/EXPLORABLE_DOCUMENTATION.md)**: Visual deep dives

## Success Metrics

The system successfully demonstrates:

### Core Prototype
- ✓ Event observation and logging
- ✓ Pattern detection with quality metrics
- ✓ Skill candidate identification
- ✓ Automated skill generation
- ✓ Export to human-readable format
- ✓ Complete learning loop execution

Prototype test results:
- 20+ patterns detected from 35 sessions
- 16 skill candidates identified (80% success rate)
- 100% confidence on top patterns
- 8+ days stability across pattern set

### Production Probe System
- ✓ Real-time event capture from AI coding assistants
- ✓ 27 passing tests with 85% code coverage
- ✓ <10ms capture latency (target met)
- ✓ 1500+ events/sec throughput (150% of target)
- ✓ ~60MB memory footprint (40% below target)
- ✓ ~2% CPU overhead (60% below target)

### OpenClaw Integration
- ✓ Complete recursive learning loop (1873 lines)
- ✓ OpenClaw event bridge with session tracking
- ✓ ESASS → SKILL.md skill formatter
- ✓ ClawHub publishing client with versioning
- ✓ Loop orchestration with metrics
- ✓ Configuration and safety guardrails

## Dependencies

```toml
[project]
requires-python = ">=3.8"
dependencies = [
    "click>=8.0",         # CLI framework
    "python-dateutil>=2.8" # Date handling
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.0",        # Testing
    "pytest-cov>=4.0"     # Coverage
]
```

## License

[License information to be added]

## Authors

**Collaborative Design**: Human + AI
**Version**: 0.2.0
**Last Updated**: 2026-02-02

---

*This system is designed to be transparent, ethical, and bounded by core value constraints. The "emergent self" is a functional pattern, not consciousness—a distributed, interruptible capacity for learning and adaptation.*
