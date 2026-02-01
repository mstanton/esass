# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ESASS (Emergent Self-Adaptive Skill System)** is a meta-cognitive architecture that enables AI skills to achieve operational self-awareness through comprehensive observation, documentation, and pattern extraction from execution contexts. The system transforms implicit usage patterns into explicit, composable skill definitions.

**Status**: Early development - specification-complete, implementation in progress

**Core Technology Stack**:
- Python 3.x
- Graph database (for pattern relationships)
- Vector database (for semantic embeddings)
- Time-series database (for observation logs)

## Build and Test Commands

**Current Status**: Build system and test framework to be established.

### Setup

```bash
# Install dependencies (once requirements.txt or pyproject.toml exists)
pip install -r requirements.txt
# or
pip install -e ".[dev]"
```

### Testing

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=esass --cov-report=html

# Run specific test module
pytest tests/test_pattern_recognition.py

# Run tests matching a pattern
pytest -k "test_similarity"

# Run type checking
mypy esass/
```

### Linting and Formatting

```bash
# Format code
black esass/ tests/

# Lint code
ruff check esass/

# Sort imports
isort esass/ tests/
```

## Key Architectural Concepts

### The Meta-Cognitive Loop

ESASS implements a continuous learning cycle:

```
Observations → Logging → Pattern Recognition → Skill Genesis → Evolution → Improved Skills
      ↑                                                                          │
      └──────────────────────────────────────────────────────────────────────────┘
```

### Core Subsystems (from ARCHITECTURE.md)

1. **Observation Probe Network (OPN)**: Captures execution context across 6 probe types (input, reasoning, tool, output, context, temporal)

2. **Logging Pipeline (LP)**: Transforms raw observations into structured, queryable records with 5 log levels (L0-TRACE to L4-INSIGHT)

3. **Pattern Recognition Engine (PRE)**: Identifies recurring structures across 4 dimensions:
   - Temporal patterns (sequences, cycles)
   - Structural patterns (tool combinations, workflows)
   - Semantic patterns (conceptual clustering)
   - Behavioral patterns (response styles, decision tendencies)

4. **Skill Genesis Engine (SGE)**: Transforms validated patterns into executable skills through:
   - Pattern clustering → Template generation → Validation → Human review

5. **Skill Evolution System**: Meta-learning capabilities including:
   - Similarity-based skill consolidation (7-dimensional similarity)
   - Behavior chain optimization (5 optimization types)
   - Experience-based emergence detection
   - Lifecycle management (nascent → growing → mature → deprecated)

6. **Self-Documentation Substrate (SDS)**: Auto-generates skill manifests, decision journals, evolution timelines

### Evolution System Components

The evolution system implements meta-learning through:

**Similarity Analysis**:
- Compute 7-dimensional skill similarity matrices
- Cluster similar skills for consolidation opportunities
- Track similarity trends over time

**Behavior Chain Analysis**:
- Detect recurring skill usage sequences
- Identify optimization opportunities (collapse, parallelize, shortcut, cache, specialize)
- Build optimized composite skills from chains

**State Space Tracking**:
- Multi-dimensional skill positioning (semantic, performance, evolution coords)
- Fitness tracking across lifecycle states
- Evolution trajectory analysis

**Skill Unification**:
- Identify unification candidates from high-similarity clusters
- Generate unified skill specifications
- Create replacement/migration plans with deprecation timelines

**Experience Mining**:
- Extract patterns from usage experiences
- Detect emergent capabilities (novel combinations, context generalization, failure adaptation)
- Mine success conditions, failure modes, optimization opportunities

### Skill Unification Methods

Five unification strategies (from ARCHITECTURE.md):
- **ABSORB**: Dominant skill absorbs similar ones
- **MERGE**: Create new skill from both
- **PARAMETERIZE**: Single skill with parameters
- **COMPOSE**: Hierarchical composition
- **GENERALIZE**: Extract common abstraction

### Data Model Key Entities

All defined in TypeScript interfaces in specification (§3 of esass-specification_v0.01.md):
- `ObservationRecord` - Captured execution events with semantic embeddings
- `PatternDefinition` - Recurring structures with confidence/support metrics
- `SkillManifest` - Complete skill specifications with lineage, validation, auto-documentation
- `LogEntry` - Structured events with causality chains and anomaly scoring

## Development Workflow

### Current State (Early Development)

The repository contains:
- Complete specifications (esass-specification_v0.01.md - 1271 lines)
- Architecture documentation (ARCHITECTURE.md)
- Initial implementation: `sensors.py` (monitoring/trigger logic)
- **Build system, tests, and core infrastructure in progress**

### Expected Implementation Pattern

Based on specifications, the full system will require:

1. **Logging Infrastructure** (§4 of specification):
   - Append-only time-series database
   - 5-level log retention (24h to permanent)
   - Query API supporting causal, temporal, semantic searches

2. **Storage Layer**:
   - Graph database for pattern relationships
   - Vector database for semantic embeddings (1536-dim)
   - Versioned document store for skills

3. **Pattern Recognition** (§5 of specification):
   - Sequential pattern mining (GSP, PrefixSpan)
   - Subgraph mining for workflows
   - Topic modeling (LDA) for semantic patterns
   - Embedding clustering (HDBSCAN)

4. **Module Structure**:
   ```
   esass/
   ├── observation/
   │   ├── probes.py           # 6 probe types
   │   └── logging.py          # Logging pipeline
   ├── storage/
   │   ├── log_store.py        # Time-series log storage
   │   ├── pattern_store.py    # Graph database for patterns
   │   └── skill_store.py      # Versioned skill registry
   ├── patterns/
   │   ├── temporal.py         # Temporal pattern detection
   │   ├── structural.py       # Structural pattern detection
   │   ├── semantic.py         # Semantic pattern detection
   │   └── behavioral.py       # Behavioral pattern detection
   ├── genesis/
   │   ├── candidate.py        # Pattern candidacy evaluation
   │   ├── template.py         # Skill template generation
   │   └── validation.py       # Validation pipeline
   ├── evolution/
   │   ├── similarity.py       # 7-dimensional similarity
   │   ├── chains.py           # Behavior chain analysis
   │   ├── state_space.py      # State space tracking
   │   ├── unification.py      # Skill unification
   │   └── emergence.py        # Emergence detection
   └── documentation/
       ├── manifest.py         # Skill manifest generation
       ├── journal.py          # Decision journal
       └── timeline.py         # Evolution timeline
   ```

### When Working on New Code

1. **Follow the Specification**: All design decisions documented in esass-specification_v0.01.md and ARCHITECTURE.md

2. **Module Organization**: Use the structure outlined in ARCHITECTURE.md §2.6:
   - Separate concerns: models, assets, jobs, resources, sensors
   - 40+ data models needed (see ARCHITECTURE.md for list)

3. **Safety First**: The system has strict safety requirements (§6.4 of spec):
   - All skill generation requires validation pipeline
   - Human approval workflow for unifications
   - Rate limiting (max_evolutions_per_day)
   - Rollback capabilities mandatory

4. **Transparency Principle** (§1.1 of spec):
   - All decisions must be logged with rationale
   - No "black box" transformations
   - Every adaptation is documented

## Configuration

Two environment modes planned:

**Development**:
```python
config = EvolutionConfig(
    evolution_strategy="experimental",
    auto_approve_unifications=True,
    # Lower thresholds for testing
)
```

**Production**:
```python
config = EvolutionConfig(
    evolution_strategy="conservative",
    require_human_approval=True,
    # Conservative thresholds
)
```

Configuration parameters:
- `evolution_strategy`: conservative | balanced | aggressive | experimental
- `similarity_threshold_for_clustering`: 0.7 (default)
- `similarity_threshold_for_unification`: 0.8 (default)
- `min_chain_occurrences`: 5
- `max_evolutions_per_day`: 3
- `require_human_approval_for_unification`: true (production)
- `deprecation_grace_period_days`: 30

## Important Design Constraints

### Ethical Boundaries (§12 of specification)

1. **Transparency Commitments**:
   - Users can see what system learned about them
   - System can explain any decision
   - All learning is logged and auditable
   - Users can opt-out of learning features

2. **Forbidden Behaviors**:
   - No manipulation skills
   - No deceptive capabilities
   - Patterns correlating with harm are flagged, not promoted
   - Skill generation bounded by value constraints

### Performance Targets (§10.2 of specification)

- Observation latency: <10ms
- Query latency (simple): <100ms
- Query latency (complex): <1s
- Pattern detection cycle: <5 min
- Skill generation cycle: <1 hour
- Documentation update: <1 hour

### Storage Estimates (§10.3)

For 1000 conversations/day × 20 messages:
- Total: ~130 GB/year (before compression)
- L0 (TRACE): 10 GB rolling
- L1 (DEBUG): 14 GB (7-day retention)
- L2 (INFO): 45 GB (90-day retention)
- Patterns: 36 GB
- Skills: 4 GB

## Pattern Candidacy Criteria

A pattern becomes a skill candidate when (§6.2 of specification):
- **min_support**: ≥10 instances
- **min_confidence**: ≥0.8
- **min_stability_period**: ≥7 days
- **min_coherence**: ≥0.7
- **min_user_value_correlation**: ≥0.6
- **outcome_improvement**: statistically significant (p < 0.05)
- **no_harmful_outcomes**: true
- **reversible_actions_only**: true (for auto-activated skills)

## Skill Lifecycle States

From ARCHITECTURE.md data flow section:

```
NASCENT → GROWING → MATURE → CANDIDATE → EVOLVING
                                ↓
                    DEPRECATED → ARCHIVED or MERGED
```

## Similarity Dimensions

Skills are compared across 7 dimensions (ARCHITECTURE.md):
1. Semantic similarity
2. Behavioral similarity
3. Trigger pattern similarity
4. Output similarity
5. Structural similarity
6. Contextual similarity
7. Temporal similarity

## Implementation Phases (§9 of specification)

Six planned phases (30 weeks total):
1. **Foundation** (Weeks 1-4): Logging infrastructure
2. **Pattern Recognition** (Weeks 5-8): 4-dimensional detection
3. **Skill Genesis** (Weeks 9-14): Template generation & validation
4. **Self-Documentation** (Weeks 15-18): Auto-documentation system
5. **Adaptive Learning** (Weeks 19-24): Continuous adaptation loop
6. **Integration & Hardening** (Weeks 25-30): Production deployment

## Related Concepts

The specification references several research areas (Appendix B):
- Meta-learning systems (MAML)
- Neural architecture search
- Program synthesis from examples
- Cognitive architectures (SOAR, ACT-R)
- Reflective programming

## Current Implementation: sensors.py

The initial implementation file provides monitoring and trigger logic for the evolution system. It implements condition-based triggering for various evolution processes:

- **Similarity monitoring**: Detects when skills need similarity recomputation (new/updated skills, staleness)
- **Chain optimization**: Monitors for behavior pattern accumulation warranting optimization
- **Unification opportunities**: Identifies high-similarity clusters for skill consolidation
- **Emergence detection**: Scans for emergent capabilities from experience patterns
- **Experience thresholds**: Triggers analysis when sufficient new experiences accumulate
- **State space drift**: Detects significant skill movement in state space

Monitoring intervals range from 5 minutes (queue processing) to weekly (full pipeline runs). The system uses state persistence to track last run times and accumulated metrics between evaluations.
