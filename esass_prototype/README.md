# ESASS Prototype

**Emergent Self-Adaptive Skill System** - A meta-cognitive architecture for AI skill learning

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)]()
[![Status](https://img.shields.io/badge/status-prototype-orange.svg)]()

## Overview

The ESASS Prototype implements the core meta-cognitive learning loop that transforms implicit usage patterns into explicit, composable skill definitions. This standalone prototype demonstrates:

- **Observation**: Capture and log execution events
- **Pattern Detection**: Identify recurring temporal, behavioral, and semantic patterns
- **Skill Genesis**: Convert validated patterns into skill manifests
- **Export**: Generate documentation for Obsidian vaults

## Architecture

### System Overview

```mermaid
graph TB
    subgraph "Input Layer"
        SIM[Event Simulator]
        PROBE[Probe System<br/>future integration]
    end

    subgraph "Observation Layer"
        OL[Observation Logger]
        LS[(Log Store<br/>JSONL)]
    end

    subgraph "Analysis Layer"
        TPD[Temporal Pattern<br/>Detector]
        BPD[Behavioral Pattern<br/>Detector]
        SPD[Semantic Pattern<br/>Detector]
        MET[Metrics &<br/>Ranking]
    end

    subgraph "Storage Layer"
        PS[(Pattern Store<br/>JSON)]
        SS[(Skill Store<br/>JSON)]
    end

    subgraph "Genesis Layer"
        SCE[Skill Candidacy<br/>Evaluator]
        STG[Skill Template<br/>Generator]
    end

    subgraph "Export Layer"
        OBS[Obsidian<br/>Exporter]
        VAULT[/Obsidian Vault/]
    end

    SIM --> OL
    PROBE -.-> OL
    OL --> LS

    LS --> TPD
    LS --> BPD
    LS --> SPD

    TPD --> MET
    BPD --> MET
    SPD --> MET

    MET --> PS

    PS --> SCE
    SCE --> STG
    STG --> SS

    LS --> OBS
    PS --> OBS
    SS --> OBS
    OBS --> VAULT
```

### The Meta-Cognitive Loop

```mermaid
graph LR
    subgraph "Learning Cycle"
        O[Observe] --> L[Log]
        L --> P[Detect<br/>Patterns]
        P --> G[Generate<br/>Skills]
        G --> E[Export &<br/>Document]
        E -.->|feedback| O
    end

    style O fill:#e1f5fe
    style L fill:#e8f5e9
    style P fill:#fff3e0
    style G fill:#fce4ec
    style E fill:#f3e5f5
```

### Data Flow Architecture

```mermaid
flowchart TD
    subgraph "Phase 1: Observation"
        ES[EventSimulator] -->|generates| LE[LogEntry]
        LE -->|session_id<br/>causality| OL[ObservationLogger]
        OL -->|append| LS[(LogStore<br/>log_YYYYMMDD.jsonl)]
    end

    subgraph "Phase 2: Pattern Detection"
        LS -->|read_date_range| DET{Detectors}
        DET --> TPD[TemporalPatternDetector<br/>PrefixSpan sequences]
        DET --> BPD[BehavioralPatternDetector<br/>Tool preferences<br/>Confidence profiles<br/>Error recovery<br/>Workflow styles]
        DET --> SPD[SemanticPatternDetector<br/>TF-IDF clustering<br/>Tag co-occurrence]

        TPD --> RANK[rank_patterns<br/>support × 0.4<br/>confidence × 0.3<br/>stability × 0.3]
        BPD --> RANK
        SPD --> RANK

        RANK -->|save| PS[(PatternStore<br/>pattern_*.json)]
    end

    subgraph "Phase 3: Skill Genesis"
        PS -->|load_candidates| SCE[SkillCandidacyEvaluator<br/>support ≥ 10<br/>confidence ≥ 0.8<br/>stability ≥ 7d]
        SCE -->|validated| STG[SkillTemplateGenerator<br/>Trigger extraction<br/>Capability inference<br/>Name generation]
        STG -->|save| SS[(SkillStore<br/>*_skill.json)]
    end

    subgraph "Phase 4: Export"
        LS --> EXP[ObsidianExporter]
        PS --> EXP
        SS --> EXP
        EXP -->|YAML frontmatter| VAULT[/Obsidian Vault/<br/>ESASS/]
    end
```

### Module Architecture

```mermaid
graph TB
    subgraph "esass_prototype"
        INIT[__init__.py<br/>v0.1.0]
        MOD[models.py<br/>LogEntry, PatternDefinition<br/>SkillManifest, ObserverState]
        CFG[config.py<br/>ESASSConfig hierarchy]
        CLI[cli.py<br/>Click commands]
    end

    subgraph "observation/"
        OBS_SIM[simulator.py<br/>EventSimulator<br/>5 workflow scenarios]
        OBS_LOG[logger.py<br/>ObservationLogger<br/>State management]
    end

    subgraph "storage/"
        STR_INT[interfaces.py<br/>ABC contracts]
        STR_LOG[log_store.py<br/>JSONL storage]
        STR_PAT[pattern_store.py<br/>JSON storage]
        STR_SKL[skill_store.py<br/>JSON storage]
    end

    subgraph "analysis/"
        ANA_TMP[pattern_detector.py<br/>TemporalPatternDetector]
        ANA_BEH[behavioral_detector.py<br/>BehavioralPatternDetector]
        ANA_SEM[semantic_detector.py<br/>SemanticPatternDetector]
        ANA_MET[metrics.py<br/>Quality scoring]
    end

    subgraph "genesis/"
        GEN_CAN[candidate.py<br/>SkillCandidacyEvaluator]
        GEN_TMP[template.py<br/>SkillTemplateGenerator]
    end

    subgraph "export/"
        EXP_OBS[obsidian.py<br/>ObsidianExporter]
    end

    subgraph "tui/"
        TUI_APP[app.py<br/>ESASSApp]
        TUI_PAR[parser.py<br/>StreamParser]
        TUI_PRO[process.py<br/>ProcessManager]
    end

    CLI --> MOD
    CLI --> CFG
    CLI --> OBS_LOG
    CLI --> ANA_TMP
    CLI --> ANA_BEH
    CLI --> ANA_SEM
    CLI --> GEN_CAN
    CLI --> GEN_TMP
    CLI --> EXP_OBS

    OBS_SIM --> MOD
    OBS_LOG --> STR_LOG

    STR_LOG --> STR_INT
    STR_PAT --> STR_INT
    STR_SKL --> STR_INT

    ANA_TMP --> ANA_MET
    ANA_BEH --> ANA_MET
    ANA_SEM --> ANA_MET
```

### Pattern Detection Pipeline

```mermaid
sequenceDiagram
    participant CLI
    participant LS as LogStore
    participant TPD as TemporalDetector
    participant BPD as BehavioralDetector
    participant SPD as SemanticDetector
    participant PS as PatternStore

    CLI->>LS: read_date_range(start, end)
    LS-->>CLI: List[LogEntry]

    par Parallel Detection
        CLI->>TPD: detect_patterns(logs)
        Note over TPD: Group by session<br/>Extract sequences<br/>Mine frequent patterns<br/>Calculate confidence
        TPD-->>CLI: temporal_patterns
    and
        CLI->>BPD: detect_patterns(logs)
        Note over BPD: Analyze tool preferences<br/>Confidence profiles<br/>Error recovery styles<br/>Workflow patterns
        BPD-->>CLI: behavioral_patterns
    and
        CLI->>SPD: detect_patterns(logs)
        Note over SPD: Build TF-IDF vectors<br/>Cluster by similarity<br/>Find tag themes
        SPD-->>CLI: semantic_patterns
    end

    CLI->>CLI: rank_patterns(all_patterns)
    Note over CLI: score = support×0.4 + confidence×0.3 + stability×0.3

    CLI->>PS: save_batch(ranked_patterns)
```

### Skill Genesis Pipeline

```mermaid
sequenceDiagram
    participant CLI
    participant PS as PatternStore
    participant SCE as CandidacyEvaluator
    participant STG as TemplateGenerator
    participant SS as SkillStore

    CLI->>PS: load_all()
    PS-->>CLI: List[PatternDefinition]

    loop For each pattern
        CLI->>SCE: evaluate(pattern)
        Note over SCE: Check support ≥ 10<br/>Check confidence ≥ 0.8<br/>Check stability ≥ 7 days
        SCE-->>CLI: (is_candidate, reasons)
    end

    CLI->>SCE: filter_candidates(patterns)
    SCE-->>CLI: candidates

    loop For each candidate
        CLI->>STG: generate_skill(pattern)
        Note over STG: Extract triggers<br/>Infer capabilities<br/>Generate name<br/>Build implementation
        STG-->>CLI: SkillManifest
        CLI->>SS: save(manifest)
    end
```

### Event Type Hierarchy

```mermaid
graph TD
    subgraph "Core Event Types"
        REASON[REASONING<br/>Thinking blocks]
        TOOL[TOOL_USAGE<br/>Tool invocations]
        DECISION[DECISION<br/>Explicit choices]
        ERROR[ERROR<br/>Failures]
        OUTCOME[OUTCOME<br/>Results]
    end

    subgraph "Meta-Cognitive Events"
        ERR_REC[ERROR_RECOVERY<br/>Recovery strategies]
        STRAT[STRATEGY_SHIFT<br/>Approach changes]
        CALIB[CALIBRATION<br/>Uncertainty signals]
        INSIGHT[INSIGHT<br/>Realizations]
        SCOPE[SCOPE_EXPANSION<br/>Context growth]
    end

    TOOL -->|causes| OUTCOME
    TOOL -->|causes| ERROR
    ERROR -->|triggers| ERR_REC
    REASON -->|leads to| DECISION
    REASON -->|reveals| INSIGHT
    DECISION -->|may cause| STRAT
```

### Storage Schema

```mermaid
erDiagram
    LogEntry {
        string event_id PK
        datetime timestamp
        string event_type
        dict event_data
        string session_id
        string caused_by FK
        list tags
        dict metadata
    }

    PatternDefinition {
        string pattern_id PK
        string pattern_type
        int support
        float confidence
        int stability_days
        string description
        list sequence
        list exemplar_ids FK
        bool skill_candidate
        list tags
    }

    SkillManifest {
        string skill_id PK
        string name
        string description
        list source_pattern_ids FK
        list triggers
        list capabilities
        string implementation_summary
        string genesis_type
        string version
        string validation_status
    }

    TriggerCondition {
        string trigger_type
        string pattern
        float confidence_threshold
    }

    LogEntry ||--o{ LogEntry : "caused_by"
    PatternDefinition ||--o{ LogEntry : "exemplar_ids"
    SkillManifest ||--o{ PatternDefinition : "source_pattern_ids"
    SkillManifest ||--o{ TriggerCondition : "triggers"
```

## Installation

```bash
# Navigate to prototype directory
cd esass_prototype

# Install dependencies
pip install -e ".[dev]"

# Or install requirements directly
pip install click textual
```

## Usage

### CLI Commands

```bash
# Generate simulated observation data
esass observe-start --sessions-per-day 20 --days 14

# Stop observation
esass observe-stop

# Analyze patterns from logs
esass analyze --start-date 2026-01-01 --end-date 2026-01-31

# Generate skills from patterns
esass generate-skills

# Export to Obsidian vault
esass export --output-dir ./vault

# Run full pipeline
esass pipeline --sessions-per-day 20 --days 14

# View system statistics
esass stats

# Launch TUI (experimental)
esass run
```

### Programmatic Usage

```python
from esass_prototype.config import ESASSConfig
from esass_prototype.observation.simulator import EventSimulator
from esass_prototype.observation.logger import ObservationLogger
from esass_prototype.storage.log_store import LogStore
from esass_prototype.analysis.pattern_detector import TemporalPatternDetector
from esass_prototype.genesis.candidate import SkillCandidacyEvaluator
from esass_prototype.genesis.template import SkillTemplateGenerator

# Initialize
config = ESASSConfig()
log_store = LogStore(config.storage.data_dir)
logger = ObservationLogger(log_store, config.storage.data_dir)

# Generate synthetic events
simulator = EventSimulator()
for session in simulator.generate_session_batch(20, 14):
    for event in session:
        logger.log_event(event)

# Detect patterns
detector = TemporalPatternDetector(
    min_support=config.pattern_detection.min_support,
    min_confidence=config.pattern_detection.min_confidence
)
logs = log_store.read_all()
patterns = detector.detect_patterns(logs)

# Evaluate candidates
evaluator = SkillCandidacyEvaluator(
    min_support=config.pattern_detection.min_support,
    min_confidence=config.pattern_detection.min_confidence,
    min_stability_days=config.pattern_detection.min_stability_days
)
candidates = evaluator.filter_candidates(patterns)

# Generate skills
generator = SkillTemplateGenerator()
for pattern in candidates:
    skill = generator.generate_skill(pattern)
    print(f"Generated: {skill.name}")
```

## Directory Structure

```
esass_prototype/
├── __init__.py                 # Package metadata (v0.1.0)
├── models.py                   # Core data models (402 lines)
├── config.py                   # Configuration management (109 lines)
├── cli.py                      # Click CLI interface (317 lines)
│
├── observation/                # Event capture
│   ├── logger.py               # State & event logging (117 lines)
│   └── simulator.py            # Synthetic event generation (563 lines)
│
├── storage/                    # Persistence layer
│   ├── interfaces.py           # Abstract contracts (223 lines)
│   ├── log_store.py            # JSONL log storage (177 lines)
│   ├── pattern_store.py        # JSON pattern storage (146 lines)
│   └── skill_store.py          # JSON skill storage (170 lines)
│
├── analysis/                   # Pattern detection
│   ├── pattern_detector.py     # Temporal sequences (407 lines)
│   ├── behavioral_detector.py  # Behavioral styles (451 lines)
│   ├── semantic_detector.py    # Semantic clustering (421 lines)
│   └── metrics.py              # Quality scoring (84 lines)
│
├── genesis/                    # Skill generation
│   ├── candidate.py            # Candidacy evaluation (138 lines)
│   └── template.py             # Manifest generation (229 lines)
│
├── export/                     # Output formatters
│   └── obsidian.py             # Obsidian vault export (340 lines)
│
└── tui/                        # Terminal UI (253 lines total)
    ├── app.py                  # Textual application (95 lines)
    ├── parser.py               # Stream parsing (50 lines)
    └── process.py              # PTY management (108 lines)
```

## Configuration

### Default Thresholds

| Parameter | Value | Description |
|-----------|-------|-------------|
| `min_support` | 10 | Minimum pattern occurrences |
| `min_confidence` | 0.8 | Minimum pattern confidence |
| `min_stability_days` | 7 | Days pattern must persist |
| `max_gap_seconds` | 300 | Max time between sequence events |

### Pattern Detection Thresholds by Type

| Detector | min_support | min_confidence | min_stability |
|----------|-------------|----------------|---------------|
| Temporal | 10 | 0.8 | 7 days |
| Behavioral | 5 | 0.6 | 3 days |
| Semantic | 5 | 0.6 | 3 days |

## Pattern Types

### Temporal Patterns
Recurring event sequences detected via simplified PrefixSpan algorithm:
- Git workflows: `TOOL_USAGE[git status] → DECISION → TOOL_USAGE[git commit]`
- Analysis chains: `REASONING → TOOL_USAGE[grep] → REASONING → DECISION`

### Behavioral Patterns
Usage style tendencies:
- **Tool preferences**: Tools appearing in >60% of sessions
- **Confidence profiles**: High/low/stable confidence per event type
- **Error recovery**: retry_same_tool, pivot_to_different_tool, analyze_then_act
- **Workflow styles**: analyze_first, execution_first, deep_analysis_first

### Semantic Patterns
Conceptual clustering via TF-IDF and tag co-occurrence:
- Topic themes: testing, documentation, debugging
- Concept associations: "git" + "commit" + "status"

## Obsidian Export

The exporter generates a structured vault:

```
ESASS/
├── README.md           # Index with statistics
├── logs/               # Daily summaries
│   └── 2026-01-15.md   # YAML frontmatter + event breakdown
├── patterns/           # Pattern documentation
│   └── pattern_abc.md  # Metrics, sequence, exemplars
└── skills/             # Skill manifests
    └── git_skill.md    # Triggers, capabilities, implementation
```

Each file includes YAML frontmatter for Obsidian properties and internal `[[wiki-links]]` for cross-referencing.

## Simulation Scenarios

The EventSimulator models 5 realistic Claude Code workflows:

1. **Git Workflow**: status → diff → decision → add → commit
2. **Code Analysis**: reasoning → glob → read → reasoning → decision
3. **Bug Fix**: reasoning → grep → read → diagnosis → edit → test
4. **Documentation**: reasoning → read → decision → edit → review
5. **Test Writing**: reasoning → read → decision → write → test → verify

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Event Simulation | ✅ Complete | 5 workflow scenarios |
| Log Storage | ✅ Complete | JSONL, append-only |
| Pattern Storage | ✅ Complete | JSON, searchable |
| Skill Storage | ✅ Complete | JSON, versioned |
| Temporal Detection | ✅ Complete | PrefixSpan-like |
| Behavioral Detection | ✅ Complete | 4 behavior types |
| Semantic Detection | ✅ Complete | TF-IDF clustering |
| Skill Candidacy | ✅ Complete | §6.2 criteria |
| Skill Generation | ✅ Complete | Template-based |
| Obsidian Export | ✅ Complete | YAML frontmatter |
| CLI | ✅ Complete | 8 commands |
| TUI | ✅ Complete | Textual-based |
| Probe Integration | ⏳ Planned | See esass/probes/ |
| Graph Database | ⏳ Planned | Pattern relationships |
| Vector Database | ⏳ Planned | Semantic embeddings |
| Skill Evolution | ⏳ Planned | ABSORB, MERGE, etc. |

## Related Documentation

- [ESASS Specification](../esass-specification_v0.01.md) - Complete system specification
- [Architecture](../ARCHITECTURE.md) - Detailed architecture design
- [CLAUDE.md](../CLAUDE.md) - Development guidelines
- [Probe System](../esass/probes/README.md) - Event capture probes

## License

See repository root for license information.
