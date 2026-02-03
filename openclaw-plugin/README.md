# ESASS × OpenClaw × ClawHub

## Recursive Self-Improving Skill Architecture

A meta-cognitive system that enables AI agents to learn from their own execution patterns and automatically develop, publish, and evolve new capabilities.

```text
    ┌──────────────┐
    │   ClawHub    │◀──────────────────────────────┐
    │   Registry   │                                │
    └──────┬───────┘                                │
           │ Install                                │ Publish
           ▼                                        │
    ┌──────────────┐                                │
    │   OpenClaw   │       ┌──────────────┐         │
    │    Gateway   │──────▶│    ESASS     │───────┘
    │ (Agent Loop) │Events │ Observation  │ Skills
    └──────────────┘       │ + Genesis    │
                           └──────────────┘
                           
         RECURSIVE SKILL EVOLUTION LOOP
```

---

## 🎯 What This Does

1. **Observes**: ESASS probes capture every tool call, reasoning step, and decision from OpenClaw agents
2. **Detects**: Pattern recognition identifies recurring behavioral sequences  
3. **Generates**: High-confidence patterns crystallize into OpenClaw-compatible SKILL.md files
4. **Publishes**: Skills automatically publish to ClawHub for discovery
5. **Evolves**: Similar skills merge, weak skills deprecate, the ecosystem improves
6. **Loops**: Enhanced agents generate new patterns, closing the recursive loop

---

## 📚 Documentation

| Document | Description |
| ---------- | ------------- |
| [**ESASS_OPENCLAW_INTEGRATION.md**](ESASS_OPENCLAW_INTEGRATION.md) | Architecture overview and integration design |
| [**IMPLEMENTATION_GUIDE.md**](IMPLEMENTATION_GUIDE.md) | Complete code implementation with examples |
| [**EXPLORABLE_DOCUMENTATION.md**](EXPLORABLE_DOCUMENTATION.md) | Visual deep dives into each component |
| [**examples/skills/**](examples/skills/) | Sample ESASS-generated skills |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.8+
python --version

# Node.js 22+
node --version

# OpenClaw installed
openclaw --help

# ClawHub CLI
npm i -g clawhub
clawhub login
```

### Installation

```bash
# Clone and setup
git clone https://github.com/mstanton/esass
cd esass

# Install dependencies
pip install uv
uv sync

# Verify ESASS
uv run esass --help
```

### Run the Demo

```python
import asyncio
from src.loop.controller import RecursiveLoopController, LoopConfig

async def main():
    # Configure the loop
    config = LoopConfig(
        observation_window_hours=24,
        cycle_interval_hours=6,
        min_support=10,
        min_confidence=0.8,
        auto_publish=True
    )
    
    # Create and start controller
    controller = RecursiveLoopController(config=config)
    
    # Register callbacks
    controller.on_skill_generated(lambda s: print(f"✓ Generated: {s.name}"))
    controller.on_skill_published(lambda s, r: print(f"✓ Published: {r.url}"))
    
    # Run one cycle
    results = await controller.run_cycle()
    print(f"Cycle complete: {results}")

asyncio.run(main())
```

---

## 🏗️ Architecture

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

### Component Overview

| Component | Purpose | Key Files |
| ----------- | --------- | ----------- |
| **OpenClaw Bridge** | Capture events from agent loop | `src/bridge/openclaw_hooks.py` |
| **ESASS Probes** | Extract structured observations | `esass/probes/*.py` |
| **Pattern Detector** | Mine recurring sequences | `esass_prototype/analysis/` |
| **Skill Generator** | Create SKILL.md from patterns | `src/adapters/skill_formatter.py` |
| **ClawHub Client** | Publish and sync skills | `src/adapters/clawhub_client.py` |
| **Loop Controller** | Orchestrate the cycle | `src/loop/controller.py` |

---

## 📊 Metrics & Monitoring

### Loop Health Indicators

| Metric | Target | Description |
| -------- | -------- | ------------- |
| Events/Day | 1000+ | Raw observation volume |
| Pattern Detection Rate | 5+/week | New patterns discovered |
| Skill Crystallization Rate | 2+/week | Skills generated |
| Skill Adoption Rate | 30%+ | Install rate on ClawHub |
| Skill Effectiveness | 80%+ | Success rate when used |
| Loop Latency | <7 days | Observation → Available |

### Safety Thresholds

| Safeguard | Default | Description |
| ----------- | --------- | ------------- |
| Min Confidence | 0.85 | Pattern reliability |
| Min Support | 15 | Observation count |
| Min Stability | 7 days | Pattern persistence |
| Rate Limit | 10/day | Max skills published |
| Human Approval | Optional | Review before publish |

---

## 🔧 Configuration

### Environment Variables

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

### Loop Configuration

```python
from src.loop.controller import LoopConfig

config = LoopConfig(
    # Timing
    observation_window_hours=24,
    cycle_interval_hours=6,
    
    # Detection thresholds
    min_events_for_detection=100,
    min_support=10,
    min_confidence=0.8,
    min_stability_days=7,
    
    # Generation
    auto_generate=True,
    max_skills_per_cycle=5,
    
    # Publishing
    auto_publish=True,
    publish_confidence_threshold=0.85,
    publish_support_threshold=15,
    
    # Safety
    require_human_approval=False,
    rate_limit_skills_per_day=10
)
```

---

## 📁 Project Structure

```text
esass-openclaw-integration/
├── README.md                          # This file
├── ESASS_OPENCLAW_INTEGRATION.md      # Architecture overview
├── IMPLEMENTATION_GUIDE.md            # Code implementation
├── EXPLORABLE_DOCUMENTATION.md        # Visual deep dives
│
├── src/
│   ├── bridge/
│   │   ├── openclaw_hooks.py          # Event capture from OpenClaw
│   │   ├── event_translator.py        # Translate to ESASS format
│   │   └── feedback_collector.py      # Skill usage feedback
│   │
│   ├── adapters/
│   │   ├── skill_formatter.py         # ESASS → SKILL.md conversion
│   │   ├── clawhub_client.py          # ClawHub API client
│   │   └── openclaw_loader.py         # Skill installation
│   │
│   ├── loop/
│   │   ├── controller.py              # Main loop orchestration
│   │   ├── scheduler.py               # Timing and triggers
│   │   └── metrics.py                 # Loop health monitoring
│   │
│   └── config/
│       └── settings.py                # Configuration management
│
├── examples/
│   ├── quick_start.py                 # Demo script
│   └── skills/
│       └── git-smart-workflow/        # Sample generated skill
│           └── SKILL.md
│
└── tests/
    ├── test_bridge.py
    ├── test_adapters.py
    └── test_loop.py
```

---

## 🎓 Key Concepts

### Skill Genesis

Skills aren't programmed—they emerge from observation. A skill becomes a "candidate" when:

1. **Support** ≥ 10: Pattern observed at least 10 times
2. **Confidence** ≥ 0.8: 80%+ of the time, the pattern completes successfully
3. **Stability** ≥ 7 days: Pattern persists over a week (not a fluke)

### Skill Evolution

Skills aren't static—they evolve through:

- **Unification**: Similar skills merge into stronger ones
- **Parameterization**: Variants become options on a single skill
- **Composition**: Sequential skills become orchestrated workflows
- **Deprecation**: Weak skills are gracefully retired

### The Ecosystem Perspective

Skills exist in relationships:

- **Symbiotic**: Skills that enhance each other (git-commit + code-review)
- **Competitive**: Skills competing for the same triggers
- **Keystone**: Critical skills that other skills depend on

---

## 🔗 Related Projects

| Project | Description | Link |
| --------- | ------------- | ------ |
| **ESASS** | Emergent Self-Adaptive Skill System | [github.com/mstanton/esass](https://github.com/mstanton/esass) |
| **OpenClaw** | AI Agent Gateway | [docs.openclaw.ai](https://docs.openclaw.ai) |
| **ClawHub** | Skill Registry | [clawhub.com](https://clawhub.com) |

---

## 📜 License

MIT License - See LICENSE file for details.

---

## 🙏 Acknowledgments

- **ESASS** concept developed by Matthew Stanton
- **OpenClaw** created by Peter Steinberger and contributors
- **ClawHub** registry infrastructure by the OpenClaw team

---

> "Skills aren't programmed—they emerge from the residue of intelligent behavior, crystallize through observation, and evolve through usage."
