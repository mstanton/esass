# Local LLM MCP Server for ESASS

A Model Context Protocol (MCP) server that provides local LLM inference for ESASS skill execution, reducing Claude API costs by 70-99%.

## Overview

This system implements a 3-tier hybrid architecture:

```
┌─────────────────────────────────────────────────────────────┐
│ Tier 3: Claude (Passthrough)                                │
│   - Complex reasoning, architecture, security review        │
│   - Used when local tiers fail or for critical tasks        │
│   - Cost: $15-25 per million tokens                         │
└─────────────────────────────────────────────────────────────┘
                            ↑ Fallback
┌─────────────────────────────────────────────────────────────┐
│ Tier 2: HuggingFace Inference API                           │
│   - Cloud-hosted models (Mistral-7B)                        │
│   - Fallback when local unavailable                         │
│   - Cost: ~$1-2 per million tokens                          │
└─────────────────────────────────────────────────────────────┘
                            ↑ Fallback
┌─────────────────────────────────────────────────────────────┐
│ Tier 1: Local (Ollama + gemma3:4b)                          │
│   - Primary execution tier                                  │
│   - Handles 70%+ of tasks                                   │
│   - Cost: ~$0 (local compute only)                          │
└─────────────────────────────────────────────────────────────┘
```

## Features

- **3-Tier Routing**: Automatic routing based on task complexity
- **Cost Tracking**: Per-execution logging with savings analytics
- **Adaptive Learning**: Learns from failures to improve routing
- **Skill Execution**: Run ESASS skills via local LLM
- **Pattern Analysis**: Semantic analysis of tool usage patterns
- **Skill Naming**: Generate meaningful names from patterns

## Quick Start

### 1. Install Ollama

```bash
# Windows
winget install ollama.ollama

# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Pull the Model

```bash
ollama pull gemma3:4b
```

### 3. Start Ollama

```bash
ollama serve
```

### 4. Install Dependencies

```bash
cd esass/local-llm-mcp
pip install -r requirements.txt
```

### 5. Run the MCP Server

```bash
python server.py
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_ENDPOINT` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `gemma3:4b` | Model to use |
| `OLLAMA_TIMEOUT` | `60` | Request timeout (seconds) |
| `HF_TOKEN` | - | HuggingFace API token |
| `HF_MODEL` | `mistralai/Mistral-7B-Instruct-v0.3` | HF model |
| `LOCAL_LLM_ENABLED` | `true` | Enable/disable local LLM |
| `COST_TRACKING_DIR` | `./data/cost_tracking` | Cost data directory |
| `ADAPTIVE_ROUTING_DIR` | `./data/adaptive_routing` | Learning data directory |

### Capability Routing

Tasks are routed based on capability scores:

| Capability | Score | Default Tier |
|------------|-------|--------------|
| `file_operations` | 0.95 | Local |
| `tool_orchestration` | 0.90 | Local |
| `documentation` | 0.90 | Local |
| `testing` | 0.85 | Local |
| `git_operations` | 0.80 | Local |
| `problem_analysis` | 0.70 | Local |
| `decision_making` | 0.60 | HuggingFace |
| `security` | 0.10 | Claude |

**Routing Rules:**
- Score >= 0.7 → Local
- Score >= 0.4 → HuggingFace
- Score < 0.4 → Claude

## MCP Tools

### execute_skill

Execute an ESASS skill with automatic tier routing.

```json
{
  "skill_name": "python_refactor_skill",
  "skill_description": "Refactor Python function for readability",
  "capabilities": ["file_operations", "tool_orchestration"],
  "context": {"file": "main.py", "function": "process_data"}
}
```

### analyze_pattern

Analyze a tool usage pattern for semantic meaning.

```json
{
  "pattern_sequence": "Read(python) -> Grep(class) -> Edit(add_method)",
  "support": 15,
  "confidence": 0.85
}
```

**Returns:**
```json
{
  "category": "file_modification",
  "description": "Workflow for adding methods to Python classes",
  "suggested_name": "python_method_addition_skill",
  "is_meaningful": true
}
```

### generate_skill_name

Generate a semantic skill name from a pattern.

```json
{
  "pattern_sequence": "Read(config) -> Edit -> Bash(restart)",
  "tags": ["configuration", "deployment"]
}
```

**Returns:**
```json
{
  "skill_name": "config_restart_skill",
  "tier_used": "local"
}
```

### check_availability

Check which tiers are available.

```json
{}
```

**Returns:**
```json
{
  "availability": {
    "local": true,
    "huggingface": false,
    "claude": true
  },
  "config": {
    "ollama_endpoint": "http://localhost:11434",
    "ollama_model": "gemma3:4b"
  }
}
```

### get_cost_dashboard

Get cost tracking analytics.

```json
{}
```

**Returns:**
```json
{
  "session_summary": {
    "total_executions": 100,
    "tier_breakdown": {"local": 70, "huggingface": 20, "claude": 10},
    "total_cost": 0.25,
    "total_savings": 0.68,
    "savings_percentage": 73.5
  },
  "projection": {
    "projected_monthly_cost": 3.27,
    "projected_cost_if_all_claude": 27.74,
    "projected_monthly_savings": 24.47
  }
}
```

### get_full_analytics

Get comprehensive analytics including adaptive learning.

```json
{}
```

### get_adaptive_status

Get adaptive routing status and learned patterns.

```json
{
  "skill_name": "flaky_skill",
  "capabilities": ["tool_orchestration"]
}
```

## Cost Tracking

The system tracks every execution:

```
┌─────────────────────────────────────────────────────────────┐
│ Execution Log Entry                                         │
├─────────────────────────────────────────────────────────────┤
│ timestamp: 1707500000.0                                     │
│ skill_name: "python_refactor_skill"                         │
│ tier_requested: "local"                                     │
│ tier_used: "local"                                          │
│ fallback_used: false                                        │
│ success: true                                               │
│ tokens_used: 450                                            │
│ latency_ms: 2100                                            │
│ cost_actual: 0.000045                                       │
│ cost_if_claude: 0.00675                                     │
│ savings: 0.006705                                           │
└─────────────────────────────────────────────────────────────┘
```

### Cost per 1K Tokens

| Tier | Cost | Relative |
|------|------|----------|
| Local | $0.0001 | 1x |
| HuggingFace | $0.001 | 10x |
| Claude | $0.015 | 150x |

### Typical Savings

| Execution Mix | Monthly Cost | vs All Claude | Savings |
|---------------|--------------|---------------|---------|
| 100% Local | $0.30 | $45 | 99.3% |
| 70/20/10 | $3.27 | $27.74 | 88.2% |
| 50/30/20 | $8.10 | $45 | 82% |

## Adaptive Routing

The system learns from execution history:

### Automatic Demotion

When a skill fails consistently on a tier:
- After 3+ attempts with >50% failure rate
- Skill is demoted to next tier (Local → HF → Claude)
- Override lasts 1 week then resets

### Automatic Promotion

When a skill succeeds consistently:
- After 5+ successes with >90% success rate
- Override is removed, returns to default routing

### Example

```
Skill: "flaky_api_skill"

1. Initial: Routes to Local (default)
2. 4/7 local executions fail (57% failure rate)
3. System demotes to HuggingFace
4. Next calls route to HF automatically
5. After 1 week, override expires
6. System tries Local again
```

## File Structure

```
local-llm-mcp/
├── server.py              # MCP server entry point
├── config.py              # Configuration dataclasses
├── tier_router.py         # 3-tier routing logic
├── ollama_client.py       # Ollama API client
├── huggingface_client.py  # HuggingFace API client
├── cost_tracker.py        # Cost analytics
├── adaptive_router.py     # Learning-based routing
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── data/
    ├── cost_tracking/     # Execution logs (JSON)
    └── adaptive_routing/  # Learning data (JSON)
```

## Integration with Claude Code

### Register MCP Server

Add to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "local-llm-mcp": {
      "type": "stdio",
      "command": "python",
      "args": ["C:/workspace/ESASS/esass/local-llm-mcp/server.py"],
      "env": {
        "OLLAMA_ENDPOINT": "http://localhost:11434",
        "OLLAMA_MODEL": "gemma3:4b"
      }
    }
  }
}
```

### Usage in ESASS

The RecursiveLoopController uses local LLM for:
- Skill execution routing
- Pattern semantic analysis
- Skill name generation
- Pattern deduplication

## Testing

### Run All Tests

```bash
python test_phase5.py           # Phase 5 unit tests
python test_real_execution.py   # Real execution tests
python test_comprehensive.py    # Full integration tests
```

### Expected Output

```
============================================================
COMPREHENSIVE PHASE 5 TEST SUITE
============================================================
  multiple_executions: PASS
  adaptive_learning: PASS
  cost_projections: PASS
  real_ollama: PASS
  dashboard: PASS

Total: 5/5 tests passed
```

## Troubleshooting

### Ollama Not Available

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve
```

### Model Not Found

```bash
# List available models
ollama list

# Pull required model
ollama pull gemma3:4b
```

### JSON Parsing Errors

The system handles markdown-wrapped JSON responses. If issues persist:
- Check model output format
- Verify prompt templates in `ollama_client.py`

### High Latency

- gemma3:4b typically responds in 2-4 seconds
- For faster responses, consider `gemma3:1b` (less capable)
- Ensure GPU acceleration is enabled in Ollama

## Model Recommendations

| Model | Size | Speed | Capability | Use Case |
|-------|------|-------|------------|----------|
| gemma3:4b | 3.3GB | 2-4s | Good | Default choice |
| gemma3:12b | 8.1GB | 5-10s | Better | Complex analysis |
| functiongemma | 300MB | <1s | Limited | Simple tasks only |

## License

Part of the ESASS project. See main repository for license.
