# ESASS × OpenClaw: Explorable Documentation

## Interactive Architecture Explorer

This document provides deep dives into each component of the recursive skill learning loop.

---

## 🗺️ System Map

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        RECURSIVE SKILL EVOLUTION SYSTEM                        ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║    ┌─────────────────────────────────────────────────────────────────────┐   ║
║    │                         USER INTERACTIONS                            │   ║
║    │   WhatsApp │ Telegram │ Discord │ iMessage │ Web │ CLI              │   ║
║    └──────────────────────────────┬──────────────────────────────────────┘   ║
║                                   │                                          ║
║                                   ▼                                          ║
║    ┌─────────────────────────────────────────────────────────────────────┐   ║
║    │                         OPENCLAW GATEWAY                             │   ║
║    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐               │   ║
║    │  │ Channel │──│  Agent  │──│  Tools  │──│Response │               │   ║
║    │  │ Router  │  │  Loop   │  │Executor │  │ Stream  │               │   ║
║    │  └────┬────┘  └────┬────┘  └────┬────┘  └─────────┘               │   ║
║    │       │            │            │                                   │   ║
║    │  ┌────┴────────────┴────────────┴────┐                             │   ║
║    │  │      ESASS OBSERVATION HOOKS      │  ◀── [EXPLORE: Hooks]       │   ║
║    │  └───────────────────┬───────────────┘                             │   ║
║    └──────────────────────┼──────────────────────────────────────────────┘   ║
║                           │                                                  ║
║                           ▼                                                  ║
║    ┌─────────────────────────────────────────────────────────────────────┐   ║
║    │                      ESASS OBSERVATION LAYER                         │   ║
║    │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐       │   ║
║    │  │  Tool     │  │ Reasoning │  │ Decision  │  │  Context  │       │   ║
║    │  │  Probe    │  │  Probe    │  │  Probe    │  │  Probe    │       │   ║
║    │  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘       │   ║
║    │        └──────────────┴──────────────┴──────────────┘              │   ║
║    │                              │                                      │   ║
║    │                    ┌─────────┴─────────┐                            │   ║
║    │                    │   Event Pipeline  │  ◀── [EXPLORE: Pipeline]   │   ║
║    │                    └─────────┬─────────┘                            │   ║
║    └──────────────────────────────┼──────────────────────────────────────┘   ║
║                                   │                                          ║
║                                   ▼                                          ║
║    ┌─────────────────────────────────────────────────────────────────────┐   ║
║    │                      ESASS ANALYSIS ENGINE                           │   ║
║    │  ┌───────────────────┐      ┌───────────────────┐                  │   ║
║    │  │  Pattern Detector │  ──▶ │  Skill Generator  │                  │   ║
║    │  │  • Temporal       │      │  • Template       │                  │   ║
║    │  │  • Semantic       │      │  • Validation     │                  │   ║
║    │  │  • Behavioral     │      │  • SKILL.md       │                  │   ║
║    │  └─────────┬─────────┘      └─────────┬─────────┘                  │   ║
║    │            │                          │                             │   ║
║    │            │    ◀── [EXPLORE: Patterns]   ◀── [EXPLORE: Genesis]   │   ║
║    └────────────┼──────────────────────────┼─────────────────────────────┘   ║
║                 │                          │                                 ║
║                 │                          ▼                                 ║
║    ┌────────────┼─────────────────────────────────────────────────────────┐  ║
║    │            │              SKILL EVOLUTION LAYER                      │  ║
║    │  ┌─────────┴─────────┐  ┌───────────────┐  ┌───────────────┐       │  ║
║    │  │  Similarity       │  │  Unification  │  │   Lifecycle   │       │  ║
║    │  │  Clustering       │  │  Pipeline     │  │   Manager     │       │  ║
║    │  └───────────────────┘  └───────────────┘  └───────────────┘       │  ║
║    │                                                                     │  ║
║    │             ◀── [EXPLORE: Evolution]                               │  ║
║    └─────────────────────────────────────────────────────────────────────┘  ║
║                                   │                                         ║
║                                   ▼                                         ║
║    ┌─────────────────────────────────────────────────────────────────────┐  ║
║    │                         CLAWHUB REGISTRY                             │  ║
║    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐               │  ║
║    │  │ Publish │  │ Version │  │ Search  │  │  Sync   │               │  ║
║    │  │         │  │ Control │  │         │  │         │               │  ║
║    │  └─────────┘  └─────────┘  └─────────┘  └────┬────┘               │  ║
║    │                                              │                      │  ║
║    │             ◀── [EXPLORE: ClawHub]          │                      │  ║
║    └──────────────────────────────────────────────┼──────────────────────┘  ║
║                                                   │                         ║
║                                                   │ Skills sync back        ║
║                                                   ▼                         ║
║    ┌─────────────────────────────────────────────────────────────────────┐  ║
║    │                     OPENCLAW SKILL LOADER                            │  ║
║    │                                                                      │  ║
║    │   ~/.openclaw/skills/  ◀────────────────────────────────────────────│  ║
║    │        ↓                                                            │  ║
║    │   Agent System Prompt (skills injected)                             │  ║
║    │        ↓                                                            │  ║
║    │   Enhanced Agent Capabilities                                       │  ║
║    │        ↓                                                            │  ║
║    │   ┌──────────────────────────────────────┐                         │  ║
║    │   │  RECURSIVE LOOP CLOSES HERE ───────────────▶ Back to Top      │  ║
║    │   └──────────────────────────────────────┘                         │  ║
║    └─────────────────────────────────────────────────────────────────────┘  ║
║                                                                             ║
╚═════════════════════════════════════════════════════════════════════════════╝
```

---

## 🔍 Deep Dive: Observation Hooks

### How Events Flow from OpenClaw to ESASS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     OPENCLAW → ESASS EVENT FLOW                              │
└─────────────────────────────────────────────────────────────────────────────┘

User sends message: "Can you check the git status and commit my changes?"
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ OPENCLAW AGENT LOOP                                                          │
│                                                                              │
│  1. Message received                                                         │
│     ├── emit: SESSION_START(session_id, channel, user_id)                   │
│     └── emit: MESSAGE_RECEIVED(content, context)                            │
│                                                                              │
│  2. Agent thinking                                                           │
│     └── emit: THINKING_BLOCK(content: "I'll check git status first...")     │
│                                                                              │
│  3. Tool selection                                                           │
│     └── emit: TOOL_SELECTED(tool: "Bash", alternatives: ["Read", "Grep"])   │
│                                                                              │
│  4. Tool execution                                                           │
│     ├── emit: TOOL_CALL_START(call_id, tool: "Bash", params: {cmd: "git..."})
│     └── emit: TOOL_CALL_COMPLETE(call_id, result, success: true)            │
│                                                                              │
│  5. More thinking + tools...                                                 │
│                                                                              │
│  6. Response generation                                                      │
│     ├── emit: MESSAGE_SENT(response)                                        │
│     └── emit: SESSION_END(session_id)                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Events
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ESASS PROBE SYSTEM                                                           │
│                                                                              │
│  ProbeRegistry receives events and routes to interested probes:              │
│                                                                              │
│  THINKING_BLOCK ──▶ ReasoningProbe                                          │
│                      ├── Extract hypotheses ("I'll check git status first")  │
│                      ├── Estimate confidence (0.8)                           │
│                      ├── Extract evidence chains                             │
│                      └── Generate: LogEntry(type="reasoning", tags=["git"])  │
│                                                                              │
│  TOOL_CALL_* ──▶ ToolCallProbe                                              │
│                   ├── Track tool invocation lifecycle                        │
│                   ├── Detect sequences (Bash:git status → Bash:git add)      │
│                   ├── Sanitize parameters (remove secrets)                   │
│                   └── Generate: LogEntry(type="tool_usage", outcome=SUCCESS) │
│                                                                              │
│  TOOL_SELECTED ──▶ DecisionProbe                                            │
│                     ├── Capture decision point                               │
│                     ├── Record alternatives considered                       │
│                     ├── Extract rationale                                    │
│                     └── Generate: LogEntry(type="decision", tags=["git"])    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ LogEntries
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ EVENT PIPELINE (Buffered Async)                                              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Buffer (100 events)                                                  │    │
│  │ [entry1][entry2][entry3]...[entry100] ──▶ Flush to disk             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Flush triggers:                                                             │
│  • Buffer full (100 events)                                                  │
│  • Timer expires (5 seconds)                                                 │
│  • Explicit flush() call                                                     │
│                                                                              │
│  Performance:                                                                │
│  • Throughput: ~1500 events/sec                                             │
│  • Latency: ~3ms capture overhead                                           │
│  • Memory: ~60MB footprint                                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                            data/logs/log_20260201.jsonl
```

### Event Types Reference

| Event Type | Probe | Data Captured | Tags Extracted |
|------------|-------|---------------|----------------|
| `THINKING_BLOCK` | ReasoningProbe | Content, confidence, evidence | Concepts mentioned |
| `TOOL_CALL_START` | ToolCallProbe | Tool name, parameters | Tool category, targets |
| `TOOL_CALL_COMPLETE` | ToolCallProbe | Result, duration, success | Outcome type |
| `TOOL_CALL_ERROR` | ToolCallProbe | Error type, message | Error category |
| `TOOL_SELECTED` | DecisionProbe | Decision, alternatives, rationale | Decision domain |
| `SKILL_ACTIVATED` | FeedbackProbe | Skill name, trigger, context | Skill category |
| `SKILL_COMPLETED` | FeedbackProbe | Success, duration | Outcome |

---

## 🔍 Deep Dive: Pattern Detection

### How Patterns Emerge from Events

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PATTERN DETECTION PIPELINE                               │
└─────────────────────────────────────────────────────────────────────────────┘

Raw Logs (1000 events across 50 sessions)
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: SESSION GROUPING                                                     │
│                                                                              │
│ Session-001: [reasoning:git] → [tool:Bash:git status] → [decision:commit]   │
│ Session-002: [reasoning:file] → [tool:Read:main.py] → [tool:Edit:main.py]   │
│ Session-003: [reasoning:git] → [tool:Bash:git status] → [decision:commit]   │
│ Session-004: [reasoning:test] → [tool:Bash:pytest] → [decision:fix]         │
│ Session-005: [reasoning:git] → [tool:Bash:git status] → [decision:commit]   │
│ ...                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: SEQUENCE MINING (PrefixSpan)                                         │
│                                                                              │
│ Find all frequent subsequences of length 2-5:                                │
│                                                                              │
│ Subsequence                                          │ Count │ Sessions     │
│ ─────────────────────────────────────────────────────┼───────┼────────────  │
│ [reasoning:git] → [tool:Bash:git*]                   │  45   │ 45/50 (90%) │
│ [reasoning:git] → [tool:Bash:git*] → [decision]      │  42   │ 42/50 (84%) │
│ [tool:Read] → [tool:Edit]                            │  38   │ 38/50 (76%) │
│ [reasoning:test] → [tool:Bash:pytest]                │  28   │ 28/50 (56%) │
│ [tool:Bash:git status] → [tool:Bash:git add]         │  35   │ 35/50 (70%) │
│ ...                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: QUALITY METRICS                                                      │
│                                                                              │
│ For each subsequence, compute:                                               │
│                                                                              │
│ SUPPORT = number of occurrences                                              │
│ CONFIDENCE = P(complete sequence | first event)                              │
│ STABILITY = days the pattern has appeared                                    │
│                                                                              │
│ Example: [reasoning:git] → [tool:Bash:git status] → [decision:commit]        │
│                                                                              │
│   Support    = 42 occurrences                                                │
│   Confidence = 42/45 = 0.93 (93% of git reasoning leads to this sequence)   │
│   Stability  = 12 days (pattern first seen 12 days ago, still occurring)    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: CANDIDACY EVALUATION                                                 │
│                                                                              │
│ Thresholds for skill candidacy:                                              │
│   • min_support: 10                                                          │
│   • min_confidence: 0.8                                                      │
│   • min_stability_days: 7                                                    │
│                                                                              │
│ Pattern                                    │Support│Conf │Stable│Candidate? │
│ ───────────────────────────────────────────┼───────┼─────┼──────┼────────── │
│ [reasoning:git] → [tool:git*] → [decision] │  42   │0.93 │ 12d  │ ✅ YES    │
│ [tool:Read] → [tool:Edit]                  │  38   │0.76 │ 10d  │ ❌ Conf   │
│ [reasoning:test] → [tool:pytest]           │  28   │0.85 │ 8d   │ ✅ YES    │
│ [tool:Grep] → [tool:Read]                  │  15   │0.68 │ 5d   │ ❌ Both   │
│ [tool:git status] → [tool:git add]         │  35   │0.82 │ 11d  │ ✅ YES    │
│                                                                              │
│ Result: 3 skill candidates identified                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PATTERN DEFINITION OUTPUT                                                    │
│                                                                              │
│ {                                                                            │
│   "pattern_id": "pattern-abc123",                                           │
│   "pattern_type": "temporal",                                               │
│   "sequence": [                                                             │
│     "reasoning:git,commit,workflow",                                        │
│     "tool_usage:Bash,git,status",                                           │
│     "decision:git,commit"                                                   │
│   ],                                                                        │
│   "support": 42,                                                            │
│   "confidence": 0.93,                                                       │
│   "stability_days": 12,                                                     │
│   "skill_candidate": true,                                                  │
│   "tags": ["git", "commit", "workflow"],                                    │
│   "first_seen": "2026-01-20T10:30:00Z",                                     │
│   "last_seen": "2026-02-01T15:45:00Z"                                       │
│ }                                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pattern Types

| Type | Description | Detection Method | Example |
|------|-------------|------------------|---------|
| **Temporal** | Recurring event sequences | PrefixSpan algorithm | reasoning → tool → decision |
| **Semantic** | Similar content patterns | Embedding clustering | "debug" + "error" + "fix" |
| **Behavioral** | Action-outcome chains | Causal analysis | edit → test_fail → edit → test_pass |
| **Contextual** | Environment-dependent | Context correlation | morning + code_review patterns |

---

## 🔍 Deep Dive: Skill Genesis

### From Pattern to SKILL.md

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SKILL GENESIS PIPELINE                                │
└─────────────────────────────────────────────────────────────────────────────┘

Pattern Definition (Candidate)
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: TEMPLATE GENERATION                                                  │
│                                                                              │
│ Input: Pattern [reasoning:git] → [tool:Bash:git status] → [decision:commit] │
│                                                                              │
│ Extract:                                                                     │
│   Name: git_commit_skill (from dominant tags)                               │
│   Triggers: ["git commit", "commit changes", "save work to git"]            │
│   Capabilities: [git_operations, decision_making]                           │
│   Implementation: Describe the sequence steps                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: SKILL MANIFEST                                                       │
│                                                                              │
│ SkillManifest {                                                             │
│   skill_id: "skill-def456",                                                 │
│   name: "git_commit_skill",                                                 │
│   description: "Intelligent git commit workflow with semantic analysis",    │
│   source_pattern_ids: ["pattern-abc123"],                                   │
│   triggers: [                                                               │
│     "intent_match:git,commit",                                              │
│     "event_type:reasoning",                                                 │
│     "context:git,workflow"                                                  │
│   ],                                                                        │
│   capabilities: ["git_operations", "decision_making"],                      │
│   implementation_summary: "reasoning → git status → decision → commit",    │
│   genesis_type: "derived",                                                  │
│   validation_status: "pending",                                             │
│   version: "1.0.0"                                                          │
│ }                                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: SKILL.md FORMATTING (OpenClaw Compatible)                            │
│                                                                              │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ ---                                                                     │ │
│ │ name: git-commit-skill                                                  │ │
│ │ description: Intelligent git commit workflow...                         │ │
│ │ version: 1.0.0                                                          │ │
│ │ author: esass-genesis                                                   │ │
│ │ genesis:                                                                │ │
│ │   type: emergent                                                        │ │
│ │   pattern_id: pattern-abc123                                            │ │
│ │   confidence: 0.93                                                      │ │
│ │   support: 42                                                           │ │
│ │ metadata:                                                               │ │
│ │   openclaw:                                                             │ │
│ │     triggers: ["git commit", "commit changes"]                          │ │
│ │     capabilities: [git_operations, decision_making]                     │ │
│ │ ---                                                                     │ │
│ │                                                                         │ │
│ │ # Git Commit Skill                                                      │ │
│ │                                                                         │ │
│ │ ## Overview                                                             │ │
│ │ Intelligent git commit workflow with semantic analysis...               │ │
│ │                                                                         │ │
│ │ ## When to Use                                                          │ │
│ │ Use when the user wants to commit changes to git...                     │ │
│ │                                                                         │ │
│ │ ## Workflow                                                             │ │
│ │ 1. **Analyze Context**                                                  │ │
│ │    Evaluate git status and staged changes                               │ │
│ │                                                                         │ │
│ │ 2. **Execute Git Status**                                               │ │
│ │    ```bash                                                              │ │
│ │    git status                                                           │ │
│ │    ```                                                                  │ │
│ │                                                                         │ │
│ │ 3. **Make Decision**                                                    │ │
│ │    Choose commit strategy based on changes                              │ │
│ │ ...                                                                     │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: VALIDATION                                                           │
│                                                                              │
│ Checks:                                                                      │
│   ✅ YAML frontmatter valid                                                 │
│   ✅ Required fields present (name, description)                            │
│   ✅ Triggers are meaningful (not empty)                                    │
│   ✅ Capabilities map to known categories                                   │
│   ✅ No sensitive data in content                                           │
│   ✅ Markdown structure valid                                               │
│                                                                              │
│ Result: VALID                                                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
    skills/generated/git-commit-skill/SKILL.md
```

---

## 🔍 Deep Dive: Skill Evolution

### How Skills Improve Over Time

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SKILL EVOLUTION SYSTEM                                │
└─────────────────────────────────────────────────────────────────────────────┘

                              LIFECYCLE STATES
                              
    ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐
    │ NASCENT │ ───▶ │ GROWING │ ───▶ │ MATURE  │ ───▶ │CANDIDATE│
    │ (new)   │      │ (usage) │      │(stable) │      │(evolve) │
    └─────────┘      └─────────┘      └─────────┘      └────┬────┘
                                                            │
                          ┌─────────────────────────────────┤
                          │                                 │
                          ▼                                 ▼
                   ┌────────────┐                    ┌────────────┐
                   │ DEPRECATED │                    │  EVOLVED   │
                   │ (replaced) │                    │  (merged)  │
                   └────────────┘                    └────────────┘


                         UNIFICATION METHODS

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ABSORB: Dominant skill absorbs weaker one                                  │
│  ┌───────────┐   ┌───────────┐        ┌───────────────────┐                │
│  │ git-commit│ + │git-add-all│  ───▶  │ git-commit        │                │
│  │ (strong)  │   │ (weak)    │        │ (enhanced)        │                │
│  └───────────┘   └───────────┘        └───────────────────┘                │
│                                                                             │
│  MERGE: Create new from both                                                │
│  ┌───────────┐   ┌───────────┐        ┌───────────────────┐                │
│  │ git-status│ + │ git-diff  │  ───▶  │ git-status-diff   │                │
│  │ (similar) │   │ (similar) │        │ (new unified)     │                │
│  └───────────┘   └───────────┘        └───────────────────┘                │
│                                                                             │
│  PARAMETERIZE: Single skill with parameters                                 │
│  ┌───────────┐   ┌───────────┐        ┌───────────────────┐                │
│  │ git-commit│ + │git-commit │  ───▶  │ git-commit        │                │
│  │ (amend)   │   │ (regular) │        │ (--amend option)  │                │
│  └───────────┘   └───────────┘        └───────────────────┘                │
│                                                                             │
│  COMPOSE: Hierarchical composition                                          │
│  ┌───────────┐   ┌───────────┐        ┌───────────────────┐                │
│  │ git-commit│ + │ git-push  │  ───▶  │ git-workflow      │                │
│  │ (step 1)  │   │ (step 2)  │        │ (orchestrates)    │                │
│  └───────────┘   └───────────┘        └───────────────────┘                │
│                                                                             │
│  GENERALIZE: Extract common abstraction                                     │
│  ┌───────────┐   ┌───────────┐        ┌───────────────────┐                │
│  │python-test│ + │ jest-test │  ───▶  │ generic-test      │                │
│  │ (pytest)  │   │ (js)      │        │ (language-aware)  │                │
│  └───────────┘   └───────────┘        └───────────────────┘                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


                        7-DIMENSIONAL SIMILARITY

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  Skills are compared across 7 dimensions:                                   │
│                                                                             │
│  1. SEMANTIC    ──▶ Description/purpose similarity (embeddings)            │
│  2. BEHAVIORAL  ──▶ Action sequence similarity                             │
│  3. TRIGGER     ──▶ Activation condition overlap                           │
│  4. OUTPUT      ──▶ Result type similarity                                 │
│  5. STRUCTURAL  ──▶ Workflow structure similarity                          │
│  6. CONTEXTUAL  ──▶ Usage context overlap                                  │
│  7. TEMPORAL    ──▶ Usage time pattern similarity                          │
│                                                                             │
│  Combined score determines unification candidates.                          │
│                                                                             │
│  Example Similarity Matrix:                                                 │
│                                                                             │
│                  │ git-commit │ git-add │ git-status │ python-test │        │
│  ────────────────┼────────────┼─────────┼────────────┼─────────────│        │
│  git-commit      │    1.00    │  0.82   │    0.75    │    0.15     │        │
│  git-add         │    0.82    │  1.00   │    0.68    │    0.12     │        │
│  git-status      │    0.75    │  0.68   │    1.00    │    0.18     │        │
│  python-test     │    0.15    │  0.12   │    0.18    │    1.00     │        │
│                                                                             │
│  Unification threshold: 0.80 → git-commit + git-add are candidates         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Deep Dive: ClawHub Integration

### Publishing and Discovery Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLAWHUB INTEGRATION                                  │
└─────────────────────────────────────────────────────────────────────────────┘

                              PUBLISH FLOW

ESASS Generated Skill
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ VALIDATION                                                                   │
│                                                                              │
│   ✅ Confidence ≥ 0.85 (met: 0.93)                                          │
│   ✅ Support ≥ 15 (met: 42)                                                 │
│   ✅ SKILL.md format valid                                                  │
│   ✅ No sensitive data                                                      │
│   ✅ Rate limit not exceeded (2/10 today)                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ CLAWHUB CLI                                                                  │
│                                                                              │
│   $ clawhub publish ./skills/git-commit-skill \                             │
│       --slug git-commit-skill \                                             │
│       --name "Git Commit Skill" \                                           │
│       --version 1.0.0 \                                                     │
│       --changelog "ESASS auto-generated skill" \                            │
│       --tags latest,esass-generated                                         │
│                                                                              │
│   ✅ Published: https://clawhub.com/skills/git-commit-skill                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ CLAWHUB REGISTRY                                                             │
│                                                                              │
│   Skill: git-commit-skill                                                   │
│   Version: 1.0.0                                                            │
│   Tags: [latest, esass-generated]                                           │
│   Stars: 0                                                                  │
│   Installs: 0                                                               │
│                                                                              │
│   Vector embedding computed for semantic search                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘


                              DISCOVERY FLOW

User or System searches: "git commit workflow"
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ CLAWHUB VECTOR SEARCH                                                        │
│                                                                              │
│   $ clawhub search "git commit workflow"                                    │
│                                                                              │
│   Results (ranked by semantic similarity):                                  │
│                                                                              │
│   1. git-commit-skill (0.94) - Intelligent git commit workflow...           │
│   2. git-workflow (0.87) - Complete git workflow automation...              │
│   3. conventional-commits (0.72) - Commit message formatting...             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ INSTALL TO OPENCLAW                                                          │
│                                                                              │
│   $ clawhub install git-commit-skill                                        │
│                                                                              │
│   Installing git-commit-skill@1.0.0...                                      │
│   ✅ Installed to ~/.openclaw/skills/git-commit-skill/                      │
│                                                                              │
│   File structure:                                                           │
│   ~/.openclaw/skills/                                                       │
│   └── git-commit-skill/                                                     │
│       └── SKILL.md                                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ OPENCLAW SKILL LOADING                                                       │
│                                                                              │
│   On next session, OpenClaw:                                                │
│                                                                              │
│   1. Scans skill directories:                                               │
│      - Bundled: ./node_modules/openclaw/skills/                             │
│      - Managed: ~/.openclaw/skills/  ◀── NEW SKILL HERE                     │
│      - Workspace: <workspace>/skills/                                       │
│                                                                              │
│   2. Loads SKILL.md with frontmatter                                        │
│                                                                              │
│   3. Injects into system prompt:                                            │
│      <available_skills>                                                     │
│        <skill>                                                              │
│          <name>git-commit-skill</name>                                      │
│          <description>Intelligent git commit workflow...</description>      │
│          <location>~/.openclaw/skills/git-commit-skill/SKILL.md</location>  │
│        </skill>                                                             │
│      </available_skills>                                                    │
│                                                                              │
│   4. Agent can now use the skill!                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Deep Dive: The Complete Recursive Loop

### End-to-End Flow Visualization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    THE COMPLETE RECURSIVE LEARNING LOOP                      │
└─────────────────────────────────────────────────────────────────────────────┘

                                  TIME ───────────────────▶

Day 1-3: OBSERVATION PHASE
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  User interactions across WhatsApp, Telegram, Discord...                    │
│                                                                             │
│  Session 1: "commit my changes" → git status → git add → git commit        │
│  Session 2: "commit the fixes" → git status → git add → git commit         │
│  Session 3: "save my work" → git status → git diff → git add → git commit  │
│  ...                                                                        │
│  Session 50: similar patterns accumulating                                  │
│                                                                             │
│  ESASS probes capture all tool calls, reasoning, decisions                  │
│  Event pipeline writes to: data/logs/log_20260201.jsonl                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
Day 4: PATTERN DETECTION (Automated Cycle)
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  Loop Controller triggers detection cycle at 6-hour interval                │
│                                                                             │
│  1. Load logs from last 24 hours: 500 events                               │
│  2. Run PrefixSpan mining: 25 patterns found                               │
│  3. Apply quality thresholds: 8 skill candidates                           │
│                                                                             │
│  Top candidate: [reasoning:git] → [tool:git*] → [decision]                 │
│    Support: 45, Confidence: 0.93, Stability: 4 days                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
Day 4-7: SKILL MATURATION
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  Pattern continues to accumulate support                                    │
│  Day 5: Support 52, Confidence 0.94, Stability 5 days                      │
│  Day 6: Support 58, Confidence 0.93, Stability 6 days                      │
│  Day 7: Support 67, Confidence 0.94, Stability 7 days ✅ READY             │
│                                                                             │
│  Pattern meets all candidacy thresholds for skill genesis                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
Day 7: SKILL GENESIS
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  1. Template Generator creates SkillManifest                               │
│  2. Skill Formatter converts to SKILL.md                                   │
│  3. Validation passes all checks                                           │
│                                                                             │
│  Output: skills/generated/git-commit-skill/SKILL.md                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
Day 7: PUBLISH TO CLAWHUB
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  Auto-publish triggered (confidence 0.94 > 0.85 threshold)                 │
│                                                                             │
│  $ clawhub publish ... --version 1.0.0                                     │
│  ✅ Published: https://clawhub.com/skills/git-commit-skill                 │
│                                                                             │
│  Skill now discoverable by all OpenClaw users worldwide                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
Day 7+: SYNC TO OPENCLAW
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  $ clawhub sync                                                            │
│                                                                             │
│  Skill installed to ~/.openclaw/skills/git-commit-skill/                   │
│  OpenClaw loads skill on next session                                      │
│                                                                             │
│  Agent now has enhanced git commit capabilities!                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
Day 8+: LOOP CLOSES - FEEDBACK & EVOLUTION
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  User: "commit my changes"                                                 │
│                                                                             │
│  OpenClaw activates: git-commit-skill                                      │
│  ESASS observes: SKILL_ACTIVATED, SKILL_COMPLETED                          │
│                                                                             │
│  Feedback loop:                                                             │
│  - Track skill usage success rate                                          │
│  - Detect new patterns building on skill                                   │
│  - Identify skill variations for evolution                                 │
│                                                                             │
│  Eventually: git-commit-skill + git-push-skill → git-workflow-skill        │
│                                                                             │
│  🔄 RECURSIVE IMPROVEMENT CONTINUES                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Metrics Dashboard

### Key Performance Indicators

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RECURSIVE LOOP HEALTH DASHBOARD                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  OBSERVATION METRICS                                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ Events/Day:     ████████████████████ 2,450                           │ │
│  │ Sessions/Day:   ████████████ 156                                      │ │
│  │ Probe Coverage: ██████████████████████████ 98%                        │ │
│  │ Pipeline Health:██████████████████████████████ 100%                   │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  PATTERN DETECTION METRICS                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ Patterns Detected:   ████████████████ 32                              │ │
│  │ Skill Candidates:    ████████████ 12                                  │ │
│  │ Avg Confidence:      ██████████████████████ 0.87                      │ │
│  │ Avg Support:         ████████████████ 28                              │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  SKILL GENESIS METRICS                                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ Skills Generated:    ████████ 8                                       │ │
│  │ Skills Published:    ██████ 6                                         │ │
│  │ Publish Success:     ████████████████████████ 95%                     │ │
│  │ Avg Generation Time: 2.3s                                             │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  EVOLUTION METRICS                                                          │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ Unifications:        ████ 4                                           │ │
│  │ Deprecations:        ██ 2                                             │ │
│  │ Skill Generations:   Gen 1: 5  Gen 2: 2  Gen 3: 1                     │ │
│  │ Ecosystem Health:    ██████████████████████████ 94%                   │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  LOOP TIMING                                                                │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ Cycle Interval:      6 hours                                          │ │
│  │ Last Cycle:          2026-02-01 15:30:00 (45 min ago)                 │ │
│  │ Cycle Duration:      12.4 seconds                                     │ │
│  │ Cycles Today:        4                                                │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Getting Started Checklist

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           IMPLEMENTATION CHECKLIST                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PREREQUISITES                                                              │
│  □ Python 3.8+ installed                                                    │
│  □ Node.js 22+ installed                                                    │
│  □ OpenClaw installed and configured                                        │
│  □ ClawHub account created                                                  │
│                                                                             │
│  SETUP                                                                      │
│  □ Clone ESASS repository                                                   │
│  □ Install dependencies: uv sync                                            │
│  □ Install clawhub CLI: npm i -g clawhub                                    │
│  □ Authenticate: clawhub login                                              │
│                                                                             │
│  CONFIGURATION                                                              │
│  □ Set ESASS_DATA_DIR environment variable                                  │
│  □ Set CLAWHUB_TOKEN for auto-publish                                       │
│  □ Configure loop parameters in settings.py                                 │
│  □ Set confidence/support thresholds                                        │
│                                                                             │
│  INTEGRATION                                                                │
│  □ Add ESASS hooks to OpenClaw agent loop                                   │
│  □ Test event capture with demo sessions                                    │
│  □ Verify pattern detection with test data                                  │
│  □ Test skill generation pipeline                                           │
│  □ Verify ClawHub publishing                                                │
│                                                                             │
│  DEPLOYMENT                                                                 │
│  □ Enable production loop controller                                        │
│  □ Configure monitoring/alerting                                            │
│  □ Set up log rotation                                                      │
│  □ Document operational procedures                                          │
│                                                                             │
│  MONITORING                                                                 │
│  □ Track loop health metrics                                                │
│  □ Monitor skill quality signals                                            │
│  □ Review generated skills periodically                                     │
│  □ Tune thresholds based on results                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

*This explorable documentation is designed to be navigated both linearly and by jumping to specific deep dives. Each section is self-contained but connects to the larger system architecture.*
