# ESASS Skill Evolution System

## Overview

The Skill Evolution System provides meta-learning capabilities for ESASS, enabling:

- **Automatic skill consolidation** - Similar skills unified into more powerful ones
- **Behavior chain optimization** - Frequent sequences crystallized into composite skills
- **Experience-based learning** - Emergent capabilities discovered from usage patterns
- **Lifecycle management** - Skills evolve through nascent → growing → mature → deprecated

## Architecture

```
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

## Data Flow

### 1. Similarity Computation

```
Active Skills → Embedding → 7D Similarity Matrix → Skill Clusters
```

### 2. Behavior Chain Discovery

```
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

```
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

```
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

```
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
|----------|-------|
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
|-------|---------|
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
|-----|--------|
| `skill_similarity_job` | similarity_matrix, clusters |
| `behavior_chain_job` | chains, optimized_chains |
| `state_space_job` | state_space, trajectories |
| `skill_unification_job` | candidates, unified_skills, plans |
| `experience_mining_job` | patterns, emergence |
| `full_evolution_pipeline_job` | All assets |

### Sensors (sensors.py)

| Sensor | Trigger Condition | Interval |
|--------|-------------------|----------|
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
|----------|---------|
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

```
Observations → Patterns → Skills → Usage Experiences → Evolution → Improved Skills
      ↑                                                                    │
      └────────────────────────────────────────────────────────────────────┘
```

Skills aren't just created—they're refined over time based on actual usage, forming a self-improving system.
