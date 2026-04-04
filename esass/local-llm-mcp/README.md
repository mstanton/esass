# Local LLM MCP Server for ESASS

A Model Context Protocol (MCP) server that provides local LLM inference for ESASS skill execution, reducing Claude API costs by 70-99%.

## Overview

This system implements a **hardened 3-tier hybrid architecture** with enterprise-grade reliability:

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server (server.py)                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │   Input     │ │    Rate     │ │   Model Warmup      │   │
│  │ Validation  │ │  Limiting   │ │   (on startup)      │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    ▼                    ▼                    ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ Tier 1: Local  │ │ Tier 2: HF     │ │ Tier 3: Claude │
│ (Ollama)       │ │ (Inference API)│ │ (Passthrough)  │
├────────────────┤ ├────────────────┤ ├────────────────┤
│ Circuit Breaker│ │ Circuit Breaker│ │ Always         │
│ (3 fail/30s)   │ │ (5 fail/60s)   │ │ Available      │
├────────────────┤ ├────────────────┤ └────────────────┘
│ Retry (3x exp) │ │ Retry (3x exp) │
├────────────────┤ └────────────────┘
│ Response Cache │
│ (50 items/5m)  │
└────────────────┘
```

## Features

### Core Features

- **3-Tier Routing**: Automatic routing based on task complexity
- **Cost Tracking**: Per-execution logging with savings analytics
- **Adaptive Learning**: Learns from failures to improve routing
- **Skill Execution**: Run ESASS skills via local LLM
- **Pattern Analysis**: Semantic analysis of tool usage patterns
- **Skill Naming**: Generate meaningful names from patterns

### Hardening Features (v2.0)

- **Circuit Breaker**: Prevents cascading failures when a tier is unhealthy
- **Retry Logic**: Exponential backoff with jitter for transient failures
- **Rate Limiting**: Token bucket limiter (30 req/min, burst of 10)
- **Response Caching**: LRU cache with TTL for repeated queries
- **Input Validation**: Full validation with size limits and sanitization
- **Health Check Caching**: 30-second cache to reduce API calls
- **Model Warmup**: Automatic warmup on server startup
- **Memory Bounds**: Configurable limits on in-memory logs

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
# Or for better quality:
ollama pull gemma4:26b
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
| `OLLAMA_MODEL` | `gemma4:26b` | Model to use |
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

**Response:**

```json
{
  "success": true,
  "tier_used": "local",
  "fallback_used": false,
  "routing_reason": "capability",
  "routing_details": "Capability score 0.93 routes to local",
  "content": {
    "actions": [{"tool": "Read", "params": {"file": "main.py"}}],
    "reasoning": "...",
    "success": true
  },
  "tokens_used": 131,
  "error": null
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
  "success": true,
  "tier_used": "local",
  "analysis": {
    "category": "file_modification",
    "description": "Workflow for adding methods to Python classes",
    "suggested_name": "python_method_addition_skill",
    "is_meaningful": true
  }
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
  "success": true,
  "skill_name": "config_edit_restart_skill",
  "tier_used": "local"
}
```

### check_availability

Check tier availability with circuit breaker and cache status.

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
  "circuit_breakers": {
    "ollama": {"name": "ollama", "state": "closed", "failure_count": 0},
    "huggingface": {"name": "huggingface", "state": "closed", "failure_count": 0}
  },
  "cache": {
    "ollama": {"size": 5, "max_size": 50, "total_hits": 12}
  },
  "rate_limit": {
    "available_tokens": 8.5,
    "capacity": 10,
    "rate_per_second": 0.5
  },
  "config": {
    "ollama_endpoint": "http://localhost:11434",
    "ollama_model": "gemma4:26b"
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

### get_adaptive_status

Get adaptive routing status and learned patterns.

```json
{
  "skill_name": "flaky_skill",
  "capabilities": ["tool_orchestration"]
}
```

## Hardening Features

### Circuit Breaker

Protects against cascading failures when a tier becomes unhealthy.

| Tier | Failure Threshold | Recovery Timeout | Half-Open Max |
|------|-------------------|------------------|---------------|
| Ollama | 3 failures | 30 seconds | 3 calls |
| HuggingFace | 5 failures | 60 seconds | 3 calls |

**States:**

- `CLOSED`: Normal operation, requests pass through
- `OPEN`: Tier unhealthy, requests fail fast
- `HALF_OPEN`: Testing recovery, limited requests allowed

### Retry Logic

Automatic retry with exponential backoff for transient failures.

| Setting | Value |
|---------|-------|
| Max Attempts | 3 |
| Base Delay | 1-2 seconds |
| Max Delay | 10-30 seconds |
| Strategy | Exponential with jitter |
| Retryable | Timeout, Connection errors |

### Rate Limiting

Token bucket rate limiter to prevent abuse.

| Setting | Value |
|---------|-------|
| Rate | 30 requests/minute |
| Burst | 10 requests |
| Exempt | Status queries (check_availability, get_routing_stats) |

### Response Cache

LRU cache with TTL for repeated identical requests.

| Setting | Value |
|---------|-------|
| Max Size | 50 entries |
| Default TTL | 5 minutes |
| Eviction | LRU (Least Recently Used) |

### Input Validation

All requests are validated before processing.

| Field | Limits |
|-------|--------|
| `skill_name` | Max 200 chars, non-empty |
| `skill_description` | Max 10,000 chars, non-empty |
| `capabilities` | Max 20 items, each max 100 chars |
| `context` | Max 50KB when serialized |

### Model Warmup

On server startup:

1. Check Ollama availability
2. Send minimal warmup request to load model
3. Set 5-minute keep-alive to prevent model unloading

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
├── ollama_client.py       # Ollama API client (hardened)
├── huggingface_client.py  # HuggingFace API client (hardened)
├── cost_tracker.py        # Cost analytics
├── adaptive_router.py     # Learning-based routing
├── utils.py               # Shared utilities (NEW)
│   ├── extract_json()     # Robust JSON extraction
│   ├── clean_skill_name() # Skill name sanitization
│   ├── CircuitBreaker     # Circuit breaker pattern
│   ├── ResponseCache      # LRU cache with TTL
│   ├── RateLimiter        # Token bucket limiter
│   ├── retry_async()      # Exponential backoff retry
│   └── validate_skill_request()  # Input validation
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── test_hardened.py       # Hardening unit tests (49 tests)
├── test_comprehensive.py  # Integration tests (5 tests)
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
        "OLLAMA_MODEL": "gemma4:26b"
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
cd esass/local-llm-mcp

# Hardening unit tests (49 tests)
pytest test_hardened.py -v

# Integration tests (5 tests)
pytest test_comprehensive.py -v

# All tests (54 total)
pytest test_hardened.py test_comprehensive.py -v
```

### Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_hardened.py` | 49 | Utils, Circuit Breaker, Cache, Rate Limiter, Validation, Retry |
| `test_comprehensive.py` | 5 | Full integration, Cost tracking, Adaptive learning |

### Expected Output

```
============================= test session starts =============================
collected 54 items

test_hardened.py .................................................       [ 90%]
test_comprehensive.py .....                                              [100%]

============================= 54 passed in 35.64s =============================
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
ollama pull gemma4:26b
```

### Circuit Breaker Open

If you see "Circuit breaker open" errors:

1. Check if Ollama is running: `curl http://localhost:11434/api/tags`
2. Wait 30-60 seconds for automatic recovery
3. Or restart the MCP server to reset circuit breakers

### Rate Limit Exceeded

If you see "Rate limit exceeded" errors:

- Wait a few seconds before retrying
- Check `rate_limit` status via `check_availability`
- Status queries are exempt from rate limiting

### JSON Parsing Errors

The system handles markdown-wrapped JSON responses automatically via `extract_json()`. If issues persist:

- Check model output format
- Verify prompt templates in `ollama_client.py`

### High Latency

- gemma4:26b typically responds in 2-4 seconds
- gemma4:26b typically responds in 5-10 seconds
- For faster responses, consider `gemma4:26b` (less capable)
- Ensure GPU acceleration is enabled in Ollama
- First request may be slower (model loading)

### Memory Usage

In-memory execution logs are bounded to 1000 entries by default. Older logs are persisted to disk in `data/cost_tracking/`.

## Model Recommendations

| Model | Size | Speed | Capability | Use Case |
|-------|------|-------|------------|----------|
| gemma4:26b | 3.3GB | 2-4s | Good | Default choice |
| gemma4:26b | 8.1GB | 5-10s | Better | Complex analysis |
| functiongemma | 300MB | <1s | Limited | Simple tasks only |

## Changelog

### v2.0 (2026-02-11) - Hardening Release

- Added `utils.py` with shared utilities
- Implemented circuit breaker pattern for Ollama and HuggingFace
- Added exponential backoff retry logic
- Added token bucket rate limiting
- Added LRU response cache with TTL
- Added input validation with size limits
- Added model warmup on server startup
- Added health check caching (30s)
- Added memory bounds for execution logs
- Centralized JSON extraction logic
- Added 49 unit tests for hardening features
- Updated comprehensive tests with pytest markers

### v1.0 (2026-02-10) - Initial Release

- 3-tier routing (Local, HuggingFace, Claude)
- Cost tracking and analytics
- Adaptive routing with learning
- MCP server implementation

## License

Part of the ESASS project. See main repository for license.
