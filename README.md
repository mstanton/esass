# ESASS - Emergent Self-Adaptive Skill System

A meta-cognitive architecture that enables AI coding assistants to observe their own tool usage, detect recurring patterns, and autonomously generate reusable skills.

ESASS hooks into [Claude Code](https://claude.ai/code) sessions, silently observing every tool call. Over time it recognizes workflows you repeat, crystallizes them into named skills, and makes them available for faster execution through a local LLM tier that cuts API costs by up to 90%.

## Quick Start

```bash
pip install -e "."            # core
pip install -e ".[all]"       # core + TUI + MCP server
pip install -e ".[all,dev]"   # everything + test tools

cd your-project
esass init
```

`esass init` detects your environment and sets up:

- `.esass/config.yaml` -- project-level configuration
- `.esass/data/` -- local observation logs and MCP data (gitignored)
- `~/.claude/hooks.json` -- PostToolUse and SessionStart hooks
- `.claude/commands/esass.md` -- the `/esass` slash command

Restart Claude Code after init. The observer starts automatically.

### Optional: Local LLM for cost-optimized skill execution

```bash
pip install -e ".[mcp]"      # adds MCP server dependencies
ollama serve                  # start Ollama
ollama pull gemma3:4b         # pull the default model
esass init --enable-mcp       # configure MCP server in .mcp.json
```

### Flags

```
esass init --global          # install hooks and data in ~/
esass init --enable-mcp      # add MCP server config to .mcp.json
esass init --ollama-model X  # use a specific Ollama model
esass init --yes             # non-interactive, accept defaults
```

## How It Works

```
Claude Code session
      │
      ├── PostToolUse hook fires on every tool call
      │     └── python -m esass.hooks.post_tool_use
      │           ├── logs event to .esass/data/logs/
      │           ├── updates sequence tracker
      │           └── runs 10 specialized probes
      │
      ├── MCP server (if enabled)
      │     ├── executes skills via local LLM (Ollama)
      │     ├── logs executions to .esass/data/logs/mcp_events_{date}.jsonl
      │     └── writes status snapshot to .esass/data/mcp/status.json
      │
      ├── Unified Dashboard (python -m esass.hooks.dashboard)
      │     ├── polls tool event logs (0.5s refresh)
      │     ├── polls MCP event logs and status
      │     └── renders: field, events, patterns, MCP panel
      │
      ├── esass analyze   (detect patterns from logs)
      ├── esass generate  (turn patterns into skills)
      └── esass export    (push to Obsidian vault)
```

### The Pipeline

1. **Observe** -- Hooks capture tool name, parameters, outcome, timing, and session context for every tool call.
2. **Analyze** -- Pattern detection finds recurring tool sequences (e.g., `Grep -> Read -> Edit` repeated 15 times becomes a candidate).
3. **Generate** -- Validated patterns are turned into skill definitions with triggers, templates, and metadata.
4. **Execute** -- Skills route through a 3-tier LLM system: local Ollama (~$0), HuggingFace ($0.001/1K tok), or Claude ($0.015/1K tok).
5. **Evolve** -- Adaptive routing tracks success rates per skill and promotes/demotes across tiers automatically.

## CLI Commands

| Command | Description |
|---------|-------------|
| `esass init` | Initialize ESASS in current project |
| `esass stats` | Event, pattern, and skill statistics |
| `esass analyze` | Detect patterns from observation logs |
| `esass generate-skills` | Generate skills from validated patterns |
| `esass pipeline` | Run full observe -> analyze -> generate -> export |
| `esass export` | Export patterns and skills to Obsidian vault |
| `esass watch` | Real-time event monitor (terminal) |
| `esass audit` | Interactive skill auditor TUI |
| `esass setup` | Show hook installation instructions |

## Dashboard

The unified dashboard runs in a separate terminal and provides real-time visibility into both tool usage and MCP server activity.

```bash
# Launch manually
python -m esass.hooks.dashboard

# Or auto-launched via SessionStart hook
```

### What it shows

```
═══════════════════════════════════════════════════════════════
  ESASS UNIFIED DASHBOARD       [✓ SYNCHRONIZED]    10:30:15
═══════════════════════════════════════════════════════════════

  Protection Field                    Live Event Stream

  [gradient visualization]             10:30:14 [R] Read   src/main.py
                                       10:30:13 [E] Edit   src/main.py
                                       10:30:12 [M] MCP    fix_import ✓ local $0.01

  Field Status        Tool Usage           System Health

  Health:  STABLE     [R] Read    ███      Alerts:  ✓ NONE
  Trust:   ██████ 65% [E] Edit    ██       Errors:  ▁▁▂▃▁▁▁
  Events:  142        [$] Bash    █        Success: ▇▇▇▆▇▇▇
────────────────────────────────────────────────────────────────
  MCP Server           Tier Distribution       Cost Tracking

  local         ✓      local     ████████ 81%  Executions:  47
  huggingface   ✓      huggingface ██     17%  Cost:     $0.0023
  claude        ✓      claude      █       2%  Savings:  $0.69 (99%)

  ollama    ○ CLOSED   Cache: 12/50 (23%)      Rate: ████████ 8/10
  huggingface ○ CLOSED
────────────────────────────────────────────────────────────────
  Pattern Formation & Skill Crystallization

  ● ●●●●○ Read → Edit → Bash           (12x)
  ● ●●●○○ Grep → Read → Edit           (8x)
────────────────────────────────────────────────────────────────
  Unified Event Stream (tool calls + MCP executions)

  10:30:14   [R]Read  file_op         src/main.py
  10:30:13   [M]MCP   fix_import  ✓   local  $0.0149
  10:30:12   [$]Bash  git             git status

  [H]istory:[ON] [M]CP:[ON] [S]napshot [C]lear │ Ctrl+C to exit
```

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| `H` | Toggle historical alerts display |
| `M` | Toggle MCP server panel |
| `S` | Save dashboard snapshot to markdown |
| `C` | Clear event buffer |

### Dashboard data flow

The dashboard reads from two file-based streams (no sockets or IPC):

| Source | File | Updated by |
|--------|------|-----------|
| Tool events | `.esass/data/logs/log_{date}.jsonl` | PostToolUse hook |
| MCP events | `.esass/data/logs/mcp_events_{date}.jsonl` | MCP server |
| MCP status | `.esass/data/mcp/status.json` | MCP server (every 5s) |

If the MCP server isn't running, the MCP panel is hidden automatically.

## Project Structure

```
src/esass/
├── __init__.py          # Version, public API
├── config.py            # Centralized config with auto-detection chain
├── models.py            # Core data models
├── cli/                 # Click CLI (esass command)
│   ├── main.py          # Command group and all subcommands
│   └── init_cmd.py      # esass init logic
├── probes/              # 10 specialized observation probes
│   ├── base.py          # Probe ABC, FilteringProbe, TagExtractor
│   ├── config.py        # Probe configuration and initialization
│   ├── pipeline.py      # Event pipeline (sync, async, priority)
│   ├── registry.py      # Probe registry and lifecycle
│   ├── tool_probe.py    # Tool usage and sequence detection
│   ├── reasoning_probe.py # Reasoning and causal chain tracking
│   ├── decision_probe.py  # Decision and tradeoff analysis
│   ├── calibration_probe.py # Confidence calibration
│   ├── insight_probe.py   # Insight and realization detection
│   ├── error_recovery_probe.py # Error recovery tracking
│   ├── strategy_shift_probe.py # Strategy shift detection
│   ├── scope_expansion_probe.py # Scope creep detection
│   ├── reliability_probe.py # Tool reliability tracking
│   ├── field_boundary_probe.py # Field boundary monitoring
│   ├── latency_probe.py  # Latency tracking
│   └── logic_loop_probe.py # Logic loop detection
├── hooks/               # Claude Code hook entry points
│   ├── post_tool_use.py # Main hook (python -m esass.hooks.post_tool_use)
│   ├── session_start.py # Session startup hook
│   ├── dashboard.py     # Unified monitoring dashboard
│   ├── startup.py       # Dashboard auto-launcher
│   └── templates/       # Config file templates for esass init
├── analysis/            # Pattern detection engine
├── genesis/             # Skill generation from patterns
├── storage/             # Log and pattern persistence
├── export/              # Obsidian vault export
├── tui/                 # Textual-based terminal UI
└── mcp/                 # MCP server (optional, pip install esass[mcp])
    ├── server.py        # MCP server entry point + status loop
    ├── event_logger.py  # Writes execution events for dashboard
    ├── status_writer.py # Writes periodic status snapshot
    ├── ollama_client.py # Local LLM client with circuit breaker
    ├── huggingface_client.py
    ├── tier_router.py   # 3-tier routing logic
    ├── adaptive_router.py # Success-rate based tier promotion
    ├── cost_tracker.py  # Cost analytics and persistence
    └── utils.py         # Circuit breaker, cache, rate limiter, retry
```

### Data directory layout

```
.esass/data/
├── logs/
│   ├── log_20260214.jsonl          # Tool events (one per hook call)
│   └── mcp_events_20260214.jsonl   # MCP execution events
├── mcp/
│   ├── status.json                 # MCP server health snapshot
│   ├── cost_tracking/              # Cumulative cost stats + daily JSONL
│   └── adaptive_routing/           # Pattern history + capability learning
├── state/
│   ├── sequence_state.json         # Tool sequence counter
│   └── current_session.json        # Session ID tracker
├── patterns/                       # Detected pattern definitions
└── skills/                         # Generated skill manifests
```

## Configuration

ESASS looks for config in this order:

1. `$ESASS_CONFIG` environment variable
2. `.esass/config.yaml` in the current project
3. `~/.esass/config.yaml` global config
4. Built-in defaults

Key settings in `.esass/config.yaml`:

```yaml
observation:
  max_events_per_session: 10000
  buffer_size: 100
  flush_interval_seconds: 30

pattern_detection:
  min_support: 3
  min_confidence: 0.7
  max_pattern_length: 10

skill_generation:
  min_pattern_support: 5
  require_human_review: true

local_llm:
  enabled: false
  ollama_model: "gemma3:4b"
  ollama_url: "http://localhost:11434"
```

Environment variable overrides: `ESASS_DATA_DIR`, `ESASS_CONFIG`.

## Local LLM Integration

The MCP server provides cost-optimized skill execution through a 3-tier system:

| Tier | Provider | Cost/1K tokens | Use case |
|------|----------|---------------|----------|
| Local | Ollama (gemma3:4b) | ~$0.0001 | File ops, testing, git (70% of tasks) |
| Cloud | HuggingFace | ~$0.001 | Complex analysis, fallback |
| Premium | Claude | ~$0.015 | Security, architecture decisions |

Resilience features:
- **Circuit breaker**: Opens after 3 consecutive Ollama failures (30s recovery)
- **Retry with backoff**: 3 attempts with exponential delay
- **Response cache**: LRU cache with 5-minute TTL
- **Rate limiting**: 30 requests/minute with burst capacity of 10
- **Adaptive routing**: Tracks success rates, auto-demotes failing skills
- **Dashboard integration**: Execution events and server status streamed to the dashboard in real time

### MCP tools

Available in Claude Code sessions when the MCP server is running:

| Tool | Description |
|------|-------------|
| `execute_skill` | Run a skill via local LLM with automatic tier fallback |
| `analyze_pattern` | Semantic analysis of tool usage patterns |
| `generate_skill_name` | Create meaningful skill names from patterns |
| `check_availability` | Check LLM tier health and circuit breaker state |
| `get_cost_dashboard` | Session costs, savings, tier breakdown, projections |
| `get_full_analytics` | Comprehensive analytics with adaptive learning data |
| `get_adaptive_status` | Tier overrides and learned capability routing |
| `get_routing_stats` | Routing statistics and failure counts |

## Testing

```bash
# All tests (164)
pytest

# Probe tests (27 tests)
pytest tests/test_probes.py -v

# Hardened MCP tests (49 tests)
pytest tests/test_hardened.py -v

# MCP dashboard integration tests (19 tests)
pytest tests/test_mcp_dashboard.py -v

# Integration tests
pytest tests/test_comprehensive.py -v

# With coverage
pytest --cov=esass --cov-report=html
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[all,dev]"

# Lint
ruff check src/

# Format check
ruff format --check src/

# Run the event simulator (for testing the dashboard)
python -m esass.hooks.simulate_events --speed 2 --loops 5

# Start Ollama for local LLM development
ollama serve && ollama pull gemma3:4b
```

## Optional Dependencies

| Extra | What it adds |
|-------|-------------|
| `tui` | Textual-based terminal UI for `esass audit` |
| `mcp` | MCP server + Ollama/HuggingFace clients |
| `all` | `tui` + `mcp` |
| `dev` | pytest, ruff, coverage tools |

## License

MIT
