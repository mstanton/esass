---
name: local-llm-executor
description: |
  Executes ESASS skills using local FunctionGemma model via Ollama.
  Falls back to HuggingFace Inference API, then Claude for complex tasks.
  Optimized for cost savings on routine skill execution.
version: 0.1.0
genesis:
  type: manual
  confidence: 1.0
  created: 2026-02-09
triggers:
  - trigger_type: intent_match
    pattern: execute skill locally
    confidence_threshold: 0.8
  - trigger_type: context
    pattern: cost_optimization,local_inference
    confidence_threshold: 0.8
capabilities:
  - skill_execution
  - pattern_analysis
  - cost_optimization
---

# Local LLM Skill Executor

Executes ESASS skills using a 3-tier local-first approach for maximum cost savings.

## Tier Hierarchy

1. **Tier 1: Local (Ollama/Gemma3:12b)** - Primary, ~$0 cost
   - Fast inference on local GPU
   - Suitable for: skill execution, code generation, file operations

2. **Tier 2: HuggingFace Inference API** - Fallback, ~5x cheaper than Claude
   - Cloud-hosted Mistral-7B
   - Suitable for: complex analysis, longer context

3. **Tier 3: Claude** - Passthrough for critical tasks
   - Full frontier model capabilities
   - Suitable for: architecture design, security review

## Prerequisites

```bash
# Install Ollama
winget install ollama.ollama

# Pull FunctionGemma model
ollama pull gemma3:12b

# Start Ollama server
ollama serve
```

## Environment Variables

```bash
# Required for Tier 2 fallback
export HF_TOKEN="your_huggingface_token"

# Optional configuration
export OLLAMA_ENDPOINT="http://localhost:11434"
export OLLAMA_MODEL="gemma3:12b"
export LOCAL_LLM_ENABLED="true"
```

## MCP Tools Provided

### execute_skill

Execute an ESASS skill with automatic tier routing.

```json
{
  "skill_name": "python_workflow_skill",
  "skill_description": "Read Python files, analyze, and edit",
  "capabilities": ["file_operations", "tool_orchestration"],
  "context": {"files": ["main.py"], "action": "refactor"}
}
```

### analyze_pattern

Analyze a tool usage pattern for semantic clustering.

```json
{
  "pattern_sequence": "Read(python) -> Grep(search) -> Edit(python)",
  "support": 15,
  "confidence": 0.95
}
```

### generate_skill_name

Generate a semantic skill name from a pattern.

```json
{
  "pattern_sequence": "Read(python) -> Grep -> Edit",
  "tags": ["python", "refactor", "edit"]
}
```

## Routing Logic

Skills are routed based on:

1. **Capability scores** - file_operations (0.95), security (0.1)
2. **Token estimates** - >2048 tokens routes to HuggingFace
3. **Availability** - Automatic fallback if tier unavailable

## Error Handling

- Automatic retry with exponential backoff
- Graceful fallback through tier chain
- Failure tracking for adaptive routing

## Performance

- **Local inference**: ~50-100ms per token on GPU
- **HuggingFace**: ~500ms-2s per request
- **Cost savings**: ~70% reduction vs Claude-only
