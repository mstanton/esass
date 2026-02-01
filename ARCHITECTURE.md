# ESASS Skill Evolution System

## Overview

The Skill Evolution System provides meta-learning capabilities for ESASS, enabling:

- **Automatic skill consolidation** - Similar skills unified into more powerful ones
- **Behavior chain optimization** - Frequent sequences crystallized into composite skills
- **Experience-based learning** - Emergent capabilities discovered from usage patterns
- **Lifecycle management** - Skills evolve through nascent → growing → mature → deprecated

## Architecture

```text
                                    ┌─────────────────────────────────────────────────────────┐
                                    │              SKILL EVOLUTION SYSTEM                     │
                                    └─────────────────────────────────────────────────────────┘
                                                              │
        ┌─────────────────────────────────────────────────────┼─────────────────────────────────────────────────────┐
        │                                                     │                                                     │
        ▼                                                     ▼                                                     ▼
┌───────────────────┐                              ┌─────────────────────┐                              ┌─────────────────────┐
│  SIMILARITY LAYER │                              │   STATE SPACE LAYER │                              │  EXPERIENCE LAYER   │
├───────────────────┤                              ├─────────────────────┤                              ├─────────────────────┤
│                   │                              │                     │                              │                     │
│ 7-Dimensional     │                              │ Multi-Dimensional   │                              │ Usage Pattern       │
│ Similarity:       │                              │ Positioning:        │                              │ Mining:             │
│ • Semantic        │                              │ • Semantic coords   │                              │ • Success conditions│
│ • Behavioral      │       ┌─────────────────┐    │ • Performance       │     ┌───────────────────┐    │ • Failure modes     │
│ • Trigger         │─────▶│ SKILL CLUSTERS  │──▶│   coords            │──▶ │ EVOLUTION       │◀───│ • Optimization ops  │
│ • Output          │       └─────────────────┘    │ • Evolution coords  │     │ TRAJECTORIES      │    │ • Context deps      │
│ • Structural      │              │               │                     │     └───────────────────┘    │                     │
│ • Contextual      │              │               │ Fitness tracking:   │            │                 │ Emergence Detection:│
│ • Temporal        │              │               │ • Lifecycle state   │            │                 │ • Novel combinations│
│                   │              │               │ • Unification       │            │                 │ • Context general.  │
└───────────────────┘              │               │   potential         │            │                 │ • Failure adaptation│
                                   │               │ • Replacement risk  │            │                 │                     │
                                   │               │                     │            │                 └─────────────────────┘
                                   │               └─────────────────────┘            │                           │
                                   │                          │                       │                           │
                                   └──────────────────────────┼───────────────────────┘                           │
                                                              │                                                   │
                                                              ▼                                                   │
                                    ┌─────────────────────────────────────────────────────┐                       │
                                    │              UNIFICATION PIPELINE                   │◀──────────────────────┘
                                    ├─────────────────────────────────────────────────────┤
                                    │                                                     │
                                    │  Unification Methods:                               │
                                    │  • ABSORB     - Dominant skill absorbs others       │
                                    │  • MERGE      - Create new from both                │
                                    │  • PARAMETERIZE - Single skill with parameters      │
                                    │  • COMPOSE    - Hierarchical composition            │
                                    │  • GENERALIZE - Extract common abstraction          │
                                    │                                                     │
                                    │  Safety Controls:                                   │
                                    │  • Risk/benefit scoring                             │
                                    │  • Human approval workflow                          │
                                    │  • Daily rate limiting                              │
                                    │  • Rollback windows                                 │
                                    │  • Deprecation grace periods                        │
                                    │                                                     │
                                    └─────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
                                    ┌─────────────────────────────────────────────────────┐
                                    │              REPLACEMENT PLANS                      │
                                    ├─────────────────────────────────────────────────────┤
                                    │  • Deprecation timeline                             │
                                    │  • Migration mapping (old triggers → new)           │
                                    │  • Rollback procedures                              │
                                    │  • User notifications                               │
                                    └─────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
                                    ┌─────────────────────────────────────────────────────┐
                                    │              NEW UNIFIED SKILLS                     │
                                    │              (feed back into Skill Genesis)         │
                                    └─────────────────────────────────────────────────────┘
```

## Event Capture System (Real-Time Observation)

**Status**: ✅ Implemented (`esass/probes/`)

The probe system provides real-time observation of Claude Code execution, capturing events that feed into the pattern detection and skill evolution pipeline.

### Probe Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                     Claude Code Core                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │ Conversation │───▶│ Tool Pipeline │───▶│ Response Gen │ │
│  │   Manager    │    │              │    │              │ │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘ │
│         │ (1)               │ (2)               │ (3)      │
└─────────┼───────────────────┼───────────────────┼──────────┘
          │                   │                   │
          ▼                   ▼                   ▼
    ┌─────────────────────────────────────────────────┐
    │         ESASS Observation Probe Network         │
    ├─────────────────────────────────────────────────┤
    │  SessionProbe  │  ToolProbe  │  ReasoningProbe  │
    └─────────┬───────────┬───────────────┬───────────┘
              │           │               │
              └───────────┼───────────────┘
                          ▼
                   ┌──────────────┐
                   │ Event Router │
                   │  (Registry)  │
                   └──────┬───────┘
                          │
                          ▼
                   ┌──────────────┐
                   │Event Pipeline│
                   │  (Buffered)  │
                   └──────┬───────┘
                          │
                          ▼
                   ┌──────────────┐
                   │  Log Store   │
                   └──────────────┘
```

### Probe Types

1. **ToolCallProbe** (`tool_probe.py`)
   - Observes: tool_call_start, tool_call_complete, tool_call_error
   - Captures: Tool name, parameters, results, outcomes, timing
   - Features: Parameter sanitization, sequence detection, causality tracking

2. **ReasoningProbe** (`reasoning_probe.py`)
   - Observes: thinking_block, message_generated, hypothesis_formed
   - Captures: Hypotheses, confidence levels, evidence citations
   - Features: Confidence estimation, evidence extraction, causal reasoning detection

3. **DecisionProbe** (`decision_probe.py`)
   - Observes: tool_selected, approach_selected, plan_mode_decision
   - Captures: Decisions, alternatives considered, rationale
   - Features: Tradeoff analysis detection, confidence estimation

### Event Pipeline

The buffered event pipeline provides high-throughput, low-latency event processing:

- **Throughput**: 1,500+ events/sec
- **Latency**: ~3ms capture overhead
- **Buffer Size**: Configurable (default 100 events)
- **Flush Interval**: Configurable (default 5 seconds)
- **Async Processing**: Non-blocking worker thread
- **Backpressure**: Queue-based with configurable limits

### Configuration

Environment variables for probe system:

```bash
# System
ESASS_ENABLED=true
ESASS_DATA_DIR=./data
ESASS_LOG_LEVEL=INFO

# Probes
ESASS_TOOL_PROBE_ENABLED=true
ESASS_REASONING_PROBE_ENABLED=true
ESASS_DECISION_PROBE_ENABLED=true
ESASS_MIN_CONFIDENCE=0.3

# Pipeline
ESASS_BUFFER_SIZE=100
ESASS_FLUSH_INTERVAL=5.0
ESASS_SAMPLE_RATE=1.0
```

### Integration Points

The probe system hooks into Claude Code at these lifecycle points:

| Hook Point | Event Type | Data Captured |
|------------|------------|---------------|
| Tool execution start | tool_call_start | Tool name, parameters, context |
| Tool execution complete | tool_call_complete | Result, success/failure, timing |
| Tool execution error | tool_call_error | Error type, message, stack trace |
| Message generation | message_generated | Message content, context |
| Thinking block | thinking_block | Thinking content, reasoning chains |
| Decision point | tool_selected | Decision, alternatives, rationale |

### Performance

Benchmarked performance (Intel i7, 16GB RAM):

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Event capture latency | <10ms | ~3ms | ✅ |
| Throughput | 1000/sec | ~1500/sec | ✅ |
| Memory footprint | <100MB | ~60MB | ✅ |
| CPU overhead | <5% | ~2% | ✅ |

### Testing

Comprehensive test suite with 27 tests, ~85% coverage:

```bash
# Run all probe tests
pytest tests/test_probes.py -v

# With coverage
pytest tests/test_probes.py --cov=esass.probes --cov-report=html
```

See `esass/probes/README.md` for complete probe system documentation.

## Data Flow

### 1. Similarity Computation

```text
Active Skills → Embedding → 7D Similarity Matrix → Skill Clusters
```

### 2. Behavior Chain Discovery

```text
Usage Experiences → Sequence Mining → Behavior Chains → Chain Optimization
                                            │
                                            ▼
                                    Chain Optimization Types:
                                    • COLLAPSE - Merge sequential skills
                                    • PARALLELIZE - Concurrent execution
                                    • SHORTCUT - Skip intermediate steps
                                    • CACHE - Cache intermediate results
                                    • SPECIALIZE - Common case variant
```

### 3. State Space Evolution

```text
Skills + Usage + Similarity → State Space Nodes → Evolution Trajectories
                                     │
                                     ▼
                              Lifecycle States:
                              NASCENT → GROWING → MATURE → CANDIDATE → EVOLVING
                                                              ↓
                                                    DEPRECATED → ARCHIVED
                                                              or
                                                          MERGED
```

### 4. Experience-Based Emergence

```text
Usage Experiences → Pattern Mining → Experience Patterns → Emergent Capabilities
                          │                                        │
                          ▼                                        ▼
                    Pattern Types:                          Emergence Types:
                    • success_condition                     • novel_combination
                    • failure_mode                          • context_generalization
                    • optimization_opportunity              • failure_adaptation
                    • context_dependency
```

## Module Structure

```text
esass_dagster/evolution/
├── __init__.py          # Module exports
├── models.py            # Data models (40+ types)
├── assets.py            # Dagster assets (11 assets)
├── jobs.py              # Orchestration jobs (11 jobs)
├── resources.py         # Resource definitions (6 resources)
└── sensors.py           # Trigger sensors (8 sensors)
```

## Key Components

### Models (models.py)

| Category | Types |
| :--- | :--- |
| **Enums** | EvolutionStrategy, SimilarityDimension, UnificationMethod, ChainOptimizationType, SkillLifecycleState |
| **Similarity** | SkillSimilarityScore, SimilarityWeights, SkillCluster, SimilarityMatrix |
| **Chains** | BehaviorChainNode, BehaviorChainEdge, BehaviorChain, ChainOptimizationResult |
| **State Space** | SkillStateNode, SkillStateEdge, SkillStateSpace, EvolutionTrajectory |
| **Unification** | UnificationCandidate, UnifiedSkillSpec, SkillReplacementPlan |
| **Experience** | UsageExperience, ExperiencePattern, EmergentCapability |
| **Config** | EvolutionConfig |
| **Batches** | SimilarityBatch, ChainBatch, UnificationBatch, ExperienceBatch, EmergenceBatch |

### Assets (assets.py)

| Asset | Purpose |
| :--- | :--- |
| `skill_similarity_matrix` | Compute 7D pairwise similarity |
| `skill_clusters` | Group similar skills |
| `behavior_chains` | Detect usage sequences |
| `optimized_chains` | Optimize detected chains |
| `skill_state_space` | Build multi-dimensional representation |
| `evolution_trajectories` | Track skill movement over time |
| `unification_candidates` | Identify unification opportunities |
| `unified_skills` | Generate unified skill specs |
| `replacement_plans` | Create deprecation plans |
| `experience_patterns` | Mine patterns from usage |
| `emergent_capabilities` | Detect emergent behaviors |

### Jobs (jobs.py)

| Job | Assets |
| :--- | :--- |
| `skill_similarity_job` | similarity_matrix, clusters |
| `behavior_chain_job` | chains, optimized_chains |
| `state_space_job` | state_space, trajectories |
| `skill_unification_job` | candidates, unified_skills, plans |
| `experience_mining_job` | patterns, emergence |
| `full_evolution_pipeline_job` | All assets |

### Sensors (sensors.py)

| Sensor | Trigger Condition | Interval |
| :--- | :--- | :--- |
| `skill_similarity_sensor` | New/updated skills, 24h stale | 1h |
| `chain_optimization_sensor` | Experience accumulation | 2h |
| `unification_opportunity_sensor` | High-similarity clusters | 4h |
| `emergence_detection_sensor` | Pattern accumulation | 6h |
| `experience_threshold_sensor` | 100+ new experiences | 30m |
| `state_space_drift_sensor` | Significant skill movement | 2h |
| `unification_queue_sensor` | Approved candidates | 5m |
| `full_evolution_sensor` | Weekly schedule | 1h |

### Resources (resources.py)

| Resource | Purpose |
| :--- | :--- |
| `EvolutionConfigResource` | Pipeline configuration |
| `ExperienceStoreResource` | Usage experience storage |
| `ChainStoreResource` | Behavior chain storage |
| `StateSpaceStoreResource` | State space snapshots |
| `UnificationQueueResource` | Human approval workflow |
| `EvolutionMetricsResource` | Evolution analytics |

## Configuration

### Development (Lower thresholds, auto-approve)

```python
resources = create_dev_evolution_resources()
```

### Production (Conservative, human approval required)

```python
resources = create_prod_evolution_resources()
```

### Custom Configuration

```python
config = EvolutionConfigResource(
    evolution_strategy="balanced",           # conservative, balanced, aggressive, experimental
    similarity_threshold_for_clustering=0.7,
    similarity_threshold_for_unification=0.8,
    min_chain_occurrences=5,
    max_evolutions_per_day=3,
    require_human_approval_for_unification=True,
    deprecation_grace_period_days=30,
)
```

## Safety Mechanisms

1. **Risk Scoring** - Each unification assessed for risk/benefit
2. **Human Approval** - Configurable approval workflow
3. **Rate Limiting** - Max evolutions per day
4. **Rollback Windows** - Mandatory rollback period
5. **Deprecation Grace** - Time for users to migrate
6. **Validation Checks** - Pre-execution validation

## Integration with ESASS

The evolution system completes the meta-cognitive loop:

```text
Observations → Patterns → Skills → Usage Experiences → Evolution → Improved Skills
      ↑                                                                    │
      └────────────────────────────────────────────────────────────────────┘
```

Skills aren't just created—they're refined over time based on actual usage, forming a self-improving system.

---

## Ecosystem Dynamics & Advanced Emergence

### Ecosystem Perspective

**Key Insight**: Patterns exist in ecological relationships - not as isolated entities, but as components of a dynamic emergence ecosystem.

**Pattern Interaction Types**:
- **Symbiotic**: Patterns that enhance each other (e.g., debugging + documentation)
- **Competitive**: Patterns competing for same contexts
- **Predatory**: Powerful patterns suppressing emerging competitors
- **Mutualistic**: Bidirectional beneficial relationships
- **Niche-based**: Patterns dominating specific interaction contexts

**Ecosystem Metrics**:
- `keystone_importance`: How critical a pattern is to ecosystem stability (0-1)
- `niche_breadth`: Range of contexts where pattern is effective
- `ecosystem_stability_impact`: Pattern's effect on overall ecosystem health

### Proto-Patterns and Fossil Reconstruction

**Proto-Patterns**: Incomplete skill precursors showing potential but lacking full structure.

**Key Metrics**:
- `fossil_completeness`: % of expected skill structure observed (min 40%)
- `turbulence_score`: High entropy with positive outcomes (edge of chaos)
- `catalytic_factor`: Impact on enabling other patterns

**Emergence Phases**: Latent → Crystallizing → Stable

### Multi-Scale Dynamics

Skills emerge across three scales with cross-scale coupling:

| Scale | Examples | Metric |
|-------|----------|--------|
| Micro | Word choice, timing | Aggregates upward |
| Meso | Workflow structures | Bidirectional |
| Macro | Domain expertise | Constrains downward |

**Validation Requirement**: `cross_scale_coherence` ≥ 0.7

### Exploration Mechanisms

**Edge of Chaos Principle**: Most valuable skills emerge from transitional states.

**Strategies**:
1. **Anomaly Harvesting**: Seek rare (1-in-10,000) successful interactions
2. **Boundary Testing**: Probe capability limits
3. **Pattern Mutation**: Intentionally vary patterns to test robustness
4. **Fossil Reconstruction**: Complete incomplete patterns using Markov prediction

---

**See Also**: [CRITIQUE_SYNTHESIS.md](CRITIQUE_SYNTHESIS.md) for detailed integration guidance.
