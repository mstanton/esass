# ESASS Quick Start Guide

Get up and running with the ESASS prototype in 5 minutes.

## Prerequisites

- Python 3.8 or higher
- Git (optional, for version control)
- Terminal/Command prompt access

## Step 1: Installation

### Install uv (Python Package Manager)

```bash
# On Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via pip
pip install uv
```

### Install ESASS Prototype

```bash
# Navigate to ESASS directory
cd C:\workspace\ESASS

# Sync dependencies and install package
uv sync

# Verify installation
uv run esass --help
```

Expected output:

```text
Usage: esass [OPTIONS] COMMAND [ARGS]...

  ESASS - Emergent Self-Adaptive Skill System

Commands:
  analyze          Analyze logs and detect patterns
  export           Export to Obsidian vault
  generate-skills  Generate skills from candidate patterns
  observe-start    Start observation mode
  observe-stop     Stop observation mode
  pipeline         Run full pipeline
  stats            Show system statistics
```

## Step 2: Run the Demo Pipeline

Execute the complete ESASS learning loop:

```bash
uv run python test_pipeline.py
```

You should see output like:

```text
============================================================
ESASS PROTOTYPE - FULL PIPELINE TEST
============================================================

[1/4] GENERATING SIMULATED DATA...
[OK] Generated 196 events across 35 sessions

[2/4] LOGGING EVENTS...
[OK] Logged 196 events, 35 sessions

[3/4] DETECTING PATTERNS...
[OK] Detected 20 patterns
  - Skill candidates: 16

  Top patterns:
  [OK] 1. reasoning(analysis,codebase,exploration) ->tool_usage(files,...
     Support: 45, Confidence: 100%, Stability: 8d

[4/4] GENERATING SKILLS...
[OK] Generated 16 skills from 16 candidate patterns

[5/5] EXPORTING TO OBSIDIAN...
[OK] Exported to obsidian_export\ESASS

============================================================
PIPELINE COMPLETE [SUCCESS]
============================================================
Total events: 196
Total patterns: 20
Skill candidates: 16
Generated skills: 16

Results exported to: obsidian_export\ESASS\README.md
============================================================
```

## Step 3: Explore the Results

### View Generated Data

The pipeline creates several directories with output:

```bash
# View log files (JSONL format)
ls data/logs/

# View detected patterns (JSON)
ls data/patterns/

# View generated skills (JSON)
ls data/skills/

# View Obsidian export (Markdown)
ls obsidian_export/ESASS/
```

### Examine a Pattern

```bash
# View a pattern file (Windows)
type data\patterns\pattern_*.json | more

# View a pattern file (macOS/Linux)
cat data/patterns/pattern_*.json | head -20
```

Example pattern:

```json
{
  "pattern_id": "abc123...",
  "pattern_type": "temporal",
  "sequence": [
    "reasoning:git,commit,workflow",
    "tool_usage:git,status",
    "decision:git,staging"
  ],
  "support": 45,
  "confidence": 0.95,
  "stability_days": 10,
  "skill_candidate": true,
  "tags": ["git", "commit", "workflow"],
  "first_seen": "2026-01-25T10:30:00",
  "last_seen": "2026-02-01T15:45:00"
}
```

### Examine a Skill

```bash
# View a skill manifest (Windows)
type data\skills\git_commit_skill.json

# View a skill manifest (macOS/Linux)
cat data/skills/git_commit_skill.json
```

Example skill:

```json
{
  "skill_id": "def456...",
  "name": "git_commit_skill",
  "description": "reasoning(git,commit,workflow) ->tool_usage(git,status) ->decision(git,staging)",
  "source_pattern_ids": ["pattern-abc123"],
  "triggers": [
    "intent_match:git,commit,workflow",
    "event_type:reasoning"
  ],
  "capabilities": [
    "git_operations",
    "tool_orchestration"
  ],
  "implementation_summary": "...",
  "validation_status": "pending",
  "genesis_type": "derived",
  "version": "0.1.0"
}
```

## Step 4: Use CLI Commands

### View System Statistics

```bash
uv run esass stats
```

Output:

```text
ESASS System Statistics

Logs:
  Total events: 196
  Total sessions: 35
  Date range: 2026-01-25 to 2026-02-01
  Storage size: 245 KB

Patterns:
  Total patterns: 20
  Skill candidates: 16 (80%)
  Avg support: 28.5
  Avg confidence: 0.92
  Avg stability: 8.2 days

Skills:
  Total skills: 16
  Pending validation: 16
  Validated: 0
  Unique capabilities: 8
```

### Analyze Logs

```bash
# Analyze last 7 days
uv run esass analyze --days 7

# Analyze all logs
uv run esass analyze
```

### Generate Skills

```bash
# Generate from all candidate patterns
uv run esass generate-skills

# Preview without saving
uv run esass generate-skills --dry-run
```

### Export to Obsidian

```bash
# Export to default location
uv run esass export

# Export to specific vault
uv run esass export --vault C:\Users\YourName\Documents\ObsidianVault\ESASS
```

## Step 5: Integration with Obsidian (Optional)

### Install Obsidian

1. Download from <https://obsidian.md/>
2. Install and create a new vault or use existing one

### Configure ESASS Export

Edit `esass_prototype/config.py` or create a config file:

```python
from esass_prototype.config import ESASSConfig

config = ESASSConfig()
config.export.obsidian_vault = "C:/Users/YourName/Documents/ObsidianVault/ESASS"
config.export.auto_export = True  # Auto-export on changes
```

### Export and View

```bash
# Export to configured vault
uv run esass export

# Open Obsidian and navigate to ESASS folder
# Start with README.md for overview
```

### Navigate in Obsidian

- **README.md**: Overview with statistics and navigation
- **patterns/**: Individual pattern files with metrics
- **skills/**: Skill manifests with lineage
- **logs/**: Daily log summaries

Use Obsidian's features:

- **Internal links**: Click [[pattern_abc123]] to jump to pattern
- **Graph view**: Visualize relationships between patterns and skills
- **Search**: Find patterns by tags, support, or confidence
- **Tags**: Filter by #git, #testing, #documentation, etc.

## Step 6: Customize Configuration

Edit `esass_prototype/config.py` for your needs:

```python
from esass_prototype.config import ESASSConfig

config = ESASSConfig()

# Adjust pattern detection thresholds
config.pattern_detection.min_support = 15        # More strict
config.pattern_detection.min_confidence = 0.85   # Higher confidence required
config.pattern_detection.min_stability_days = 10 # Longer stability period

# Change storage location
config.storage.data_dir = "./my_custom_data"

# Enable auto-export
config.export.auto_export = True
config.export.obsidian_vault = "/path/to/vault/ESASS"
```

## Common Tasks

### Clear All Data and Start Fresh

```bash
# Remove all generated data
rm -rf data/
rm -rf obsidian_export/

# Run pipeline again
uv run python test_pipeline.py
```

### Increase Simulation Data

Edit `test_pipeline.py`:

```python
# Change session count and duration
entries = simulator.generate_multiple_sessions(count=100, days=30)
```

Then run:

```bash
uv run python test_pipeline.py
```

### Run Only Pattern Detection

```python
from esass_prototype.storage.log_store import LogStore
from esass_prototype.analysis.pattern_detector import TemporalPatternDetector

# Load existing logs
log_store = LogStore()
logs = log_store.load_all()

# Detect patterns with custom thresholds
detector = TemporalPatternDetector(
    min_support=20,
    min_confidence=0.9,
    min_stability_days=14
)
patterns = detector.detect_patterns(logs)

print(f"Detected {len(patterns)} patterns")
for p in patterns[:5]:
    print(f"  - {p.description} (support={p.support})")
```

### Generate Custom Events

```python
from esass_prototype.observation.simulator import EventSimulator

# Create simulator
simulator = EventSimulator(seed=42)

# Generate specific scenario
events = simulator._git_workflow_sequence("session-123", datetime.utcnow())

# Or generate multiple sessions
events = simulator.generate_multiple_sessions(count=50, days=7)
```

## Troubleshooting

### uv command not found

```bash
# Add uv to PATH (Windows)
# Restart terminal after installation

# Or use full path
C:\Users\YourName\.cargo\bin\uv.exe run esass --help
```

### Module not found errors

```bash
# Ensure you're in the ESASS directory
cd C:\workspace\ESASS

# Reinstall dependencies
uv sync

# Verify package is installed
uv run python -c "import esass_prototype; print('OK')"
```

### No patterns detected

Possible causes:

- Not enough events (generate more sessions)
- Thresholds too high (lower min_support, min_confidence)
- Events too random (use lower seed value for more consistent scenarios)

Solution:

```bash
# Generate more data with more sessions
uv run esass pipeline --sessions 100 --days 14

# Or lower thresholds in config.py
config.pattern_detection.min_support = 5
config.pattern_detection.min_confidence = 0.7
```

### Unicode encoding errors

If you see `UnicodeEncodeError` on Windows:

```bash
# Set environment variable
set PYTHONIOENCODING=utf-8

# Or run with UTF-8 encoding
chcp 65001
uv run python test_pipeline.py
```

## Next Steps

### Explore the Code

Key files to understand:

1. `esass_prototype/models.py` - Data models
2. `esass_prototype/observation/simulator.py` - Event generation
3. `esass_prototype/analysis/pattern_detector.py` - Pattern detection
4. `esass_prototype/genesis/template.py` - Skill generation

### Read the Documentation

- **README.md**: Full prototype documentation
- **esass/esass-specification_v0.01.md**: Complete system specification
- **esass/ARCHITECTURE.md**: Architecture details
- **esass/CLAUDE.md**: Development guide

### Extend the Prototype

Add new features:

- New event scenarios
- Additional pattern detection algorithms
- Custom skill templates
- Different export formats

### Integrate with Real System

The next phase would:

1. Replace simulation with real event capture
2. Hook into Claude Code events
3. Capture actual reasoning, tool usage, decisions
4. Process real interaction patterns

## Support

For questions or issues:

- Check the main README.md
- Review the specification in esass/esass-specification_v0.01.md
- Examine the test_pipeline.py for usage examples

---

**You're ready to explore ESASS!** Start with the demo pipeline and then experiment with the CLI commands to understand how the learning loop works.
