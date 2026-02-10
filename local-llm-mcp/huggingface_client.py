"""HuggingFace Inference API client for Tier 2 fallback."""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from config import get_config

logger = logging.getLogger(__name__)


@dataclass
class HuggingFaceResponse:
    """Response from HuggingFace Inference API."""
    content: str
    model: str
    usage: Dict[str, int] | None = None


class HuggingFaceClient:
    """Client for HuggingFace Inference API (Tier 2 fallback)."""

    INFERENCE_API_URL = "https://api-inference.huggingface.co/models"

    def __init__(
        self,
        model: str | None = None,
        token: str | None = None,
        timeout: int | None = None,
    ):
        config = get_config()
        self.model = model or config.hf_model
        self.token = token or config.hf_token
        self.timeout = timeout or config.hf_timeout_seconds
        self._client: httpx.AsyncClient | None = None

        if not self.token:
            logger.warning("HF_TOKEN not set - HuggingFace client may not work")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(self.timeout),
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
            # Simple health check
            response = await client.get(
                f"{self.INFERENCE_API_URL}/{self.model}",
                params={"wait_for_model": "false"},
            )
            return response.status_code in (200, 503)  # 503 = model loading
        except Exception as e:
            logger.debug(f"HuggingFace availability check failed: {e}")
            return False

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
        """
        client = await self._get_client()

        # Format prompt with system message if provided
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
        }

        logger.debug(f"HuggingFace request to {self.model}")

        response = await client.post(
            f"{self.INFERENCE_API_URL}/{self.model}",
            json=payload,
        )
        response.raise_for_status()

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

        response = await self.generate(prompt, system=system_prompt)

        try:
            # Try to extract JSON from response
            content = response.content
            # Find JSON in response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(content[start:end])
            else:
                raise json.JSONDecodeError("No JSON found", content, 0)
        except json.JSONDecodeError:
            result = {
                "actions": [],
                "reasoning": response.content,
                "success": False,
                "error": "Failed to parse response as JSON",
            }

        result["model"] = response.model
        result["tier"] = "huggingface"

        return result

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
Tags: {', '.join(tags)}

Requirements: snake_case, ends with _skill, 3-5 words.
Reply with ONLY the skill name."""

        response = await self.generate(prompt, max_new_tokens=50, temperature=0.3)
        name = response.content.strip().lower().split()[0]  # Take first word/name

        if not name.endswith("_skill"):
            name = f"{name}_skill"

        name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)

        return name

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

        response = await self.generate(prompt, max_new_tokens=200, temperature=0.3)

        try:
            content = response.content
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                analysis = json.loads(content[start:end])
            else:
                raise json.JSONDecodeError("No JSON found", content, 0)
        except json.JSONDecodeError:
            analysis = {
                "category": "unknown",
                "description": response.content[:200],
                "suggested_name": f"pattern_{hash(pattern_sequence) % 10000:04x}_skill",
                "is_meaningful": False,
            }

        analysis["tier"] = "huggingface"
        return analysis


# Singleton instance
_client: HuggingFaceClient | None = None


async def get_huggingface_client() -> HuggingFaceClient:
    """Get the global HuggingFace client instance."""
    global _client
    if _client is None:
        _client = HuggingFaceClient()
    return _client
