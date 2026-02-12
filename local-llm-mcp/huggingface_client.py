"""HuggingFace Inference API client for Tier 2 fallback.

Enhanced with:
- Connection pooling with limits
- Circuit breaker for failure protection
- Retry logic with exponential backoff
- Better error classification
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from config import get_config
from utils import (
    extract_json,
    clean_skill_name,
    CircuitBreaker,
    CircuitBreakerConfig,
    RetryConfig,
    RetryStrategy,
    retry_async,
)

logger = logging.getLogger(__name__)


class HuggingFaceError(Exception):
    """Base exception for HuggingFace errors."""
    pass


class HuggingFaceRateLimitError(HuggingFaceError):
    """Rate limit exceeded."""
    pass


class HuggingFaceModelLoadingError(HuggingFaceError):
    """Model is loading."""
    pass


@dataclass
class HuggingFaceResponse:
    """Response from HuggingFace Inference API."""
    content: str
    model: str
    usage: Dict[str, int] | None = None


class HuggingFaceClient:
    """Client for HuggingFace Inference API (Tier 2 fallback).

    Features:
    - Connection pooling with configurable limits
    - Circuit breaker to prevent cascading failures
    - Retry with exponential backoff
    - Proper error classification (rate limits, model loading, etc.)
    """

    INFERENCE_API_URL = "https://api-inference.huggingface.co/models"

    def __init__(
        self,
        model: str | None = None,
        token: str | None = None,
        timeout: int | None = None,
        max_connections: int = 5,
    ):
        config = get_config()
        self.model = model or config.hf_model
        self.token = token or config.hf_token
        self.timeout = timeout or config.hf_timeout_seconds
        self.max_connections = max_connections

        self._client: httpx.AsyncClient | None = None
        self._is_healthy: bool | None = None
        self._last_health_check: float = 0

        if not self.token:
            logger.warning("HF_TOKEN not set - HuggingFace client may not work")

        # Circuit breaker
        self._circuit = CircuitBreaker(
            "huggingface",
            CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=2,
                timeout_seconds=60.0,  # Longer timeout for cloud service
            )
        )

        # Retry configuration - include rate limit errors
        self._retry_config = RetryConfig(
            max_attempts=3,
            base_delay_seconds=2.0,
            max_delay_seconds=30.0,
            strategy=RetryStrategy.EXPONENTIAL,
            retryable_exceptions=(
                httpx.TimeoutException,
                httpx.ConnectError,
                HuggingFaceModelLoadingError,
            ),
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with connection pooling."""
        if self._client is None:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            limits = httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=3,
                keepalive_expiry=60.0,
            )

            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
                limits=limits,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def is_available(self) -> bool:
        """Check if HuggingFace API is available."""
        if not self.token:
            return False

        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.INFERENCE_API_URL}/{self.model}",
                params={"wait_for_model": "false"},
                timeout=10.0,
            )

            if response.status_code == 200:
                self._is_healthy = True
                return True
            elif response.status_code == 503:
                # Model loading - technically available but slow
                self._is_healthy = True
                return True
            else:
                self._is_healthy = False
                return False

        except Exception as e:
            logger.debug(f"HuggingFace availability check failed: {e}")
            self._is_healthy = False
            return False

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error responses with proper classification."""
        if response.status_code == 429:
            raise HuggingFaceRateLimitError("Rate limit exceeded")
        elif response.status_code == 503:
            try:
                data = response.json()
                if "loading" in str(data).lower():
                    raise HuggingFaceModelLoadingError("Model is loading")
            except json.JSONDecodeError:
                pass
            raise HuggingFaceError(f"Service unavailable: {response.status_code}")
        elif response.status_code >= 400:
            raise HuggingFaceError(f"HTTP {response.status_code}: {response.text[:200]}")

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
    ) -> HuggingFaceResponse:
        """Generate a response using HuggingFace Inference API.

        Args:
            prompt: The user prompt
            system: Optional system message (prepended to prompt)
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            HuggingFaceResponse with the generated content

        Raises:
            RuntimeError: If circuit is open
            HuggingFaceError: On API errors
        """
        # Check circuit breaker
        if not self._circuit.can_execute():
            raise RuntimeError(
                "Circuit breaker open for HuggingFace - service appears unavailable"
            )

        async def _do_generate() -> HuggingFaceResponse:
            client = await self._get_client()

            # Format prompt for instruction-following models
            full_prompt = prompt
            if system:
                full_prompt = f"[INST] {system}\n\n{prompt} [/INST]"

            payload = {
                "inputs": full_prompt,
                "parameters": {
                    "max_new_tokens": max_new_tokens,
                    "temperature": temperature,
                    "return_full_text": False,
                },
                "options": {
                    "wait_for_model": True,  # Wait if model is loading
                },
            }

            logger.debug(f"HuggingFace request to {self.model}")

            response = await client.post(
                f"{self.INFERENCE_API_URL}/{self.model}",
                json=payload,
            )

            self._handle_error_response(response)

            data = response.json()

            # Handle different response formats
            if isinstance(data, list) and len(data) > 0:
                content = data[0].get("generated_text", "")
            elif isinstance(data, dict):
                content = data.get("generated_text", str(data))
            else:
                content = str(data)

            return HuggingFaceResponse(
                content=content,
                model=self.model,
            )

        try:
            result = await retry_async(_do_generate, self._retry_config)
            self._circuit.record_success()
            return result

        except HuggingFaceRateLimitError:
            # Don't count rate limits against circuit breaker
            raise

        except Exception as e:
            self._circuit.record_failure()
            raise

    async def execute_skill(
        self,
        skill_name: str,
        skill_description: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a skill using HuggingFace model (Tier 2 fallback).

        Args:
            skill_name: Name of the skill to execute
            skill_description: Description/implementation summary
            context: Execution context

        Returns:
            Dict with execution result
        """
        system_prompt = """You are a skill executor. Analyze the skill and context,
then return a JSON response with execution plan.

Format:
{
    "actions": [{"tool": "...", "params": {...}}],
    "reasoning": "...",
    "success": true/false
}"""

        prompt = f"""Execute skill: {skill_name}

Description: {skill_description}

Context:
{json.dumps(context, indent=2)}

Return JSON execution plan."""

        try:
            response = await self.generate(
                prompt,
                system=system_prompt,
                temperature=0.3,
            )

            result = extract_json(response.content)

            # Ensure required fields
            if "success" not in result:
                result["success"] = "error" not in result

            result["model"] = response.model
            result["tier"] = "huggingface"

            return result

        except Exception as e:
            logger.error(f"HuggingFace skill execution failed: {e}")
            return {
                "actions": [],
                "reasoning": str(e),
                "success": False,
                "error": str(e),
                "tier": "huggingface",
            }

    async def generate_skill_name(
        self,
        pattern_sequence: str,
        tags: List[str],
    ) -> str:
        """Generate a semantic skill name (Tier 2 fallback).

        Args:
            pattern_sequence: Tool sequence pattern
            tags: Associated tags

        Returns:
            Semantic skill name
        """
        prompt = f"""Generate a concise skill name for this pattern:

Pattern: {pattern_sequence}
Tags: {', '.join(tags) if tags else 'none'}

Requirements: snake_case, ends with _skill, 3-5 words.
Reply with ONLY the skill name."""

        try:
            response = await self.generate(
                prompt,
                max_new_tokens=30,
                temperature=0.3,
            )
            return clean_skill_name(response.content)

        except Exception as e:
            logger.warning(f"HuggingFace skill name generation failed: {e}")
            return f"pattern_{hash(pattern_sequence) % 10000:04x}_skill"

    async def analyze_pattern(
        self,
        pattern_sequence: str,
        support: int,
        confidence: float,
    ) -> Dict[str, Any]:
        """Analyze a pattern semantically (Tier 2 fallback).

        Args:
            pattern_sequence: The tool sequence pattern
            support: Occurrence count
            confidence: Confidence score

        Returns:
            Pattern analysis
        """
        prompt = f"""Analyze this tool pattern and return JSON:

Pattern: {pattern_sequence}
Occurrences: {support}
Confidence: {confidence:.1%}

JSON format:
{{
    "category": "file_modification|search_navigation|git_workflow|testing|documentation|configuration",
    "description": "what it does",
    "suggested_name": "skill_name",
    "is_meaningful": true/false
}}"""

        try:
            response = await self.generate(
                prompt,
                max_new_tokens=200,
                temperature=0.3,
            )

            analysis = extract_json(response.content)

            # Ensure required fields
            if "category" not in analysis:
                analysis["category"] = "unknown"
            if "is_meaningful" not in analysis:
                analysis["is_meaningful"] = False

            analysis["tier"] = "huggingface"
            return analysis

        except Exception as e:
            logger.warning(f"HuggingFace pattern analysis failed: {e}")
            return {
                "category": "unknown",
                "description": str(e),
                "suggested_name": f"pattern_{hash(pattern_sequence) % 10000:04x}_skill",
                "is_meaningful": False,
                "tier": "huggingface",
                "error": str(e),
            }

    def get_circuit_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return self._circuit.get_status()


# Singleton instance
_client: HuggingFaceClient | None = None


async def get_huggingface_client() -> HuggingFaceClient:
    """Get the global HuggingFace client instance."""
    global _client
    if _client is None:
        _client = HuggingFaceClient()
    return _client


def reset_huggingface_client() -> None:
    """Reset the global client (for testing)."""
    global _client
    _client = None
