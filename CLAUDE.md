# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Build and Test

```bash
# Install (editable, all extras + dev tools)
pip install -e ".[all,dev]"

# Run all tests
pytest

# Specific test suites
pytest tests/test_probes.py -v           # 27 probe tests
pytest tests/test_hardened.py -v         # 49 hardened MCP tests
pytest tests/test_comprehensive.py -v    # MCP integration tests

# Lint
ruff check src/
```

## Project Layout

Single pip-installable package. Source lives in `src/esass/`, tests in `tests/`.

```
src/esass/
├── config.py            # Centralized config (auto-detection chain)
├── models.py            # Core data models
├── cli/main.py          # Click CLI (esass command, all subcommands)
├── cli/init_cmd.py      # esass init
├── probes/              # 10 observation probes (base.py, config.py, tool_probe.py, ...)
├── hooks/               # Claude Code hooks
│   ├── post_tool_use.py # Main hook entry point
│   ├── session_start.py # Session startup
│   ├── dashboard.py     # Monitoring dashboard
│   └── templates/       # Config templates for esass init
├── analysis/            # Pattern detection
├── genesis/             # Skill generation
├── storage/             # Persistence layer
├── export/              # Obsidian export
├── tui/                 # Terminal UI (optional, esass[tui])
└── mcp/                 # MCP server (optional, esass[mcp])
    ├── server.py        # Entry point (esass-mcp-server command)
    ├── mcp_config.py    # MCP-specific config (Tier enum, routing)
    ├── ollama_client.py # Circuit breaker + cache + retry
    ├── huggingface_client.py
    ├── tier_router.py
    ├── adaptive_router.py
    ├── cost_tracker.py
    └── utils.py         # CircuitBreaker, ResponseCache, RateLimiter, retry_async
```

## Key Architecture

### Hooks (no hardcoded paths)

All hooks use `python -m` for portability:

```json
{
  "PostToolUse": [{"command": "python -m esass.hooks.post_tool_use", "timeout": 5000}],
  "SessionStart": [{"command": "python -m esass.hooks.session_start", "timeout": 10000}]
}
```

### Config Chain

`load_config()` in `src/esass/config.py` resolves config from:

1. `$ESASS_CONFIG` env var
2. `.esass/config.yaml` (project-local)
3. `~/.esass/config.yaml` (global)
4. Built-in defaults

Data directory defaults to `.esass/data/` in the project root.

### Import Conventions

All imports use the `esass.*` namespace:

```python
from esass.config import load_config, get_data_dir
from esass.probes.base import FilteringProbe, ProbeContext
from esass.mcp.ollama_client import OllamaClient
from esass.mcp.utils import CircuitBreaker, retry_async
```

MCP config is at `esass.mcp.mcp_config` (renamed from `config.py` to avoid clash with `esass.config`).

### 3-Tier LLM Routing

| Tier | Client | Circuit Breaker | When |
|------|--------|----------------|------|
| Local (Ollama) | `ollama_client.py` | 3 failures / 30s recovery | score >= 0.7 |
| HuggingFace | `huggingface_client.py` | 5 failures / 60s recovery | 0.4 <= score < 0.7 |
| Claude | passthrough | none | score < 0.4 |

### Probe System

10 probes observe every tool call and produce structured log entries:

- ToolCallProbe, ToolSequenceDetector
- ReasoningProbe, CausalReasoningProbe
- DecisionProbe, TradeoffAnalysisProbe
- CalibrationProbe, InsightProbe
- ErrorRecoveryProbe, StrategyShiftProbe
- ScopeExpansionProbe, ReliabilityProbe
- FieldBoundaryProbe, LatencyProbe, LogicLoopProbe

All probes extend `FilteringProbe` from `src/esass/probes/base.py`. Probes must never crash the system -- errors are logged and swallowed.

## Common Tasks

### Add ESASS to a new project

```bash
cd my-project
esass init                    # basic setup
esass init --enable-mcp       # with local LLM support
```

### Run the dashboard manually

```bash
python -m esass.hooks.dashboard
```

### Simulate events for dashboard testing

```bash
python -m esass.hooks.simulate_events --speed 2 --loops 5
```

### Start Ollama for local LLM

```bash
ollama serve
ollama pull gemma4:31b
```

## Entry Points

| Command | Module |
|---------|--------|
| `esass` | `esass.cli.main:esass` |
| `esass-mcp-server` | `esass.mcp.server:main` |
