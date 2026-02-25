"""Ollama client for local LLM interactions.

Enhanced with:
- Connection pooling with limits
- Circuit breaker for failure protection
- Retry logic with exponential backoff
- Response caching for repeated queries
- Model warmup/keep-alive
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from esass.mcp.mcp_config import get_config
from esass.mcp.utils import (
    extract_json,
    clean_skill_name,
    CircuitBreaker,
    CircuitBreakerConfig,
    ResponseCache,
    RetryConfig,
    RetryStrategy,
    retry_async,
)

logger = logging.getLogger(__name__)


@dataclass
class OllamaResponse:
    """Response from Ollama API."""

    content: str
    model: str
    done: bool
    tool_calls: List[Dict[str, Any]] | None = None
    total_duration: int | None = None
    eval_count: int | None = None
    load_duration: int | None = None
    prompt_eval_count: int | None = None


class OllamaClient:
    """Client for interacting with Ollama API.

    Features:
    - Connection pooling with configurable limits
    - Circuit breaker to prevent cascading failures
    - Retry with exponential backoff
    - Response caching for identical requests
    - Model keep-alive to reduce cold starts
    """

    def __init__(
        self,
        endpoint: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
        max_connections: int = 10,
        enable_cache: bool = True,
        cache_ttl: float = 300.0,
    ):
        config = get_config()
        self.endpoint = endpoint or config.ollama_endpoint
        self.model = model or config.ollama_model
        self.timeout = timeout or config.ollama_timeout_seconds
        self.max_connections = max_connections

        self._client: httpx.AsyncClient | None = None
        self._last_health_check: float = 0
        self._health_check_interval = 30.0  # seconds
        self._is_healthy: bool | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

        # Circuit breaker for failure protection
        self._circuit = CircuitBreaker(
            "ollama",
            CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout_seconds=30.0,
            ),
        )

        # Response cache
        self._cache: ResponseCache | None = None
        if enable_cache:
            self._cache = ResponseCache(
                max_size=50,
                default_ttl_seconds=cache_ttl,
            )

        # Retry configuration
        self._retry_config = RetryConfig(
            max_attempts=3,
            base_delay_seconds=1.0,
            max_delay_seconds=10.0,
            strategy=RetryStrategy.EXPONENTIAL,
            retryable_exceptions=(httpx.TimeoutException, httpx.ConnectError),
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with connection pooling."""
        current_loop = asyncio.get_running_loop()
        if self._client is None or self._client.is_closed or self._loop != current_loop:
            limits = httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=5,
                keepalive_expiry=30.0,
            )
            self._client = httpx.AsyncClient(
                base_url=self.endpoint,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
                limits=limits,
            )
            self._loop = current_loop
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def is_available(self) -> bool:
        """Check if Ollama is available and the model is loaded.

        Uses cached health status for frequent checks.
        """
        now = time.time()

        # Return cached status if recent
        if (
            self._is_healthy is not None
            and now - self._last_health_check < self._health_check_interval
        ):
            return self._is_healthy

        try:
            client = await self._get_client()
            response = await client.get("/api/tags", timeout=5.0)

            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                model_base = self.model.split(":")[0]
                self._is_healthy = any(model_base in m for m in models)
            else:
                self._is_healthy = False

        except Exception as e:
            logger.debug(f"Ollama availability check failed: {e}")
            self._is_healthy = False

        self._last_health_check = now
        return self._is_healthy

    async def warmup(self) -> bool:
        """Warm up the model to reduce first-request latency.

        Sends a minimal request to load the model into memory.
        """
        try:
            client = await self._get_client()
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": False,
                "options": {"num_predict": 1},  # Minimal generation
            }

            response = await client.post("/api/chat", json=payload, timeout=30.0)
            success = response.status_code == 200

            if success:
                logger.info(f"Model {self.model} warmed up successfully")
            return success

        except Exception as e:
            logger.warning(f"Model warmup failed: {e}")
            return False

    async def keep_alive(self, duration_minutes: int = 5) -> bool:
        """Keep model loaded in memory.

        Args:
            duration_minutes: How long to keep model loaded

        Returns:
            True if successful
        """
        try:
            client = await self._get_client()
            payload = {
                "model": self.model,
                "keep_alive": f"{duration_minutes}m",
            }

            response = await client.post("/api/generate", json=payload)
            return response.status_code == 200

        except Exception as e:
            logger.debug(f"Keep-alive failed: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        tools: List[Dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        use_cache: bool = True,
    ) -> OllamaResponse:
        """Generate a response from the model.

        Args:
            prompt: The user prompt
            system: Optional system message
            tools: Optional list of tool definitions for function calling
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            use_cache: Whether to use response cache

        Returns:
            OllamaResponse with the generated content

        Raises:
            RuntimeError: If circuit is open
            httpx.HTTPError: On request failure after retries
        """
        # Check circuit breaker
        if not self._circuit.can_execute():
            raise RuntimeError(
                f"Circuit breaker open for Ollama - service appears unavailable"
            )

        # Check cache
        if use_cache and self._cache:
            cache_key = self._cache.make_key(
                "generate", prompt=prompt, system=system, model=self.model
            )
            if cached := self._cache.get(cache_key):
                logger.debug("Cache hit for generate request")
                return cached

        async def _do_generate() -> OllamaResponse:
            client = await self._get_client()

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            payload: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                },
            }

            if max_tokens:
                payload["options"]["num_predict"] = max_tokens

            if tools:
                payload["tools"] = tools

            logger.debug(f"Ollama request: {len(prompt)} chars, temp={temperature}")

            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()

            data = response.json()
            message = data.get("message", {})

            return OllamaResponse(
                content=message.get("content", ""),
                model=data.get("model", self.model),
                done=data.get("done", True),
                tool_calls=message.get("tool_calls"),
                total_duration=data.get("total_duration"),
                eval_count=data.get("eval_count"),
                load_duration=data.get("load_duration"),
                prompt_eval_count=data.get("prompt_eval_count"),
            )

        try:
            result = await retry_async(_do_generate, self._retry_config)
            self._circuit.record_success()

            # Cache successful result
            if use_cache and self._cache:
                self._cache.set(cache_key, result)

            return result

        except Exception as e:
            self._circuit.record_failure()
            raise

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (for semantic clustering).

        Falls back to nomic-embed-text if available.
        """
        try:
            client = await self._get_client()
            payload = {
                "model": "nomic-embed-text",
                "prompt": text,
            }

            response = await client.post("/api/embeddings", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])

        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")
            return []

    async def execute_skill(
        self,
        skill_name: str,
        skill_description: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a skill using the local model.

        Args:
            skill_name: Name of the skill to execute
            skill_description: Description/implementation summary
            context: Execution context (files, parameters, etc.)

        Returns:
            Dict with execution result including:
            - actions: List of tool actions to take
            - reasoning: Explanation of approach
            - success: Whether execution planning succeeded
            - tokens: Token count (if available)
        """
        system_prompt = """You are a skill executor. Given a skill description and context,
determine what actions to take and return a structured JSON response.

Respond in JSON format:
{
    "actions": [{"tool": "...", "params": {...}}],
    "reasoning": "...",
    "success": true/false
}"""

        prompt = f"""Execute skill: {skill_name}

Description: {skill_description}

Context:
{json.dumps(context, indent=2)}

Determine the appropriate actions and respond with a JSON execution plan."""

        try:
            response = await self.generate(
                prompt,
                system=system_prompt,
                temperature=0.3,  # Lower temperature for more consistent JSON
                use_cache=False,  # Don't cache skill executions
            )

            result = extract_json(response.content)

            # Ensure required fields
            if "success" not in result:
                result["success"] = "error" not in result

            result["model"] = response.model
            result["tokens"] = response.eval_count

            return result

        except Exception as e:
            logger.error(f"Skill execution failed: {e}")
            return {
                "actions": [],
                "reasoning": str(e),
                "success": False,
                "error": str(e),
            }

    async def generate_skill_name(
        self,
        pattern_sequence: str,
        tags: List[str],
    ) -> str:
        """Generate a semantic skill name from a pattern sequence.

        Args:
            pattern_sequence: e.g., "Read(python) -> Grep(search) -> Edit(python)"
            tags: Associated tags

        Returns:
            A semantic skill name like "python_search_refactor_skill"
        """
        prompt = f"""Generate a concise, semantic skill name for this pattern:

Pattern: {pattern_sequence}
Tags: {", ".join(tags) if tags else "none"}

Requirements:
- Use snake_case
- End with _skill
- Be descriptive but concise (3-5 words)
- Capture the primary action and context

Respond with ONLY the skill name, nothing else."""

        try:
            response = await self.generate(
                prompt,
                temperature=0.3,
                max_tokens=20,
            )
            return clean_skill_name(response.content)

        except Exception as e:
            logger.warning(f"Skill name generation failed: {e}")
            fallback = f"pattern_{hash(pattern_sequence) % 10000:04x}_skill"
            return fallback

    async def analyze_pattern(
        self,
        pattern_sequence: str,
        support: int,
        confidence: float,
    ) -> Dict[str, Any]:
        """Analyze a pattern for semantic meaning and clustering.

        Args:
            pattern_sequence: The tool sequence pattern
            support: How many times this pattern occurred
            confidence: Confidence score

        Returns:
            Analysis with semantic category, description, and suggested name
        """
        prompt = f"""Analyze this tool usage pattern:

Pattern: {pattern_sequence}
Occurrences: {support}
Confidence: {confidence:.1%}

Provide analysis in JSON format:
{{
    "category": "one of: file_modification, search_navigation, git_workflow, testing, documentation, configuration",
    "description": "what this pattern accomplishes",
    "suggested_name": "semantic_skill_name",
    "is_meaningful": true/false
}}"""

        try:
            response = await self.generate(prompt, temperature=0.3)
            analysis = extract_json(response.content)

            # Ensure required fields
            if "category" not in analysis:
                analysis["category"] = "unknown"
            if "is_meaningful" not in analysis:
                analysis["is_meaningful"] = False

            return analysis

        except Exception as e:
            logger.warning(f"Pattern analysis failed: {e}")
            return {
                "category": "unknown",
                "description": str(e),
                "suggested_name": f"pattern_{hash(pattern_sequence) % 10000:04x}_skill",
                "is_meaningful": False,
                "error": str(e),
            }

    def get_circuit_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return self._circuit.get_status()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self._cache:
            return self._cache.get_stats()
        return {"enabled": False}


# Singleton instance
_client: OllamaClient | None = None


async def get_ollama_client() -> OllamaClient:
    """Get the global Ollama client instance."""
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client


def reset_ollama_client() -> None:
    """Reset the global client (for testing)."""
    global _client
    _client = None
