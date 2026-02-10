"""ESASS Local LLM MCP Server.

Provides 3-tier skill execution with automatic fallback:
- Tier 1: Local (Ollama/FunctionGemma) - Free
- Tier 2: HuggingFace Inference API - Cheap
- Tier 3: Claude (passthrough) - Full capability
"""

from config import LocalLLMConfig, Tier, get_config, set_config
from ollama_client import OllamaClient, get_ollama_client
from huggingface_client import HuggingFaceClient, get_huggingface_client
from tier_router import TierRouter, get_router, RoutingResult, ExecutionResult

__version__ = "0.1.0"

__all__ = [
    "LocalLLMConfig",
    "Tier",
    "get_config",
    "set_config",
    "OllamaClient",
    "get_ollama_client",
    "HuggingFaceClient",
    "get_huggingface_client",
    "TierRouter",
    "get_router",
    "RoutingResult",
    "ExecutionResult",
]
