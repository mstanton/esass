# ESASS Prototype Architecture

Detailed architecture documentation with visual diagrams.

## High-Level Architecture

```mermaid
graph TB
    subgraph "External World"
        CC[Claude Code]
        USER[User]
    end

    subgraph "ESASS Prototype"
        direction TB

        subgraph "Observation Subsystem"
            SIM[EventSimulator<br/>564 lines]
            OL[ObservationLogger<br/>118 lines]
        end

        subgraph "Storage Subsystem"
            LS[(LogStore<br/>JSONL)]
            PS[(PatternStore<br/>JSON)]
            SS[(SkillStore<br/>JSON)]
        end

        subgraph "Analysis Subsystem"
            TPD[TemporalPatternDetector<br/>408 lines]
            BPD[BehavioralPatternDetector<br/>452 lines]
            SPD[SemanticPatternDetector<br/>422 lines]
        end

        subgraph "Genesis Subsystem"
            SCE[SkillCandidacyEvaluator<br/>139 lines]
            STG[SkillTemplateGenerator<br/>230 lines]
        end

        subgraph "Export Subsystem"
            OBS[ObsidianExporter<br/>341 lines]
        end

        subgraph "Interface Layer"
            CLI[CLI<br/>317 lines]
            TUI[TUI<br/>256 lines]
        end
    end

    CC -.->|future| OL
    USER --> CLI
    USER --> TUI
    SIM --> OL
    OL --> LS
    LS --> TPD & BPD & SPD
    TPD & BPD & SPD --> PS
    PS --> SCE
    SCE --> STG
    STG --> SS
    LS & PS & SS --> OBS
```

## Component Interaction Diagram

```mermaid
flowchart LR
    subgraph Inputs
        direction TB
        I1[Simulated Events]
        I2[Real Claude Events]
    end

    subgraph Core["Core Processing"]
        direction TB
        L[Logging]
        A[Analysis]
        G[Genesis]
    end

    subgraph Outputs
        direction TB
        O1[Pattern DB]
        O2[Skill DB]
        O3[Obsidian Vault]
    end

    I1 --> L
    I2 -.-> L
    L --> A
    A --> G
    A --> O1
    G --> O2
    L & O1 & O2 --> O3
```

## Data Model Relationships

```mermaid
classDiagram
    class LogEntry {
        +str event_id
        +datetime timestamp
        +str event_type
        +dict event_data
        +str session_id
        +str caused_by
        +list tags
        +dict metadata
        +create() LogEntry
        +to_dict() dict
        +from_dict(d) LogEntry
    }

    class PatternDefinition {
        +str pattern_id
        +str pattern_type
        +int support
        +float confidence
        +int stability_days
        +str description
        +list sequence
        +list exemplar_ids
        +bool skill_candidate
        +list tags
        +datetime first_seen
        +datetime last_seen
        +create() PatternDefinition
        +to_dict() dict
        +from_dict(d) PatternDefinition
    }

    class SkillManifest {
        +str skill_id
        +str name
        +str description
        +list source_pattern_ids
        +list triggers
        +list capabilities
        +str implementation_summary
        +str genesis_type
        +str version
        +str validation_status
        +int usage_count
        +float success_rate
        +create() SkillManifest
        +to_dict() dict
        +from_dict(d) SkillManifest
    }

    class TriggerCondition {
        +str trigger_type
        +str pattern
        +float confidence_threshold
        +to_dict() dict
        +from_dict(d) TriggerCondition
    }

    class ObserverState {
        +bool enabled
        +str mode
        +datetime started_at
        +datetime stopped_at
        +int session_count
        +int event_count
    }

    LogEntry "1" --> "0..1" LogEntry : caused_by
    PatternDefinition "1" --> "*" LogEntry : exemplar_ids
    SkillManifest "1" --> "*" PatternDefinition : source_pattern_ids
    SkillManifest "1" --> "*" TriggerCondition : triggers
```

## Storage Layer Design

```mermaid
graph TB
    subgraph "Abstract Interfaces"
        LSI[LogStoreInterface]
        PSI[PatternStoreInterface]
        SSI[SkillStoreInterface]
    end

    subgraph "File-Based Implementations"
        LS[LogStore<br/>JSONL files]
        PS[PatternStore<br/>JSON files]
        SS[SkillStore<br/>JSON files]
    end

    subgraph "Future Implementations"
        TSDB[(TimeSeries DB)]
        GRAPH[(Graph DB)]
        DOC[(Document Store)]
    end

    LSI --> LS
    PSI --> PS
    SSI --> SS

    LSI -.-> TSDB
    PSI -.-> GRAPH
    SSI -.-> DOC

    subgraph "File Structure"
        direction LR
        DATA[data/]
        LOGS[logs/<br/>log_YYYYMMDD.jsonl]
        PATS[patterns/<br/>pattern_*.json]
        SKLS[skills/<br/>*_skill.json]
        STATE[state/<br/>observer_state.json]

        DATA --> LOGS
        DATA --> PATS
        DATA --> SKLS
        DATA --> STATE
    end
```

## Pattern Detection Architecture

```mermaid
graph TB
    subgraph "Input"
        LOGS[LogEntry Stream]
    end

    subgraph "Pre-Processing"
        GROUP[Group by session_id]
        EXTRACT[Extract sequences]
        FILTER[Filter by date range]
    end

    subgraph "Detection Engines"
        subgraph "Temporal Detection"
            FREQ[Frequent Subsequence Mining]
            CONF[Confidence Calculation]
            STAB[Stability Measurement]
        end

        subgraph "Behavioral Detection"
            TOOL[Tool Preference Analysis]
            CONFP[Confidence Profiling]
            ERR[Error Recovery Classification]
            WORK[Workflow Style Detection]
        end

        subgraph "Semantic Detection"
            TFIDF[TF-IDF Vectorization]
            CLUST[Agglomerative Clustering]
            TAGS[Tag Co-occurrence Mining]
        end
    end

    subgraph "Post-Processing"
        MERGE[Merge All Patterns]
        RANK[Quality Ranking]
        DEDUP[Deduplication]
    end

    subgraph "Output"
        PATS[PatternDefinition List]
    end

    LOGS --> GROUP --> EXTRACT --> FILTER

    FILTER --> FREQ --> CONF --> STAB
    FILTER --> TOOL & CONFP & ERR & WORK
    FILTER --> TFIDF --> CLUST
    FILTER --> TAGS

    STAB --> MERGE
    TOOL & CONFP & ERR & WORK --> MERGE
    CLUST & TAGS --> MERGE

    MERGE --> RANK --> DEDUP --> PATS
```

## Skill Genesis Pipeline

```mermaid
stateDiagram-v2
    [*] --> PatternDetected

    PatternDetected --> EvaluatingSupport: Check min_support ≥ 10
    EvaluatingSupport --> EvaluatingConfidence: Support OK
    EvaluatingSupport --> Rejected: Support < 10

    EvaluatingConfidence --> EvaluatingStability: Check min_confidence ≥ 0.8
    EvaluatingConfidence --> Rejected: Confidence < 0.8

    EvaluatingStability --> Candidate: Check min_stability ≥ 7 days
    EvaluatingStability --> Rejected: Stability < 7 days

    Candidate --> TriggerExtraction: Pattern is skill candidate

    TriggerExtraction --> CapabilityInference
    CapabilityInference --> NameGeneration
    NameGeneration --> ImplementationBuilding
    ImplementationBuilding --> ManifestCreation

    ManifestCreation --> PendingValidation: SkillManifest created

    PendingValidation --> Validated: Human approval
    PendingValidation --> Rejected: Human rejection

    Validated --> [*]
    Rejected --> [*]
```

## Event Flow Through System

```mermaid
sequenceDiagram
    participant SIM as EventSimulator
    participant OL as ObservationLogger
    participant LS as LogStore
    participant DET as Detectors
    participant PS as PatternStore
    participant GEN as Genesis
    participant SS as SkillStore
    participant EXP as ObsidianExporter

    Note over SIM,EXP: Phase 1: Observation
    loop For each session
        SIM->>SIM: select_scenario()
        loop For each event in scenario
            SIM->>OL: log_event(LogEntry)
            OL->>LS: append(entry)
        end
    end

    Note over SIM,EXP: Phase 2: Pattern Detection
    DET->>LS: read_date_range()
    LS-->>DET: List[LogEntry]

    par Parallel Detection
        DET->>DET: TemporalPatternDetector.detect()
    and
        DET->>DET: BehavioralPatternDetector.detect()
    and
        DET->>DET: SemanticPatternDetector.detect()
    end

    DET->>DET: rank_patterns(all)
    DET->>PS: save_batch(patterns)

    Note over SIM,EXP: Phase 3: Skill Genesis
    GEN->>PS: load_all()
    PS-->>GEN: List[PatternDefinition]
    GEN->>GEN: evaluate_candidates()
    loop For each candidate
        GEN->>GEN: generate_skill()
        GEN->>SS: save(manifest)
    end

    Note over SIM,EXP: Phase 4: Export
    EXP->>LS: read_all()
    EXP->>PS: load_all()
    EXP->>SS: load_all()
    EXP->>EXP: generate_vault()
```

## CLI Command Structure

```mermaid
graph TD
    ESASS[esass CLI]

    subgraph "Observation Commands"
        OS[observe-start]
        OE[observe-stop]
    end

    subgraph "Analysis Commands"
        AN[analyze]
        GS[generate-skills]
    end

    subgraph "Export Commands"
        EX[export]
    end

    subgraph "Pipeline Commands"
        PI[pipeline]
    end

    subgraph "Utility Commands"
        ST[stats]
        RU[run]
    end

    ESASS --> OS & OE
    ESASS --> AN & GS
    ESASS --> EX
    ESASS --> PI
    ESASS --> ST & RU

    OS -->|--sessions-per-day<br/>--days| SIM[EventSimulator]
    AN -->|--start-date<br/>--end-date| DET[Detectors]
    GS --> GEN[Genesis]
    EX -->|--output-dir| OBS[ObsidianExporter]
    PI -->|Full flow| ALL[All Components]
    ST --> STAT[Statistics]
    RU --> TUI[TUI App]
```

## TUI Architecture

```mermaid
graph TB
    subgraph "TUI Application"
        APP[ESASSApp<br/>Textual Framework]

        subgraph "Layout"
            TERM[Terminal Output<br/>70% height]
            DASH[Dashboard<br/>30% height]
        end

        subgraph "Widgets"
            PWIDGET[Pattern Widget]
            MLOG[Metrics Log]
        end

        subgraph "Process Management"
            PM[ProcessManager]
            PTY[PTY/WinPTY]
            PARSER[StreamParser]
        end
    end

    APP --> TERM & DASH
    DASH --> PWIDGET & MLOG
    APP --> PM
    PM --> PTY
    PTY --> PARSER
    PARSER -->|detected events| APP
```

## Configuration Hierarchy

```mermaid
graph TD
    subgraph "ESASSConfig"
        direction TB
        OC[ObservationConfig]
        SC[StorageConfig]
        PDC[PatternDetectionConfig]
        SGC[SkillGenerationConfig]
        EC[ExportConfig]
        PSC[ProbeSystemConfig]
    end

    subgraph "ObservationConfig"
        O1[mode: simulation|live]
        O2[sessions_per_day: 20]
        O3[days: 14]
    end

    subgraph "StorageConfig"
        S1[data_dir: ./data]
        S2[log_format: jsonl]
        S3[retention_days: 90]
    end

    subgraph "PatternDetectionConfig"
        P1[min_support: 10]
        P2[min_confidence: 0.8]
        P3[min_stability_days: 7]
        P4[max_gap_seconds: 300]
    end

    subgraph "SkillGenerationConfig"
        G1[auto_generate: false]
        G2[require_validation: true]
    end

    subgraph "ExportConfig"
        E1[obsidian_vault: ./vault]
        E2[export_format: markdown]
    end

    OC --> O1 & O2 & O3
    SC --> S1 & S2 & S3
    PDC --> P1 & P2 & P3 & P4
    SGC --> G1 & G2
    EC --> E1 & E2
```

## Quality Metrics Flow

```mermaid
graph LR
    subgraph "Raw Metrics"
        SUP[Support<br/>count of occurrences]
        CONF[Confidence<br/>P(full|first)]
        STAB[Stability<br/>day span]
    end

    subgraph "Calculated Metrics"
        LIFT[Lift<br/>observed/expected]
        COH[Coherence<br/>internal consistency]
        DIST[Distinctiveness<br/>uniqueness score]
    end

    subgraph "Composite Score"
        RANK[Quality Score<br/>support×0.4 + conf×0.3 + stab×0.3]
    end

    subgraph "Candidacy Thresholds"
        T1[support ≥ 10]
        T2[confidence ≥ 0.8]
        T3[stability ≥ 7 days]
    end

    SUP --> LIFT
    CONF --> COH
    STAB --> DIST

    SUP & CONF & STAB --> RANK
    RANK --> T1 & T2 & T3
```

## Future Integration Points

```mermaid
graph TB
    subgraph "Current Prototype"
        PROTO[esass_prototype]
    end

    subgraph "Core ESASS (esass/)"
        PROBES[Probe System<br/>27 tests passing]
        OPN[Observation Probe Network]
    end

    subgraph "Future Databases"
        TSDB[(TimeSeries DB<br/>Logs)]
        GRAPH[(Graph DB<br/>Patterns)]
        VECTOR[(Vector DB<br/>Embeddings)]
    end

    subgraph "Future Capabilities"
        EVOL[Skill Evolution]
        UNIFY[Skill Unification]
        EMERGE[Emergence Detection]
    end

    PROBES -.->|integration| PROTO
    OPN -.->|real events| PROTO

    PROTO -.->|migrate| TSDB
    PROTO -.->|migrate| GRAPH
    PROTO -.->|migrate| VECTOR

    PROTO -.->|extend| EVOL
    PROTO -.->|extend| UNIFY
    PROTO -.->|extend| EMERGE
```

## Code Metrics Summary

| Module | Lines | Purpose |
|--------|-------|---------|
| `models.py` | 402 | Core data models |
| `config.py` | 109 | Configuration |
| `cli.py` | 317 | CLI interface |
| `observation/simulator.py` | 563 | Event simulation |
| `observation/logger.py` | 117 | Logging |
| `storage/interfaces.py` | 223 | ABC contracts |
| `storage/log_store.py` | 177 | Log storage |
| `storage/pattern_store.py` | 146 | Pattern storage |
| `storage/skill_store.py` | 170 | Skill storage |
| `analysis/pattern_detector.py` | 407 | Temporal detection |
| `analysis/behavioral_detector.py` | 451 | Behavioral detection |
| `analysis/semantic_detector.py` | 421 | Semantic detection |
| `analysis/metrics.py` | 84 | Quality scoring |
| `genesis/candidate.py` | 138 | Candidacy evaluation |
| `genesis/template.py` | 229 | Template generation |
| `export/obsidian.py` | 340 | Obsidian export |
| `tui/app.py` | 95 | TUI application |
| `tui/parser.py` | 50 | Stream parsing |
| `tui/process.py` | 108 | PTY management |
| **Total** | **4,624** | Clean, documented Python |
