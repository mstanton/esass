# ESASS Integration Plan: From Prototype to Production

**Status**: Planning Phase
**Version**: 1.0
**Date**: 2026-02-01

## Executive Summary

This document outlines the strategy for integrating ESASS with Claude Code's actual execution environment, transitioning from simulated event data to real-time capture of reasoning, tool usage, and decision-making patterns.

---

## 1. Current Implementation Review

### 1.1 What Exists

The prototype has achieved significant progress with the following components:

#### **Core Data Models** (`esass_prototype/models.py`)
- ✅ `LogEntry`: Event capture with causality tracking
- ✅ `PatternDefinition`: Temporal pattern representation with quality metrics
- ✅ `SkillManifest`: Complete skill specifications
- ✅ `TriggerCondition`: Skill activation logic
- ✅ Factory functions for creating typed events (reasoning, tool_usage, decision)

#### **Observation System** (`esass_prototype/observation/`)
- ✅ `EventSimulator`: Generates 5 realistic scenario types (git, code analysis, bug fix, docs, tests)
- ✅ `ObservationLogger`: Persists events to storage with state tracking
- ⚠️  **GAP**: Currently simulation-based, not capturing real Claude Code events

#### **Storage Layer** (`esass_prototype/storage/`)
- ✅ `LogStore`: JSONL-based event storage with date-based partitioning
- ✅ `PatternStore`: JSON-based pattern persistence
- ✅ `SkillStore`: Versioned skill registry
- ⚠️  **GAP**: File-based storage sufficient for prototype but needs database backends for production scale

#### **Pattern Recognition** (`esass_prototype/analysis/`)
- ✅ `TemporalPatternDetector`: Sequential pattern mining with support/confidence metrics
- ✅ `MetricsCalculator`: Pattern quality assessment
- ⚠️  **GAP**: Missing semantic and behavioral pattern detection (only temporal implemented)

#### **Skill Genesis** (`esass_prototype/genesis/`)
- ✅ `CandidacyEvaluator`: Filters patterns using specification thresholds
- ✅ `SkillTemplateGenerator`: Transforms patterns into skill manifests
- ✅ Validation pipeline (basic)

#### **Export System** (`esass_prototype/export/`)
- ✅ `ObsidianExporter`: Generates interconnected markdown documentation
- ✅ Pattern visualization and skill lineage tracking

#### **Orchestration** (`sensors.py`)
- ✅ Dagster-based monitoring sensors for evolution triggers
- ✅ 8 specialized sensors (similarity, chains, unification, emergence, etc.)
- ⚠️  **GAP**: Not integrated with actual skill execution or feedback loops

### 1.2 What's Missing for Real System Integration

| Component | Status | Priority | Complexity |
|-----------|--------|----------|------------|
| **Real Event Capture** | Missing | P0 | High |
| **Claude Code Hook Integration** | Missing | P0 | High |
| **Vector Database** | Missing | P1 | Medium |
| **Graph Database** | Missing | P1 | Medium |
| **Semantic Pattern Detection** | Missing | P1 | High |
| **Behavioral Pattern Detection** | Missing | P2 | Medium |
| **Evolution State Space Tracking** | Missing | P2 | High |
| **Skill Execution Framework** | Missing | P0 | High |
| **Human Approval Workflow** | Missing | P1 | Medium |
| **Rollback Mechanisms** | Missing | P1 | Medium |

---

## 2. Claude Code Integration Architecture

### 2.1 Event Capture Strategy

Claude Code exposes its execution flow through several touchpoints that ESASS can observe:

#### **A. Tool Call Interception**

Claude Code processes tool calls through a well-defined pipeline. ESASS can hook into this pipeline to capture:

```python
class ESASSToolCallObserver:
    """
    Observer that hooks into Claude Code's tool call pipeline.

    Captures:
    - Tool invocations (Read, Write, Bash, etc.)
    - Parameters passed
    - Tool results
    - Execution timing
    """

    def __init__(self, logger: ObservationLogger):
        self.logger = logger
        self.current_session_id = None
        self.call_stack = []  # Track causality

    def on_tool_call_start(self, tool_name: str, parameters: dict, context: dict):
        """Capture tool call initiation"""
        session_id = context.get('conversation_id', str(uuid4()))

        # Create tool usage event
        event = create_tool_usage_event(
            tool_name=tool_name,
            parameters=parameters,
            outcome_assessment="pending",
            session_id=session_id,
            caused_by=self.call_stack[-1] if self.call_stack else None,
            tags=self._extract_tags(tool_name, parameters)
        )

        self.logger.log(event)
        self.call_stack.append(event.event_id)
        return event.event_id

    def on_tool_call_complete(self, call_id: str, result: any, success: bool):
        """Update tool call with outcome"""
        # Update log entry with outcome assessment
        outcome = "success" if success else "failure"
        # Implementation would update the existing event
        self.call_stack.pop()

    def _extract_tags(self, tool_name: str, parameters: dict) -> List[str]:
        """Extract semantic tags from tool usage"""
        tags = [tool_name.lower()]

        # Extract context from parameters
        if tool_name == "Read":
            # Extract file type, directory context
            file_path = parameters.get('file_path', '')
            if '.py' in file_path:
                tags.append('python')
            if 'test' in file_path.lower():
                tags.append('testing')

        elif tool_name == "Bash":
            # Extract command intent
            command = parameters.get('command', '')
            if 'git' in command:
                tags.extend(['git', 'version_control'])
            if 'pytest' in command or 'test' in command:
                tags.append('testing')

        return tags
```

#### **B. Reasoning Chain Capture**

Claude Code's thinking process can be captured by observing:
- Message content analysis
- Decision points (when EnterPlanMode is considered)
- AskUserQuestion invocations

```python
class ESASSReasoningObserver:
    """
    Captures Claude's reasoning process.

    Extracts:
    - Hypotheses formed
    - Alternatives considered
    - Confidence levels (inferred from language)
    """

    def on_message_generated(self, message: str, context: dict):
        """Analyze message for reasoning patterns"""
        session_id = context['conversation_id']

        # Extract reasoning indicators
        if self._contains_hypothesis(message):
            reasoning = self._extract_reasoning(message)
            event = create_reasoning_event(
                statement=reasoning['statement'],
                confidence=reasoning['confidence'],
                evidence=reasoning['evidence'],
                session_id=session_id,
                tags=reasoning['tags']
            )
            self.logger.log(event)

    def _contains_hypothesis(self, message: str) -> bool:
        """Detect if message contains reasoning"""
        indicators = [
            "I think", "likely", "probably", "appears to",
            "suggests that", "indicates", "seems to"
        ]
        return any(ind in message.lower() for ind in indicators)
```

#### **C. Decision Point Tracking**

Track when Claude makes explicit decisions:

```python
class ESASSDecisionObserver:
    """
    Captures decision-making events.
    """

    def on_tool_selection(self, selected_tool: str, alternatives: List[str],
                          rationale: str, context: dict):
        """Log tool selection decisions"""
        event = create_decision_event(
            decision=f"use_{selected_tool}",
            confidence=self._estimate_confidence(rationale),
            options_considered=alternatives,
            rationale=rationale,
            session_id=context['conversation_id'],
            tags=['tool_selection', selected_tool]
        )
        self.logger.log(event)
```

### 2.2 Integration Points in Claude Code

ESASS needs to hook into these Claude Code lifecycle events:

| Hook Point | Purpose | Implementation Method |
|------------|---------|----------------------|
| **Conversation Start** | Initialize session tracking | Hook into conversation manager |
| **Tool Invocation** | Capture tool usage patterns | Wrap tool execution pipeline |
| **Message Generation** | Extract reasoning chains | Post-processing hook |
| **Decision Points** | Track choice rationale | Observer pattern on decision logic |
| **Task Completion** | Session boundary detection | Conversation end hook |
| **Error Events** | Capture failure patterns | Exception handler integration |

### 2.3 Proposed Hook Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Code Core                         │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │ Conversation │───▶│ Tool Pipeline │───▶│ Response Gen │ │
│  │   Manager    │    │              │    │              │ │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘ │
│         │                   │                   │          │
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
                   └──────┬───────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
         ┌────────┐  ┌────────┐  ┌─────────┐
         │ Logger │  │ Buffer │  │ Filters │
         └────┬───┘  └────┬───┘  └────┬────┘
              │           │           │
              └───────────┼───────────┘
                          ▼
                   ┌──────────────┐
                   │  Log Store   │
                   └──────────────┘
```

### 2.4 Implementation Phases

#### **Phase 1: Basic Event Capture (Weeks 1-2)**
- [ ] Create probe interface definition
- [ ] Implement tool call observer
- [ ] Hook into Claude Code tool pipeline
- [ ] Log events to existing LogStore
- [ ] Verify event capture with real interactions

#### **Phase 2: Rich Context Extraction (Weeks 3-4)**
- [ ] Implement reasoning chain extraction
- [ ] Add decision point tracking
- [ ] Enhance tag extraction logic
- [ ] Capture file context (paths, types, purposes)
- [ ] Add temporal relationship tracking

#### **Phase 3: Real-Time Pattern Detection (Weeks 5-6)**
- [ ] Streaming pattern detector
- [ ] Incremental support/confidence updates
- [ ] Session-scoped pattern recognition
- [ ] Pattern candidate notification system

#### **Phase 4: Closed-Loop Learning (Weeks 7-8)**
- [ ] Skill execution framework
- [ ] Outcome tracking (success/failure)
- [ ] Skill effectiveness metrics
- [ ] Feedback loop to pattern detector

---

## 3. Gap Analysis: Prototype vs. Production

### 3.1 Architectural Gaps

#### **Database Infrastructure**

**Current**: File-based JSON/JSONL storage
**Required**:
- **Time-series DB** (InfluxDB, TimescaleDB) for event logs
- **Graph DB** (Neo4j, ArangoDB) for pattern relationships
- **Vector DB** (Pinecone, Weaviate, Milvus) for semantic embeddings

**Migration Path**:
1. Create database abstraction layer with interfaces
2. Implement file-based backend (current)
3. Implement database backends in parallel
4. Add configuration to switch between backends
5. Migration tool to transfer file data to databases

```python
# Proposed abstraction
class LogStoreInterface(ABC):
    @abstractmethod
    def save(self, entry: LogEntry) -> None: ...

    @abstractmethod
    def query(self, filters: dict) -> List[LogEntry]: ...

class FileLogStore(LogStoreInterface):
    """Current implementation"""
    pass

class TimeSeriesLogStore(LogStoreInterface):
    """Production implementation using TimescaleDB"""
    pass
```

#### **Semantic Pattern Detection**

**Current**: Only temporal pattern detection
**Required**:
- LDA topic modeling for semantic clustering
- Embedding-based similarity (BERT, sentence-transformers)
- Concept drift detection

**Implementation**:
```python
class SemanticPatternDetector:
    """
    Detect semantic patterns using embeddings and clustering.
    """

    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(embedding_model)

    def detect_patterns(self, logs: List[LogEntry]) -> List[PatternDefinition]:
        # Extract event descriptions
        descriptions = [
            self._event_to_text(log) for log in logs
        ]

        # Generate embeddings
        embeddings = self.model.encode(descriptions)

        # Cluster similar events
        from sklearn.cluster import HDBSCAN
        clusterer = HDBSCAN(min_cluster_size=5)
        labels = clusterer.fit_predict(embeddings)

        # Create pattern definitions from clusters
        patterns = []
        for cluster_id in set(labels):
            if cluster_id == -1:  # Noise cluster
                continue

            cluster_logs = [log for i, log in enumerate(logs)
                           if labels[i] == cluster_id]

            pattern = self._create_semantic_pattern(cluster_logs)
            patterns.append(pattern)

        return patterns
```

#### **Skill Execution Framework**

**Current**: Skills are generated but not executed
**Required**:
- Skill invocation system
- Parameter binding from context
- Outcome tracking
- Success/failure metrics

**Design**:
```python
class SkillExecutor:
    """
    Executes skills and tracks outcomes for learning feedback.
    """

    def execute_skill(self, skill: SkillManifest, context: dict) -> SkillOutcome:
        """
        Execute a skill in the given context.

        Returns outcome with success metrics for feedback loop.
        """
        # Validate trigger conditions
        if not self._should_activate(skill, context):
            return SkillOutcome(activated=False)

        # Bind parameters from context
        params = self._bind_parameters(skill, context)

        # Execute implementation
        try:
            result = self._run_implementation(skill, params)
            outcome = SkillOutcome(
                activated=True,
                success=True,
                result=result,
                execution_time=...
            )
        except Exception as e:
            outcome = SkillOutcome(
                activated=True,
                success=False,
                error=str(e)
            )

        # Log outcome for learning
        self._log_skill_usage(skill, outcome, context)

        return outcome
```

### 3.2 Performance Gaps

| Metric | Prototype | Target | Gap |
|--------|-----------|--------|-----|
| Event capture latency | N/A (simulated) | <10ms | Need real-time hooks |
| Pattern detection cycle | Manual trigger | <5 min | Need streaming detector |
| Storage throughput | ~100 events/sec | ~1000 events/sec | Need database backend |
| Query latency (simple) | ~50ms (file scan) | <100ms | Need indexing |
| Query latency (complex) | N/A | <1s | Need graph DB |

### 3.3 Safety Gaps

**Current Safety Measures**:
- Basic validation in skill generation
- Human-readable output for review

**Required Safety Measures**:
- [ ] **Validation Pipeline**: Multi-stage checks before skill activation
- [ ] **Human Approval Workflow**: Queue system for unifications and new skills
- [ ] **Rate Limiting**: max_evolutions_per_day enforcement
- [ ] **Rollback System**: Version tracking and skill deactivation
- [ ] **Audit Trail**: All evolution decisions logged with rationale
- [ ] **Safety Constraints**: Forbidden pattern detection (manipulation, deception)
- [ ] **Sandbox Execution**: Test skills in isolated environment first

---

## 4. Optimization Recommendations

### 4.1 Code Refactoring

#### **A. Unify Storage Interface**

**Problem**: Each store (log, pattern, skill) has different interfaces
**Solution**: Create unified repository pattern

```python
# Current
log_store.save(entry)
pattern_store.save_pattern(pattern)
skill_store.store_skill(skill)

# Proposed
from esass_prototype.storage import Repository

repo = Repository(config)
repo.logs.save(entry)
repo.patterns.save(pattern)
repo.skills.save(skill)
```

#### **B. Event Factory Consolidation**

**Problem**: Multiple create_*_event functions with similar logic
**Solution**: Single factory with event type dispatch

```python
class EventFactory:
    """Unified event creation"""

    @staticmethod
    def create(event_type: EventType, **kwargs) -> LogEntry:
        """Create any event type with unified interface"""
        creators = {
            EventType.REASONING: EventFactory._create_reasoning,
            EventType.TOOL_USAGE: EventFactory._create_tool_usage,
            EventType.DECISION: EventFactory._create_decision,
        }
        return creators[event_type](**kwargs)
```

#### **C. Configuration Management**

**Problem**: Hardcoded thresholds scattered across files
**Solution**: Centralized config with environment overrides

```python
# esass_prototype/config.py enhancements
class ESASSConfig:
    def __init__(self):
        # Load from environment variables
        self.pattern_detection = PatternDetectionConfig(
            min_support=int(os.getenv('ESASS_MIN_SUPPORT', 10)),
            min_confidence=float(os.getenv('ESASS_MIN_CONFIDENCE', 0.8)),
            # ...
        )

    @classmethod
    def from_file(cls, path: Path) -> 'ESASSConfig':
        """Load from YAML/TOML config file"""
        pass
```

### 4.2 Performance Optimizations

#### **A. Event Buffering**

**Problem**: Each event written individually to disk
**Solution**: Batch writes with configurable flush interval

```python
class BufferedLogStore(LogStore):
    """
    Log store with write buffering for performance.
    """

    def __init__(self, data_dir: Path, buffer_size: int = 100,
                 flush_interval: int = 5):
        super().__init__(data_dir)
        self.buffer = []
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self._start_flush_timer()

    def save(self, entry: LogEntry):
        self.buffer.append(entry)
        if len(self.buffer) >= self.buffer_size:
            self.flush()

    def flush(self):
        if self.buffer:
            self.save_many(self.buffer)
            self.buffer.clear()
```

#### **B. Pattern Detection Optimization**

**Problem**: Full log scan on each detection run
**Solution**: Incremental pattern mining with windowing

```python
class IncrementalPatternDetector(TemporalPatternDetector):
    """
    Incremental pattern detection using sliding window.
    """

    def __init__(self, window_days: int = 7):
        super().__init__()
        self.window_days = window_days
        self.last_processed = None

    def detect_patterns(self, logs: List[LogEntry]) -> List[PatternDefinition]:
        # Only process events since last run
        if self.last_processed:
            logs = [log for log in logs
                   if log.timestamp > self.last_processed]

        # Update existing patterns incrementally
        new_patterns = super().detect_patterns(logs)

        self.last_processed = datetime.utcnow().isoformat()
        return new_patterns
```

#### **C. Add Caching Layer**

**Problem**: Repeated queries for same data
**Solution**: LRU cache for frequently accessed patterns/skills

```python
from functools import lru_cache

class CachedPatternStore(PatternStore):
    @lru_cache(maxsize=128)
    def load_pattern(self, pattern_id: str) -> PatternDefinition:
        return super().load_pattern(pattern_id)
```

### 4.3 Code Quality Improvements

#### **A. Add Type Hints Everywhere**

Current coverage: ~60%
Target: 100% with mypy strict mode

```python
# Before
def detect_patterns(self, logs):
    ...

# After
def detect_patterns(self, logs: List[LogEntry]) -> List[PatternDefinition]:
    ...
```

#### **B. Enhanced Error Handling**

```python
class ESASSError(Exception):
    """Base exception for ESASS"""
    pass

class EventCaptureError(ESASSError):
    """Failed to capture event"""
    pass

class PatternDetectionError(ESASSError):
    """Pattern detection failed"""
    pass

# Usage
try:
    patterns = detector.detect_patterns(logs)
except PatternDetectionError as e:
    logger.error(f"Pattern detection failed: {e}")
    # Fallback behavior
```

#### **C. Add Comprehensive Logging**

```python
import structlog

logger = structlog.get_logger()

class PatternDetector:
    def detect_patterns(self, logs: List[LogEntry]) -> List[PatternDefinition]:
        logger.info("pattern_detection.start", event_count=len(logs))

        try:
            patterns = self._mine_patterns(logs)
            logger.info("pattern_detection.complete",
                       pattern_count=len(patterns),
                       candidates=sum(1 for p in patterns if p.skill_candidate))
            return patterns
        except Exception as e:
            logger.error("pattern_detection.failed", error=str(e))
            raise
```

### 4.4 Testing Infrastructure

**Current**: No tests
**Required**:

1. **Unit Tests**: Each module >80% coverage
2. **Integration Tests**: End-to-end pipeline tests
3. **Performance Tests**: Benchmark pattern detection on large datasets
4. **Safety Tests**: Validate forbidden pattern detection

```bash
# Target test structure
tests/
├── unit/
│   ├── test_models.py
│   ├── test_pattern_detector.py
│   ├── test_skill_generator.py
│   └── test_storage.py
├── integration/
│   ├── test_pipeline.py
│   ├── test_evolution_cycle.py
│   └── test_export.py
├── performance/
│   ├── test_event_throughput.py
│   └── test_pattern_detection_scaling.py
└── safety/
    ├── test_validation_pipeline.py
    └── test_forbidden_patterns.py
```

---

## 5. Migration Roadmap

### Phase 1: Foundation (Weeks 1-4)
**Goal**: Establish real event capture

- [ ] Design probe interface specification
- [ ] Implement tool call observer
- [ ] Hook into Claude Code tool pipeline
- [ ] Verify event capture with manual testing
- [ ] Add comprehensive logging
- [ ] Set up testing infrastructure

**Deliverables**:
- Working event capture from Claude Code interactions
- Test suite with >70% coverage
- Performance benchmarks

### Phase 2: Pattern Enhancement (Weeks 5-8)
**Goal**: Add missing pattern detection capabilities

- [ ] Implement semantic pattern detector
- [ ] Add behavioral pattern detection
- [ ] Create incremental pattern mining
- [ ] Integrate vector database for embeddings
- [ ] Build pattern visualization dashboard

**Deliverables**:
- Multi-dimensional pattern detection
- Real-time pattern updates
- Pattern quality metrics dashboard

### Phase 3: Skill Lifecycle (Weeks 9-14)
**Goal**: Complete skill generation and execution loop

- [ ] Build skill execution framework
- [ ] Implement outcome tracking
- [ ] Create human approval workflow UI
- [ ] Add rollback mechanisms
- [ ] Build skill effectiveness dashboard

**Deliverables**:
- Executable skills with feedback loop
- Approval queue system
- Skill performance metrics

### Phase 4: Evolution System (Weeks 15-20)
**Goal**: Enable autonomous skill evolution

- [ ] Implement similarity analysis
- [ ] Build behavior chain optimizer
- [ ] Create state space tracking
- [ ] Implement skill unification engine
- [ ] Add emergence detection

**Deliverables**:
- Full evolution pipeline operational
- Unification recommendations with approval flow
- Emergence detection alerts

### Phase 5: Production Hardening (Weeks 21-26)
**Goal**: Production-ready deployment

- [ ] Database migration tools
- [ ] Comprehensive safety validation
- [ ] Performance optimization (target metrics met)
- [ ] Security audit
- [ ] Documentation completion
- [ ] Deployment automation

**Deliverables**:
- Production deployment
- Operations runbooks
- User documentation
- Monitoring dashboards

---

## 6. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Claude Code API changes** | High | Medium | Version pinning, abstraction layer |
| **Performance degradation** | High | Medium | Extensive benchmarking, async processing |
| **Unsafe skill generation** | Critical | Low | Multi-stage validation, human approval |
| **Database scaling issues** | Medium | Medium | Horizontal sharding, retention policies |
| **Integration complexity** | High | High | Phased rollout, feature flags |
| **Data privacy concerns** | High | Low | PII filtering, opt-out mechanisms |

---

## 7. Success Metrics

| Metric | Baseline | Target (6 months) |
|--------|----------|------------------|
| Events captured/day | 0 | 10,000+ |
| Pattern detection accuracy | N/A | >85% precision |
| Skill generation rate | 0 | 5-10/week |
| Validated skills in production | 0 | 20+ |
| Skill success rate | N/A | >70% |
| Evolution cycles completed | 0 | 50+ |
| User approval rate for unifications | N/A | >60% |

---

## 8. Next Actions

### Immediate (This Week)
1. ✅ Complete this integration plan
2. [ ] Review plan with stakeholders
3. [ ] Set up development environment for Claude Code integration
4. [ ] Design probe interface specification (detailed)
5. [ ] Create proof-of-concept tool call observer

### Short-term (Next 2 Weeks)
1. [ ] Implement basic event capture
2. [ ] Add integration tests
3. [ ] Validate event quality with real interactions
4. [ ] Begin database abstraction layer
5. [ ] Start semantic pattern detector implementation

### Medium-term (Next Month)
1. [ ] Complete Phase 1 deliverables
2. [ ] Begin Phase 2 (pattern enhancement)
3. [ ] Establish performance benchmarks
4. [ ] Create monitoring infrastructure

---

## Appendix A: Integration Code Examples

### A.1 Probe Registration System

```python
# esass/integration/probes.py

from abc import ABC, abstractmethod
from typing import Any, Dict

class Probe(ABC):
    """Base class for all ESASS probes"""

    @abstractmethod
    def observe(self, event: dict) -> Optional[LogEntry]:
        """Process an event and optionally return a log entry"""
        pass

class ProbeRegistry:
    """Central registry for all probes"""

    def __init__(self):
        self.probes: List[Probe] = []

    def register(self, probe: Probe):
        """Register a new probe"""
        self.probes.append(probe)

    def notify(self, event_type: str, event_data: dict):
        """Notify all probes of an event"""
        for probe in self.probes:
            try:
                log_entry = probe.observe({
                    'type': event_type,
                    'data': event_data
                })
                if log_entry:
                    # Send to logging pipeline
                    pass
            except Exception as e:
                logger.error(f"Probe {probe} failed", error=str(e))

# Global registry
registry = ProbeRegistry()

# Register probes
registry.register(ToolCallProbe())
registry.register(ReasoningProbe())
registry.register(DecisionProbe())
```

### A.2 Claude Code Hook Points

```python
# Proposed integration in Claude Code

# In tool execution pipeline:
def execute_tool(tool_name: str, parameters: dict, context: dict) -> Any:
    # ESASS HOOK: Before execution
    esass.registry.notify('tool_call_start', {
        'tool_name': tool_name,
        'parameters': parameters,
        'context': context
    })

    try:
        result = _actual_tool_execution(tool_name, parameters)

        # ESASS HOOK: After success
        esass.registry.notify('tool_call_complete', {
            'tool_name': tool_name,
            'result': result,
            'success': True
        })

        return result
    except Exception as e:
        # ESASS HOOK: After failure
        esass.registry.notify('tool_call_error', {
            'tool_name': tool_name,
            'error': str(e)
        })
        raise
```

---

**Document Status**: Draft for Review
**Next Review**: After stakeholder feedback
**Owner**: ESASS Development Team
