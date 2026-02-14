"""ESASS integrations with external services."""

from esass_prototype.integrations.local_llm import (
    LocalLLMClient,
    get_local_llm_client,
    is_local_llm_available,
)

__all__ = [
    "LocalLLMClient",
    "get_local_llm_client",
    "is_local_llm_available",
]
