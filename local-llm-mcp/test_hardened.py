#!/usr/bin/env python3
"""Tests for hardened local-llm-mcp components.

Tests:
- JSON extraction
- Circuit breaker
- Rate limiter
- Response cache
- Input validation
- Retry logic
"""

import asyncio
import json
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from utils import (
    extract_json,
    clean_skill_name,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    ResponseCache,
    RetryConfig,
    RetryStrategy,
    retry_async,
    RateLimiter,
    validate_skill_request,
)


# ============================================================================
# JSON Extraction Tests
# ============================================================================

class TestExtractJson:
    """Tests for extract_json function."""

    def test_raw_json(self):
        """Test parsing raw JSON."""
        content = '{"key": "value", "count": 42}'
        result = extract_json(content)
        assert result == {"key": "value", "count": 42}

    def test_json_code_block(self):
        """Test extracting JSON from markdown code block."""
        content = '''Here's the result:

```json
{
    "actions": ["read", "write"],
    "success": true
}
```

That's all!'''
        result = extract_json(content)
        assert result == {"actions": ["read", "write"], "success": True}

    def test_plain_code_block(self):
        """Test extracting JSON from plain code block."""
        content = '''```
{"name": "test_skill", "valid": true}
```'''
        result = extract_json(content)
        assert result == {"name": "test_skill", "valid": True}

    def test_json_embedded_in_text(self):
        """Test extracting JSON embedded in text."""
        content = 'The result is {"status": "ok"} and more text.'
        result = extract_json(content)
        assert result == {"status": "ok"}

    def test_nested_json(self):
        """Test extracting nested JSON."""
        content = '''Analysis:
{"outer": {"inner": {"value": 123}}}'''
        result = extract_json(content)
        assert result == {"outer": {"inner": {"value": 123}}}

    def test_invalid_json(self):
        """Test handling invalid JSON."""
        content = "This is not JSON at all"
        result = extract_json(content)
        assert "error" in result
        assert "raw" in result

    def test_truncated_json(self):
        """Test handling truncated JSON."""
        content = '{"incomplete": true, "missing'
        result = extract_json(content)
        assert "error" in result


class TestCleanSkillName:
    """Tests for clean_skill_name function."""

    def test_basic_cleaning(self):
        """Test basic name cleaning."""
        assert clean_skill_name("test_skill") == "test_skill"
        assert clean_skill_name("Test_Skill") == "test_skill"

    def test_adds_skill_suffix(self):
        """Test adding _skill suffix."""
        assert clean_skill_name("search_file").endswith("_skill")
        assert clean_skill_name("search_file_skill") == "search_file_skill"

    def test_removes_special_chars(self):
        """Test removing special characters."""
        result = clean_skill_name("test**skill`")
        assert "skill" in result
        assert result.endswith("_skill")
        assert "*" not in result
        assert "`" not in result

    def test_multiline_takes_first(self):
        """Test taking first line only."""
        name = clean_skill_name("first_skill\nsecond_skill")
        assert "second" not in name

    def test_empty_returns_unknown(self):
        """Test empty input returns unknown_skill."""
        assert clean_skill_name("") == "unknown_skill"
        assert clean_skill_name("   ") == "unknown_skill"

    def test_length_limit(self):
        """Test length limiting."""
        long_name = "a" * 100 + "_skill"
        result = clean_skill_name(long_name)
        # Should be reasonably bounded (under 60 chars)
        assert len(result) <= 60
        assert result.endswith("_skill")


# ============================================================================
# Circuit Breaker Tests
# ============================================================================

class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_initial_state_closed(self):
        """Test initial state is CLOSED."""
        breaker = CircuitBreaker("test")
        assert breaker.state == CircuitState.CLOSED
        assert breaker.can_execute()

    def test_opens_after_failures(self):
        """Test circuit opens after threshold failures."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test", config)

        for _ in range(3):
            breaker.record_failure()

        assert breaker.state == CircuitState.OPEN
        assert not breaker.can_execute()

    def test_half_open_after_timeout(self):
        """Test circuit goes half-open after timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            timeout_seconds=0.1,
        )
        breaker = CircuitBreaker("test", config)

        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        time.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN
        assert breaker.can_execute()

    def test_closes_after_successes(self):
        """Test circuit closes after successes in half-open."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=2,
            timeout_seconds=0.01,
        )
        breaker = CircuitBreaker("test", config)

        breaker.record_failure()
        time.sleep(0.02)

        assert breaker.state == CircuitState.HALF_OPEN
        breaker.record_success()
        breaker.record_success()

        assert breaker.state == CircuitState.CLOSED

    def test_reopens_on_half_open_failure(self):
        """Test circuit reopens on failure in half-open state."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            timeout_seconds=0.01,
        )
        breaker = CircuitBreaker("test", config)

        breaker.record_failure()
        time.sleep(0.02)

        assert breaker.state == CircuitState.HALF_OPEN
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

    def test_reset(self):
        """Test circuit reset."""
        breaker = CircuitBreaker("test")
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()

        breaker.reset()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.can_execute()

    def test_get_status(self):
        """Test status reporting."""
        breaker = CircuitBreaker("test")
        status = breaker.get_status()

        assert status["name"] == "test"
        assert status["state"] == "closed"
        assert "failure_count" in status


# ============================================================================
# Response Cache Tests
# ============================================================================

class TestResponseCache:
    """Tests for ResponseCache class."""

    def test_set_and_get(self):
        """Test basic set and get."""
        cache = ResponseCache()
        cache.set("key1", {"data": 123})
        assert cache.get("key1") == {"data": 123}

    def test_miss_returns_none(self):
        """Test cache miss returns None."""
        cache = ResponseCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self):
        """Test TTL expiration."""
        cache = ResponseCache(default_ttl_seconds=0.1)
        cache.set("key1", "value1")

        assert cache.get("key1") == "value1"
        time.sleep(0.15)
        assert cache.get("key1") is None

    def test_max_size_eviction(self):
        """Test LRU eviction at max size."""
        cache = ResponseCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # Should evict key1

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_make_key_deterministic(self):
        """Test key generation is deterministic."""
        cache = ResponseCache()
        key1 = cache.make_key("arg1", kwarg="value")
        key2 = cache.make_key("arg1", kwarg="value")
        key3 = cache.make_key("arg2", kwarg="value")

        assert key1 == key2
        assert key1 != key3

    def test_invalidate(self):
        """Test cache invalidation."""
        cache = ResponseCache()
        cache.set("key1", "value1")
        assert cache.invalidate("key1")
        assert cache.get("key1") is None
        assert not cache.invalidate("key1")  # Already gone

    def test_clear(self):
        """Test cache clearing."""
        cache = ResponseCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        count = cache.clear()
        assert count == 2
        assert cache.get("key1") is None

    def test_stats(self):
        """Test cache statistics."""
        cache = ResponseCache(max_size=10)
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("key1")

        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["max_size"] == 10
        assert stats["total_hits"] >= 2


# ============================================================================
# Rate Limiter Tests
# ============================================================================

class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_initial_capacity(self):
        """Test initial capacity available."""
        limiter = RateLimiter(rate=1, capacity=5)
        for _ in range(5):
            assert limiter.acquire()

    def test_blocks_when_empty(self):
        """Test blocks when tokens depleted."""
        limiter = RateLimiter(rate=1, capacity=2)
        assert limiter.acquire()
        assert limiter.acquire()
        assert not limiter.acquire()

    def test_refills_over_time(self):
        """Test tokens refill over time."""
        limiter = RateLimiter(rate=10, capacity=2)  # 10 per second
        limiter.acquire()
        limiter.acquire()
        assert not limiter.acquire()

        time.sleep(0.15)  # Should refill ~1.5 tokens
        assert limiter.acquire()

    def test_status(self):
        """Test status reporting."""
        limiter = RateLimiter(rate=5, capacity=10)
        status = limiter.get_status()

        assert status["capacity"] == 10
        assert status["rate_per_second"] == 5
        assert status["available_tokens"] <= 10

    @pytest.mark.asyncio
    async def test_async_acquire_success(self):
        """Test async acquire succeeds when available."""
        limiter = RateLimiter(rate=10, capacity=5)
        assert await limiter.acquire_async(1, timeout=1.0)

    @pytest.mark.asyncio
    async def test_async_acquire_timeout(self):
        """Test async acquire times out when empty."""
        limiter = RateLimiter(rate=0.1, capacity=1)  # Very slow refill
        limiter.acquire()

        result = await limiter.acquire_async(1, timeout=0.1)
        assert not result


# ============================================================================
# Input Validation Tests
# ============================================================================

class TestValidateSkillRequest:
    """Tests for validate_skill_request function."""

    def test_valid_request(self):
        """Test valid request passes."""
        result = validate_skill_request(
            skill_name="test_skill",
            skill_description="A test skill",
            capabilities=["file_operations"],
            context={"file": "test.py"},
        )
        assert result.valid
        assert not result.errors
        assert result.sanitized is not None

    def test_empty_skill_name(self):
        """Test empty skill name fails."""
        result = validate_skill_request(
            skill_name="",
            skill_description="A test skill",
        )
        assert not result.valid
        assert any("skill_name" in e for e in result.errors)

    def test_long_skill_name(self):
        """Test long skill name fails."""
        result = validate_skill_request(
            skill_name="a" * 250,
            skill_description="A test skill",
        )
        assert not result.valid

    def test_empty_description(self):
        """Test empty description fails."""
        result = validate_skill_request(
            skill_name="test_skill",
            skill_description="",
        )
        assert not result.valid

    def test_invalid_capabilities_type(self):
        """Test invalid capabilities type fails."""
        result = validate_skill_request(
            skill_name="test_skill",
            skill_description="A test skill",
            capabilities="not_a_list",
        )
        assert not result.valid

    def test_too_many_capabilities(self):
        """Test too many capabilities fails."""
        result = validate_skill_request(
            skill_name="test_skill",
            skill_description="A test skill",
            capabilities=["cap"] * 25,
        )
        assert not result.valid

    def test_large_context(self):
        """Test very large context fails."""
        result = validate_skill_request(
            skill_name="test_skill",
            skill_description="A test skill",
            context={"data": "x" * 100000},
        )
        assert not result.valid

    def test_non_serializable_context(self):
        """Test non-serializable context fails."""
        result = validate_skill_request(
            skill_name="test_skill",
            skill_description="A test skill",
            context={"func": lambda x: x},
        )
        assert not result.valid

    def test_sanitizes_whitespace(self):
        """Test whitespace is trimmed."""
        result = validate_skill_request(
            skill_name="  test_skill  ",
            skill_description="  A test skill  ",
        )
        assert result.valid
        assert result.sanitized["skill_name"] == "test_skill"
        assert result.sanitized["skill_description"] == "A test skill"


# ============================================================================
# Retry Logic Tests
# ============================================================================

class TestRetryAsync:
    """Tests for retry_async function."""

    @pytest.mark.asyncio
    async def test_success_first_try(self):
        """Test success on first try."""
        async def success():
            return "ok"

        result = await retry_async(success)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_success_after_failures(self):
        """Test success after initial failures."""
        attempts = [0]

        async def fails_twice():
            attempts[0] += 1
            if attempts[0] < 3:
                raise ValueError("temporary error")
            return "ok"

        config = RetryConfig(
            max_attempts=3,
            base_delay_seconds=0.01,
        )
        result = await retry_async(fails_twice, config)
        assert result == "ok"
        assert attempts[0] == 3

    @pytest.mark.asyncio
    async def test_fails_after_max_attempts(self):
        """Test fails after exhausting retries."""
        async def always_fails():
            raise ValueError("persistent error")

        config = RetryConfig(
            max_attempts=3,
            base_delay_seconds=0.01,
        )

        with pytest.raises(ValueError, match="persistent error"):
            await retry_async(always_fails, config)

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        """Test non-retryable exceptions fail immediately."""
        attempts = [0]

        async def raises_type_error():
            attempts[0] += 1
            raise TypeError("not retryable")

        config = RetryConfig(
            max_attempts=3,
            retryable_exceptions=(ValueError,),  # Only ValueError
        )

        with pytest.raises(TypeError):
            await retry_async(raises_type_error, config)

        assert attempts[0] == 1  # No retries


# ============================================================================
# Integration Tests
# ============================================================================

class TestOllamaClientIntegration:
    """Integration tests for hardened Ollama client."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_triggers(self):
        """Test circuit breaker triggers after failures."""
        from ollama_client import OllamaClient, reset_ollama_client

        reset_ollama_client()
        client = OllamaClient()

        # Force circuit breaker to open
        for _ in range(5):
            client._circuit.record_failure()

        with pytest.raises(RuntimeError, match="Circuit breaker open"):
            await client.generate("test")

    @pytest.mark.asyncio
    async def test_cache_works(self):
        """Test response caching."""
        from ollama_client import OllamaClient

        client = OllamaClient(enable_cache=True, cache_ttl=60)

        # Manually populate cache
        cache_key = client._cache.make_key(
            "generate", prompt="test", system=None, model=client.model
        )
        from ollama_client import OllamaResponse
        cached = OllamaResponse(content="cached", model="test", done=True)
        client._cache.set(cache_key, cached)

        # Should hit cache without making request
        with patch.object(client, '_get_client') as mock_client:
            result = await client.generate("test", use_cache=True)
            mock_client.assert_not_called()
            assert result.content == "cached"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
