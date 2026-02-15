"""Configuration for the Local LLM MCP Server."""

import os
from dataclasses import dataclass, field
from typing import Dict, List
from enum import Enum


class Tier(Enum):
    """Execution tier for task routing."""
    LOCAL = "local"           # Ollama/FunctionGemma
    HUGGINGFACE = "huggingface"  # HF Inference API
    CLAUDE = "claude"         # Claude API (fallback/passthrough)


@dataclass
class LocalLLMConfig:
    """Configuration for local LLM integration."""

    # General settings
    enabled: bool = True
    debug: bool = False

    # Ollama settings (Tier 1)
    ollama_endpoint: str = "http://localhost:11434"
    ollama_model: str = "gemma3:12b"  # More capable than functiongemma for general tasks
    ollama_timeout_seconds: int = 60

    # HuggingFace settings (Tier 2)
    hf_model: str = "Qwen/Qwen2.5-7B-Instruct"
    hf_token: str = field(default_factory=lambda: os.environ.get("HF_TOKEN", ""))
    hf_timeout_seconds: int = 60

    # Routing settings
    enable_pattern_analysis: bool = True
    max_local_tokens: int = 2048
    fallback_on_error: bool = True

    # Task type routing rules
    tier_rules: Dict[str, str] = field(default_factory=lambda: {
        # Tier 1: Local (FunctionGemma)
        "skill_execution": "local",
        "pattern_embedding": "local",
        "code_generation": "local",
        "file_operations": "local",
        "test_writing": "local",
        "documentation": "local",

        # Tier 2: HuggingFace (fallback or medium complexity)
        "complex_analysis": "huggingface",
        "long_context": "huggingface",
        "code_review": "huggingface",

        # Tier 3: Claude (critical tasks - passthrough)
        "architecture_design": "claude",
        "security_review": "claude",
        "complex_reasoning": "claude",
    })

    # Capability to tier mapping for skills
    capability_tiers: Dict[str, float] = field(default_factory=lambda: {
        # Higher score = more suitable for local execution
        "tool_orchestration": 0.9,
        "file_operations": 0.95,
        "git_operations": 0.8,
        "testing": 0.85,
        "documentation": 0.9,
        "problem_analysis": 0.7,
        "decision_making": 0.6,
        "security": 0.1,  # Keep on Claude
    })

    @classmethod
    def from_env(cls) -> "LocalLLMConfig":
        """Create config from environment variables."""
        return cls(
            enabled=os.environ.get("LOCAL_LLM_ENABLED", "true").lower() == "true",
            debug=os.environ.get("LOCAL_LLM_DEBUG", "false").lower() == "true",
            ollama_endpoint=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434"),
            ollama_model=os.environ.get("OLLAMA_MODEL", "gemma3:12b"),
            ollama_timeout_seconds=int(os.environ.get("OLLAMA_TIMEOUT", "30")),
            hf_model=os.environ.get("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
            hf_token=os.environ.get("HF_TOKEN", ""),
            hf_timeout_seconds=int(os.environ.get("HF_TIMEOUT", "60")),
            enable_pattern_analysis=os.environ.get("ENABLE_PATTERN_ANALYSIS", "true").lower() == "true",
        )

    def get_tier_for_task(self, task_type: str) -> Tier:
        """Get the appropriate tier for a task type."""
        tier_name = self.tier_rules.get(task_type, "local")
        return Tier(tier_name)

    def get_tier_for_capability(self, capability: str) -> Tier:
        """Get tier based on skill capability score."""
        score = self.capability_tiers.get(capability, 0.5)
        if score >= 0.7:
            return Tier.LOCAL
        elif score >= 0.4:
            return Tier.HUGGINGFACE
        else:
            return Tier.CLAUDE


# Global config instance
_config: LocalLLMConfig | None = None


def get_config() -> LocalLLMConfig:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = LocalLLMConfig.from_env()
    return _config


def set_config(config: LocalLLMConfig) -> None:
    """Set the global config instance."""
    global _config
    _config = config
