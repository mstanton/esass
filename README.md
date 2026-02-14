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
- `.esass/data/` -- local observation logs (gitignored)
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

## How It Works

```
Claude Code session
      │
      ├── PostToolUse hook fires on every tool call
      │     └── python -m esass.hooks.post_tool_use
      │           ├── logs event to .esass/data/logs/
      │           ├── updates sequence tracker
      │           └── runs 8 specialized probes
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
| `esass status` | Show system stats and probe health |
| `esass stats` | Event and pattern statistics |
| `esass analyze` | Detect patterns from observation logs |
| `esass generate-skills` | Generate skills from validated patterns |
| `esass pipeline` | Run full observe -> analyze -> generate -> export |
| `esass export` | Export patterns and skills to Obsidian vault |
| `esass watch` | Real-time event monitor |
| `esass audit` | Interactive skill auditor TUI |
| `esass setup` | Show hook installation instructions |

## Project Structure

```
src/esass/
├── __init__.py          # Version, public API
├── config.py            # Centralized config with auto-detection chain
├── models.py            # Core data models
├── cli/                 # Click CLI (esass command)
│   ├── main.py          # Command group and all subcommands
│   └── init_cmd.py      # esass init logic
├── probes/              # 8 specialized observation probes
│   ├── base.py          # Probe ABC, FilteringProbe, TagExtractor
│   ├── config.py        # Probe configuration and initialization
│   ├── tool_call.py     # Tool usage and sequence detection
│   ├── reasoning.py     # Reasoning and causal chain tracking
│   ├── decision.py      # Decision and tradeoff analysis
│   ├── calibration.py   # Confidence calibration
│   ├── insight.py       # Insight and realization detection
│   └── ...
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
    ├── server.py        # MCP server entry point
    ├── ollama_client.py # Local LLM client with circuit breaker
    ├── huggingface_client.py
    ├── tier_router.py   # 3-tier routing logic
    ├── adaptive_router.py # Success-rate based tier promotion
    ├── cost_tracker.py  # Cost analytics
    └── utils.py         # Circuit breaker, cache, rate limiter, retry
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

```bash
# MCP tools available in Claude Code sessions:
execute_skill          # Run skill via local LLM
analyze_pattern        # Semantic pattern analysis
generate_skill_name    # Create meaningful skill names
get_cost_dashboard     # Cost analytics
get_adaptive_status    # Learning status
check_availability     # LLM tier health
```

## Testing

```bash
# All tests
pytest

# Probe tests (27 tests)
pytest tests/test_probes.py -v

# Hardened MCP tests (49 tests)
pytest tests/test_hardened.py -v

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
