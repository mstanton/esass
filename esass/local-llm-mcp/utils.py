"""Shared utilities for local-llm-mcp.

Provides:
- JSON extraction from LLM responses (markdown, raw, etc.)
- Retry logic with exponential backoff
- Circuit breaker pattern
- Response caching
"""

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# JSON Extraction
# ============================================================================

def extract_json(content: str) -> Dict[str, Any]:
    """Extract JSON from LLM response, handling various formats.

    Handles:
    - ```json ... ``` code blocks
    - ``` ... ``` code blocks
    - Raw JSON objects
    - JSON embedded in text

    Args:
        content: Raw LLM response text

    Returns:
        Parsed JSON dict, or {"error": ..., "raw": ...} on failure
    """
    content = content.strip()

    # Strategy 1: Extract from ```json blocks
    json_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
    if json_block_match:
        try:
            return json.loads(json_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 2: Extract from ``` blocks
    code_block_match = re.search(r'```\s*([\s\S]*?)\s*```', content)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 3: Direct JSON parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Strategy 4: Find JSON object in text
    # Find the first { and last matching }
    brace_count = 0
    json_start = -1
    json_end = -1

    for i, char in enumerate(content):
        if char == '{':
            if json_start == -1:
                json_start = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and json_start != -1:
                json_end = i + 1
                break

    if json_start >= 0 and json_end > json_start:
        try:
            return json.loads(content[json_start:json_end])
        except json.JSONDecodeError:
            pass

    # All strategies failed
    return {"error": "Failed to extract JSON", "raw": content[:500]}


def clean_skill_name(name: str) -> str:
    """Clean and validate a skill name.

    Args:
        name: Raw skill name from LLM

    Returns:
        Cleaned snake_case skill name ending with _skill
    """
    # Remove any markdown or quotes
    name = re.sub(r'[`\'\"*]', '', name)

    # Take first line and first token
    name = name.strip().split('\n')[0].split()[0] if name.strip() else "unknown"

    # Convert to snake_case
    name = name.lower()
    name = re.sub(r'[^a-z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name)  # Collapse multiple underscores
    name = name.strip('_')

    # Ensure reasonable length first (before adding suffix)
    max_base_len = 44  # Reserve space for "_skill"
    if len(name) > max_base_len:
        name = name[:max_base_len]

    # Ensure it ends with _skill
    if not name.endswith('_skill'):
        name = f"{name}_skill"

    return name or "unknown_skill"


# ============================================================================
# Retry Logic
# ============================================================================

class RetryStrategy(Enum):
    """Retry strategy types."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    IMMEDIATE = "immediate"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)


async def retry_async(
    func: Callable[..., Awaitable[T]],
    config: Optional[RetryConfig] = None,
    **kwargs,
) -> T:
    """Execute async function with retry logic.

    Args:
        func: Async function to execute
        config: Retry configuration
        **kwargs: Arguments to pass to func

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    config = config or RetryConfig()
    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            return await func(**kwargs)
        except config.retryable_exceptions as e:
            last_exception = e

            if attempt == config.max_attempts - 1:
                break

            # Calculate delay
            if config.strategy == RetryStrategy.EXPONENTIAL:
                delay = min(
                    config.base_delay_seconds * (2 ** attempt),
                    config.max_delay_seconds
                )
            elif config.strategy == RetryStrategy.LINEAR:
                delay = min(
                    config.base_delay_seconds * (attempt + 1),
                    config.max_delay_seconds
                )
            else:
                delay = config.base_delay_seconds

            # Add jitter
            if config.jitter:
                import random
                delay = delay * (0.5 + random.random())

            logger.warning(
                f"Retry {attempt + 1}/{config.max_attempts} after {delay:.2f}s: {e}"
            )
            await asyncio.sleep(delay)

    raise last_exception


# ============================================================================
# Circuit Breaker
# ============================================================================

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5      # Failures before opening
    success_threshold: int = 2      # Successes to close from half-open
    timeout_seconds: float = 60.0   # Time before half-open
    half_open_max_calls: int = 3    # Max concurrent calls in half-open


class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures.

    Usage:
        breaker = CircuitBreaker("ollama")

        if breaker.can_execute():
            try:
                result = await some_operation()
                breaker.record_success()
            except Exception as e:
                breaker.record_failure()
                raise
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current state, checking for timeout transition."""
        if self._state == CircuitState.OPEN and self._last_failure_time:
            if time.time() - self._last_failure_time >= self.config.timeout_seconds:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info(f"Circuit {self.name}: OPEN -> HALF_OPEN")
        return self._state

    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        state = self.state

        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.config.half_open_max_calls
        else:  # OPEN
            return False

    def record_success(self) -> None:
        """Record successful execution."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                logger.info(f"Circuit {self.name}: HALF_OPEN -> CLOSED")
        else:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record failed execution."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._success_count = 0
            logger.warning(f"Circuit {self.name}: HALF_OPEN -> OPEN")
        elif self._failure_count >= self.config.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit {self.name}: CLOSED -> OPEN ({self._failure_count} failures)")

    def reset(self) -> None:
        """Reset circuit to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0

    def get_status(self) -> Dict[str, Any]:
        """Get circuit status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure": self._last_failure_time,
        }


# ============================================================================
# Response Cache
# ============================================================================

@dataclass
class CacheEntry:
    """Cache entry with TTL."""
    value: Any
    created_at: float
    ttl_seconds: float
    hits: int = 0

    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl_seconds


class ResponseCache:
    """Simple in-memory cache with TTL and size limits.

    Usage:
        cache = ResponseCache(max_size=100, default_ttl=300)

        key = cache.make_key(prompt, context)
        if cached := cache.get(key):
            return cached

        result = await expensive_operation()
        cache.set(key, result)
        return result
    """

    def __init__(
        self,
        max_size: int = 100,
        default_ttl_seconds: float = 300.0,  # 5 minutes
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl_seconds
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # For LRU eviction

    def make_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if entry.is_expired:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            return None

        entry.hits += 1
        # Update access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[float] = None,
    ) -> None:
        """Set value in cache."""
        # Evict if at capacity
        while len(self._cache) >= self.max_size and self._access_order:
            oldest_key = self._access_order.pop(0)
            self._cache.pop(oldest_key, None)

        self._cache[key] = CacheEntry(
            value=value,
            created_at=time.time(),
            ttl_seconds=ttl_seconds or self.default_ttl,
        )
        self._access_order.append(key)

    def invalidate(self, key: str) -> bool:
        """Invalidate a cache entry."""
        if key in self._cache:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            return True
        return False

    def clear(self) -> int:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self._access_order.clear()
        return count

    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        expired = [k for k, v in self._cache.items() if v.is_expired]
        for key in expired:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
        return len(expired)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_hits = sum(e.hits for e in self._cache.values())
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "total_hits": total_hits,
            "expired_count": sum(1 for e in self._cache.values() if e.is_expired),
        }


# ============================================================================
# Input Validation
# ============================================================================

@dataclass
class ValidationResult:
    """Result of input validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    sanitized: Optional[Dict[str, Any]] = None


def validate_skill_request(
    skill_name: str,
    skill_description: str,
    capabilities: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> ValidationResult:
    """Validate skill execution request.

    Args:
        skill_name: Name of skill
        skill_description: Description
        capabilities: Optional capability list
        context: Optional context dict

    Returns:
        ValidationResult with errors if invalid
    """
    errors = []

    # Validate skill_name
    if not skill_name or not isinstance(skill_name, str):
        errors.append("skill_name must be a non-empty string")
    elif len(skill_name) > 200:
        errors.append("skill_name exceeds 200 character limit")

    # Validate skill_description
    if not skill_description or not isinstance(skill_description, str):
        errors.append("skill_description must be a non-empty string")
    elif len(skill_description) > 10000:
        errors.append("skill_description exceeds 10000 character limit")

    # Validate capabilities
    if capabilities is not None:
        if not isinstance(capabilities, list):
            errors.append("capabilities must be a list")
        elif len(capabilities) > 20:
            errors.append("capabilities exceeds 20 item limit")
        else:
            for i, cap in enumerate(capabilities):
                if not isinstance(cap, str) or len(cap) > 100:
                    errors.append(f"capability[{i}] must be a string under 100 chars")

    # Validate context
    if context is not None:
        if not isinstance(context, dict):
            errors.append("context must be a dict")
        else:
            try:
                context_str = json.dumps(context)
                if len(context_str) > 50000:
                    errors.append("context exceeds 50KB when serialized")
            except (TypeError, ValueError):
                errors.append("context must be JSON-serializable")

    if errors:
        return ValidationResult(valid=False, errors=errors)

    return ValidationResult(
        valid=True,
        sanitized={
            "skill_name": skill_name.strip(),
            "skill_description": skill_description.strip(),
            "capabilities": capabilities or [],
            "context": context or {},
        }
    )


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """Token bucket rate limiter.

    Usage:
        limiter = RateLimiter(rate=10, capacity=20)  # 10/sec, burst of 20

        if limiter.acquire():
            await do_something()
        else:
            raise RateLimitExceeded()
    """

    def __init__(self, rate: float, capacity: float):
        """Initialize rate limiter.

        Args:
            rate: Tokens per second to add
            capacity: Maximum tokens (burst capacity)
        """
        self.rate = rate
        self.capacity = capacity
        self._tokens = capacity
        self._last_update = time.time()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_update = now

    def acquire(self, tokens: float = 1.0) -> bool:
        """Try to acquire tokens.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if acquired, False if rate limited
        """
        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False

    async def acquire_async(self, tokens: float = 1.0, timeout: float = 10.0) -> bool:
        """Async acquire with wait.

        Args:
            tokens: Number of tokens to acquire
            timeout: Max seconds to wait

        Returns:
            True if acquired within timeout
        """
        start = time.time()
        while time.time() - start < timeout:
            if self.acquire(tokens):
                return True
            await asyncio.sleep(0.1)
        return False

    def get_status(self) -> Dict[str, Any]:
        """Get rate limiter status."""
        self._refill()
        return {
            "available_tokens": round(self._tokens, 2),
            "capacity": self.capacity,
            "rate_per_second": self.rate,
        }
