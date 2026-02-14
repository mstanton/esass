"""
Local LLM integration for ESASS pattern analysis and skill naming.

Provides async interface to local Ollama instance for:
- Semantic skill naming
- Pattern analysis and clustering
- Embedding generation for similarity
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


@dataclass
class LocalLLMConfig:
    """Configuration for local LLM integration."""
    enabled: bool = True
    ollama_endpoint: str = "http://localhost:11434"
    ollama_model: str = "functiongemma"
    timeout_seconds: int = 30


class LocalLLMClient:
    """
    Client for local LLM operations in ESASS.

    Uses Ollama API directly for pattern analysis and skill naming.
    """

    def __init__(self, config: LocalLLMConfig | None = None):
        self.config = config or LocalLLMConfig(
            enabled=os.environ.get("LOCAL_LLM_ENABLED", "true").lower() == "true",
            ollama_endpoint=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434"),
            ollama_model=os.environ.get("OLLAMA_MODEL", "functiongemma"),
            timeout_seconds=int(os.environ.get("OLLAMA_TIMEOUT", "30")),
        )
        self._client: httpx.AsyncClient | None = None
        self._available: bool | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.ollama_endpoint,
                timeout=httpx.Timeout(self.config.timeout_seconds),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def is_available(self) -> bool:
        """Check if local LLM is available."""
        if not self.config.enabled:
            return False

        if self._available is not None:
            return self._available

        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                model_base = self.config.ollama_model.split(":")[0]
                self._available = any(model_base in m for m in models)
            else:
                self._available = False
        except Exception as e:
            logger.debug(f"Local LLM availability check failed: {e}")
            self._available = False

        return self._available

    async def _generate(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 256,
    ) -> str:
        """Generate text using local LLM."""
        client = await self._get_client()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
            }
        }

        response = await client.post("/api/chat", json=payload)
        response.raise_for_status()

        data = response.json()
        return data.get("message", {}).get("content", "")

    async def generate_skill_name(
        self,
        pattern_description: str,
        tags: List[str],
        sequence: List[str] | None = None,
    ) -> str:
        """
        Generate a semantic skill name from pattern information.

        Args:
            pattern_description: Human-readable pattern description
            tags: Associated tags
            sequence: Optional tool sequence

        Returns:
            Semantic skill name in snake_case ending with _skill
        """
        if not await self.is_available():
            return self._fallback_name(tags)

        # Build prompt
        sequence_str = " -> ".join(sequence) if sequence else pattern_description

        prompt = f"""Generate a concise, semantic skill name for this pattern:

Pattern: {sequence_str}
Tags: {', '.join(tags[:5])}

Requirements:
- Use snake_case
- End with _skill
- Be descriptive but concise (2-4 words before _skill)
- Capture the primary action and context

Respond with ONLY the skill name, nothing else."""

        try:
            response = await self._generate(prompt, max_tokens=50)
            name = response.strip().lower()

            # Clean up response - remove quotes, extra text
            name = name.replace('"', '').replace("'", "")
            name = name.split()[0] if name else ""  # Take first word
            name = name.split("\n")[0]  # Take first line

            # Remove non-alphanumeric except underscore
            name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)

            # Remove leading/trailing underscores
            name = name.strip("_")

            # Collapse multiple underscores
            while "__" in name:
                name = name.replace("__", "_")

            if not name.endswith("_skill"):
                name = f"{name}_skill" if name else self._fallback_name(tags)

            # Validate name
            invalid_names = {"_skill", "skill", "pattern_skill", "workflow_skill", "the_skill"}
            if len(name) < 10 or name in invalid_names or name.startswith("_"):
                return self._fallback_name(tags)

            return name

        except Exception as e:
            logger.warning(f"Local LLM skill naming failed: {e}")
            return self._fallback_name(tags)

    async def analyze_pattern(
        self,
        pattern_description: str,
        sequence: List[str],
        support: int,
        confidence: float,
    ) -> Dict[str, Any]:
        """
        Analyze a pattern for semantic meaning.

        Args:
            pattern_description: Human-readable description
            sequence: Tool sequence
            support: Occurrence count
            confidence: Confidence score

        Returns:
            Analysis dict with category, description, suggested_name, is_meaningful
        """
        if not await self.is_available():
            return self._fallback_analysis(pattern_description, sequence)

        sequence_str = " -> ".join(sequence)

        prompt = f"""Analyze this tool usage pattern and return JSON:

Pattern: {sequence_str}
Description: {pattern_description}
Occurrences: {support}
Confidence: {confidence:.1%}

Return JSON with these fields:
{{
    "category": "one of: file_modification, code_search, git_workflow, testing, documentation, configuration, debugging",
    "description": "brief description of what this pattern accomplishes",
    "suggested_name": "semantic_skill_name",
    "is_meaningful": true if this represents a useful workflow, false if too generic
}}

Return ONLY the JSON, no other text."""

        try:
            response = await self._generate(prompt, max_tokens=200)

            # Extract JSON from response
            content = response.strip()
            start = content.find("{")
            end = content.rfind("}") + 1

            if start >= 0 and end > start:
                analysis = json.loads(content[start:end])
                analysis["source"] = "local_llm"
                return analysis

        except Exception as e:
            logger.warning(f"Local LLM pattern analysis failed: {e}")

        return self._fallback_analysis(pattern_description, sequence)

    async def cluster_patterns_semantically(
        self,
        patterns: List[Tuple[str, List[str], List[str]]],  # (description, sequence, tags)
    ) -> List[List[int]]:
        """
        Cluster similar patterns together using semantic analysis.

        Args:
            patterns: List of (description, sequence, tags) tuples

        Returns:
            List of clusters, where each cluster is a list of pattern indices
        """
        if not await self.is_available() or len(patterns) < 2:
            # Return each pattern in its own cluster
            return [[i] for i in range(len(patterns))]

        # For now, use simple tag-based clustering with LLM assistance
        # Build pattern summaries
        summaries = []
        for desc, seq, tags in patterns:
            seq_str = " -> ".join(seq[:4])
            tag_str = ", ".join(tags[:3])
            summaries.append(f"[{seq_str}] Tags: {tag_str}")

        prompt = f"""Group these {len(patterns)} patterns into clusters based on semantic similarity.
Patterns that accomplish similar goals should be in the same cluster.

Patterns:
"""
        for i, summary in enumerate(summaries):
            prompt += f"{i}: {summary}\n"

        prompt += """
Return JSON array of clusters, where each cluster is an array of pattern indices.
Example: [[0, 2], [1, 3, 4], [5]]

Return ONLY the JSON array, no other text."""

        try:
            response = await self._generate(prompt, max_tokens=100)

            content = response.strip()
            start = content.find("[")
            end = content.rfind("]") + 1

            if start >= 0 and end > start:
                clusters = json.loads(content[start:end])

                # Validate clusters
                seen = set()
                valid_clusters = []
                for cluster in clusters:
                    if isinstance(cluster, list):
                        valid_indices = [
                            i for i in cluster
                            if isinstance(i, int) and 0 <= i < len(patterns) and i not in seen
                        ]
                        if valid_indices:
                            valid_clusters.append(valid_indices)
                            seen.update(valid_indices)

                # Add unclustered patterns
                for i in range(len(patterns)):
                    if i not in seen:
                        valid_clusters.append([i])

                return valid_clusters

        except Exception as e:
            logger.warning(f"Local LLM clustering failed: {e}")

        # Fallback: each pattern in its own cluster
        return [[i] for i in range(len(patterns))]

    def _fallback_name(self, tags: List[str]) -> str:
        """Generate fallback name from tags."""
        if len(tags) >= 2:
            return f"{tags[0]}_{tags[1]}_skill"
        elif len(tags) == 1:
            return f"{tags[0]}_workflow_skill"
        else:
            return "pattern_workflow_skill"

    def _fallback_analysis(
        self,
        description: str,
        sequence: List[str],
    ) -> Dict[str, Any]:
        """Generate fallback analysis."""
        # Infer category from sequence
        seq_str = " ".join(sequence).lower()

        if "git" in seq_str:
            category = "git_workflow"
        elif "test" in seq_str or "pytest" in seq_str:
            category = "testing"
        elif "edit" in seq_str and "read" in seq_str:
            category = "file_modification"
        elif "grep" in seq_str or "glob" in seq_str:
            category = "code_search"
        else:
            category = "general"

        return {
            "category": category,
            "description": description,
            "suggested_name": None,
            "is_meaningful": len(set(sequence)) > 1,
            "source": "fallback",
        }


# Singleton instance
_client: LocalLLMClient | None = None


async def get_local_llm_client() -> LocalLLMClient:
    """Get the global LocalLLMClient instance."""
    global _client
    if _client is None:
        _client = LocalLLMClient()
    return _client


async def is_local_llm_available() -> bool:
    """Check if local LLM is available."""
    client = await get_local_llm_client()
    return await client.is_available()


# Synchronous wrapper for non-async code
def generate_skill_name_sync(
    pattern_description: str,
    tags: List[str],
    sequence: List[str] | None = None,
) -> str:
    """Synchronous wrapper for skill name generation."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    async def _generate():
        client = await get_local_llm_client()
        return await client.generate_skill_name(pattern_description, tags, sequence)

    try:
        return loop.run_until_complete(_generate())
    except Exception as e:
        logger.warning(f"Sync skill name generation failed: {e}")
        # Fallback
        if len(tags) >= 2:
            return f"{tags[0]}_{tags[1]}_skill"
        elif len(tags) == 1:
            return f"{tags[0]}_workflow_skill"
        return "pattern_workflow_skill"
