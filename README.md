# ESASS - Emergent Self-Adaptive Skill System

A meta-cognitive architecture that enables AI skills to achieve operational self-awareness through observation, pattern recognition, and autonomous skill formation.

**Current Status**: Functional prototype demonstrating core learning loop

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

## Project Structure

```text
ESASS/
├── esass_prototype/              # Core prototype implementation
│   ├── __init__.py
...
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

## Configuration

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

The prototype demonstrates the core learning loop. The full ESASS system will add:

**Phase 2 - Real Capture**:

- Hook into Claude Code events
- Capture actual reasoning, tool usage, decisions
- Real-time logging pipeline

**Phase 3 - Advanced Patterns**:

- Semantic pattern detection (LDA, embeddings)
- Structural pattern mining (graph patterns)
- Behavioral pattern analysis

**Phase 4 - Production Storage**:

- Graph database for pattern relationships
- Vector database for semantic search
- Time-series database for log queries

**Phase 5 - Skill Evolution**:

- Similarity-based skill consolidation
- Behavior chain optimization
- Emergent capability detection
- Automatic skill refinement

**Phase 6 - Dagster Integration**:

- Orchestration pipelines
- Scheduled analysis jobs
- Event-driven triggers
- Production monitoring

## Documentation

- **[Full Specification](esass/esass-specification_v0.01.md)**: Complete technical specification (1271 lines)
- **[Architecture](esass/ARCHITECTURE.md)**: Evolution system architecture details
- **[Development Guide](esass/CLAUDE.md)**: Guide for Claude Code development
- **[Prototype README](esass/README.md)**: Original project overview

## Success Metrics

The prototype successfully demonstrates:

- ✓ Event observation and logging
- ✓ Pattern detection with quality metrics
- ✓ Skill candidate identification
- ✓ Automated skill generation
- ✓ Export to human-readable format
- ✓ Complete learning loop execution

Test results show:

- 20+ patterns detected from 35 sessions
- 16 skill candidates identified (80% success rate)
- 100% confidence on top patterns
- 8+ days stability across pattern set

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
**Version**: 0.1.0
**Date**: 2026-02-01

---

*This system is designed to be transparent, ethical, and bounded by core value constraints. The "emergent self" is a functional pattern, not consciousness—a distributed, interruptible capacity for learning and adaptation.*
