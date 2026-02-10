"""Ollama client for FunctionGemma model interactions."""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from config import get_config

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


class OllamaClient:
    """Client for interacting with Ollama API running FunctionGemma."""

    def __init__(
        self,
        endpoint: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ):
        config = get_config()
        self.endpoint = endpoint or config.ollama_endpoint
        self.model = model or config.ollama_model
        self.timeout = timeout or config.ollama_timeout_seconds
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.endpoint,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def is_available(self) -> bool:
        """Check if Ollama is available and the model is loaded."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                # Check if our model is available (with or without :latest tag)
                model_base = self.model.split(":")[0]
                return any(model_base in m for m in models)
            return False
        except Exception as e:
            logger.debug(f"Ollama availability check failed: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        tools: List[Dict[str, Any]] | None = None,
        stream: bool = False,
    ) -> OllamaResponse:
        """Generate a response from the model.

        Args:
            prompt: The user prompt
            system: Optional system message
            tools: Optional list of tool definitions for function calling
            stream: Whether to stream the response (not implemented yet)

        Returns:
            OllamaResponse with the generated content
        """
        client = await self._get_client()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,  # Non-streaming for simplicity
        }

        # Add tools if provided (for function calling)
        if tools:
            payload["tools"] = tools

        logger.debug(f"Ollama request: {json.dumps(payload, indent=2)[:500]}")

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
        )

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (for semantic clustering).

        Note: FunctionGemma may not have embedding endpoint.
        Falls back to using nomic-embed-text if available.
        """
        client = await self._get_client()

        payload = {
            "model": "nomic-embed-text",  # Common embedding model
            "prompt": text,
        }

        try:
            response = await client.post("/api/embeddings", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")
            # Return empty embedding on failure
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
            Dict with execution result
        """
        system_prompt = """You are a skill executor. Given a skill description and context,
determine what actions to take and return a structured response.

Respond in JSON format with:
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

        response = await self.generate(prompt, system=system_prompt)

        # Parse the response as JSON
        try:
            result = json.loads(response.content)
        except json.JSONDecodeError:
            result = {
                "actions": [],
                "reasoning": response.content,
                "success": False,
                "error": "Failed to parse response as JSON",
            }

        result["model"] = response.model
        result["tokens"] = response.eval_count

        return result

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
Tags: {', '.join(tags)}

Requirements:
- Use snake_case
- End with _skill
- Be descriptive but concise (3-5 words)
- Capture the primary action and context

Respond with ONLY the skill name, nothing else."""

        response = await self.generate(prompt)
        name = response.content.strip().lower()

        # Ensure it ends with _skill
        if not name.endswith("_skill"):
            name = f"{name}_skill"

        # Clean up any invalid characters
        name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)

        return name

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

        response = await self.generate(prompt)

        try:
            analysis = json.loads(response.content)
        except json.JSONDecodeError:
            analysis = {
                "category": "unknown",
                "description": response.content,
                "suggested_name": f"pattern_{hash(pattern_sequence) % 10000:04x}_skill",
                "is_meaningful": False,
            }

        return analysis


# Singleton instance
_client: OllamaClient | None = None


async def get_ollama_client() -> OllamaClient:
    """Get the global Ollama client instance."""
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client
