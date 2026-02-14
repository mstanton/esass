#!/usr/bin/env python3
"""Tests for MCP dashboard integration.

Tests:
- MCPEventLogger writes correct JSONL
- MCPStatusWriter writes correct JSON
- MCPState reads status and events correctly
- Graceful degradation when MCP not running
- MCP rendering functions
"""

import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest


# ============================================================================
# Event Logger Tests
# ============================================================================


class TestMCPEventLogger:
    """Tests for the MCP event logger."""

    def test_log_execution(self, tmp_path):
        """Test logging a skill execution event."""
        from esass.mcp.event_logger import MCPEventLogger

        logger = MCPEventLogger(data_dir=tmp_path)
        logger.log_execution(
            skill_name="test_skill",
            tier_requested="local",
            tier_used="local",
            fallback_used=False,
            success=True,
            tokens_used=100,
            latency_ms=45.2,
            cost_actual=0.00001,
            cost_if_claude=0.0015,
            savings=0.00149,
            routing_reason="capability",
        )

        # Find the event file
        today = datetime.now().strftime("%Y%m%d")
        event_file = tmp_path / "logs" / f"mcp_events_{today}.jsonl"
        assert event_file.exists()

        with open(event_file) as f:
            event = json.loads(f.readline())

        assert event["event_type"] == "mcp_execution"
        assert event["event_data"]["skill_name"] == "test_skill"
        assert event["event_data"]["tier_used"] == "local"
        assert event["event_data"]["success"] is True
        assert event["event_data"]["tokens_used"] == 100
        assert event["event_data"]["savings"] == 0.00149
        assert "event_id" in event
        assert "timestamp" in event

    def test_log_circuit_breaker_change(self, tmp_path):
        """Test logging circuit breaker state change."""
        from esass.mcp.event_logger import MCPEventLogger

        logger = MCPEventLogger(data_dir=tmp_path)
        logger.log_circuit_breaker_change(
            name="ollama",
            old_state="closed",
            new_state="open",
            reason="3 consecutive failures",
        )

        today = datetime.now().strftime("%Y%m%d")
        event_file = tmp_path / "logs" / f"mcp_events_{today}.jsonl"

        with open(event_file) as f:
            event = json.loads(f.readline())

        assert event["event_type"] == "mcp_circuit_breaker"
        assert event["event_data"]["name"] == "ollama"
        assert event["event_data"]["new_state"] == "open"

    def test_log_tier_override(self, tmp_path):
        """Test logging tier override event."""
        from esass.mcp.event_logger import MCPEventLogger

        logger = MCPEventLogger(data_dir=tmp_path)
        logger.log_tier_override(
            skill_name="pattern_search_skill",
            old_tier="local",
            new_tier="huggingface",
            reason="Local failure rate 60% > 50%",
        )

        today = datetime.now().strftime("%Y%m%d")
        event_file = tmp_path / "logs" / f"mcp_events_{today}.jsonl"

        with open(event_file) as f:
            event = json.loads(f.readline())

        assert event["event_type"] == "mcp_tier_override"
        assert event["event_data"]["new_tier"] == "huggingface"

    def test_multiple_events_append(self, tmp_path):
        """Test multiple events append to same file."""
        from esass.mcp.event_logger import MCPEventLogger

        logger = MCPEventLogger(data_dir=tmp_path)
        for i in range(5):
            logger.log_execution(
                skill_name=f"skill_{i}",
                tier_requested="local",
                tier_used="local",
                fallback_used=False,
                success=True,
                tokens_used=100,
                latency_ms=10.0,
                cost_actual=0.00001,
                cost_if_claude=0.0015,
                savings=0.00149,
                routing_reason="capability",
            )

        today = datetime.now().strftime("%Y%m%d")
        event_file = tmp_path / "logs" / f"mcp_events_{today}.jsonl"

        with open(event_file) as f:
            lines = f.readlines()
        assert len(lines) == 5

    def test_creates_log_directory(self, tmp_path):
        """Test logger creates log directory if missing."""
        from esass.mcp.event_logger import MCPEventLogger

        data_dir = tmp_path / "deep" / "nested" / "dir"
        logger = MCPEventLogger(data_dir=data_dir)
        assert (data_dir / "logs").exists()

    def test_singleton(self):
        """Test singleton pattern."""
        from esass.mcp.event_logger import get_event_logger, reset_event_logger

        reset_event_logger()
        logger1 = get_event_logger()
        logger2 = get_event_logger()
        assert logger1 is logger2
        reset_event_logger()


# ============================================================================
# Status Writer Tests
# ============================================================================


class TestMCPStatusWriter:
    """Tests for the MCP status writer."""

    def test_write_status(self, tmp_path):
        """Test writing status snapshot."""
        from esass.mcp.status_writer import MCPStatusWriter

        writer = MCPStatusWriter(data_dir=tmp_path)
        writer.write_status(
            availability={"local": True, "huggingface": True, "claude": True},
            circuit_breakers={
                "ollama": {"state": "closed", "failure_count": 0},
                "huggingface": {"state": "closed", "failure_count": 0},
            },
            cache_stats={"ollama": {"size": 5, "max_size": 50, "total_hits": 10, "total_misses": 40}},
            rate_limit={"available_tokens": 8, "capacity": 10, "rate_per_second": 0.5},
            session_summary={
                "total_executions": 47,
                "total_cost": 0.0023,
                "total_savings": 0.6854,
                "savings_percentage": 99.7,
            },
            tier_breakdown={"local": 38, "huggingface": 8, "claude": 1},
            adaptive_overrides=[],
        )

        status_file = tmp_path / "mcp" / "status.json"
        assert status_file.exists()

        with open(status_file) as f:
            data = json.load(f)

        assert data["availability"]["local"] is True
        assert data["circuit_breakers"]["ollama"]["state"] == "closed"
        assert data["costs"]["session_executions"] == 47
        assert data["costs"]["session_savings"] == 0.6854
        assert data["tier_breakdown"]["local"] == 38
        assert "updated_at" in data

    def test_atomic_overwrite(self, tmp_path):
        """Test status file is overwritten atomically."""
        from esass.mcp.status_writer import MCPStatusWriter

        writer = MCPStatusWriter(data_dir=tmp_path)

        # Write first version
        writer.write_status(
            availability={"local": True},
            circuit_breakers={},
            cache_stats={},
            rate_limit={},
            session_summary={"total_executions": 1, "total_cost": 0, "total_savings": 0, "savings_percentage": 0},
            tier_breakdown={},
            adaptive_overrides=[],
        )

        # Write second version (overwrites)
        writer.write_status(
            availability={"local": False},
            circuit_breakers={},
            cache_stats={},
            rate_limit={},
            session_summary={"total_executions": 2, "total_cost": 0, "total_savings": 0, "savings_percentage": 0},
            tier_breakdown={},
            adaptive_overrides=[],
        )

        with open(tmp_path / "mcp" / "status.json") as f:
            data = json.load(f)

        assert data["availability"]["local"] is False
        assert data["costs"]["session_executions"] == 2

    def test_remove_status(self, tmp_path):
        """Test removing status file."""
        from esass.mcp.status_writer import MCPStatusWriter

        writer = MCPStatusWriter(data_dir=tmp_path)
        writer.write_status(
            availability={}, circuit_breakers={}, cache_stats={},
            rate_limit={}, session_summary={"total_executions": 0, "total_cost": 0, "total_savings": 0, "savings_percentage": 0},
            tier_breakdown={}, adaptive_overrides=[],
        )
        assert writer.status_file.exists()

        writer.remove_status()
        assert not writer.status_file.exists()


# ============================================================================
# MCPState Tests (Dashboard Side)
# ============================================================================


class TestMCPState:
    """Tests for dashboard MCPState reading."""

    def test_disabled_when_no_files(self, tmp_path):
        """Test MCPState is disabled when no MCP files exist."""
        from esass.hooks.dashboard import MCPState, ESASS_DATA_DIR

        with patch("esass.hooks.dashboard.ESASS_DATA_DIR", tmp_path), \
             patch("esass.hooks.dashboard.LOG_DIR", tmp_path / "logs"):
            state = MCPState()
            assert not state.enabled

    def test_reads_status_file(self, tmp_path):
        """Test MCPState reads status.json correctly."""
        from esass.hooks.dashboard import MCPState

        # Create status file
        mcp_dir = tmp_path / "mcp"
        mcp_dir.mkdir(parents=True)
        status = {
            "updated_at": "2026-02-14T10:00:00",
            "availability": {"local": True, "huggingface": False, "claude": True},
            "circuit_breakers": {"ollama": {"state": "open", "failure_count": 3}},
            "cache": {"ollama": {"size": 10, "max_size": 50}},
            "rate_limit": {"available_tokens": 5, "capacity": 10},
            "costs": {
                "session_executions": 25,
                "session_cost": 0.001,
                "session_savings": 0.5,
                "savings_percentage": 99.8,
            },
            "tier_breakdown": {"local": 20, "huggingface": 4, "claude": 1},
            "adaptive_overrides": [{"skill": "test", "tier": "huggingface"}],
        }
        with open(mcp_dir / "status.json", "w") as f:
            json.dump(status, f)

        log_dir = tmp_path / "logs"
        log_dir.mkdir(parents=True)

        with patch("esass.hooks.dashboard.ESASS_DATA_DIR", tmp_path), \
             patch("esass.hooks.dashboard.LOG_DIR", log_dir):
            state = MCPState()
            state.update_from_status()

            assert state.enabled
            assert state.availability["local"] is True
            assert state.availability["huggingface"] is False
            assert state.circuit_breakers["ollama"]["state"] == "open"
            assert state.session_executions == 25
            assert state.session_savings == 0.5
            assert state.tier_breakdown["local"] == 20
            assert len(state.adaptive_overrides) == 1

    def test_reads_mcp_events(self, tmp_path):
        """Test MCPState reads mcp_events JSONL."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir(parents=True)

        today = datetime.now().strftime("%Y%m%d")
        event_file = log_dir / f"mcp_events_{today}.jsonl"

        events = [
            {
                "timestamp": "2026-02-14T10:00:01",
                "event_type": "mcp_execution",
                "event_data": {"skill_name": "skill_a", "tier_used": "local", "success": True, "savings": 0.01},
            },
            {
                "timestamp": "2026-02-14T10:00:02",
                "event_type": "mcp_execution",
                "event_data": {"skill_name": "skill_b", "tier_used": "huggingface", "success": True, "savings": 0.005},
            },
        ]

        with open(event_file, "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

        from esass.hooks.dashboard import MCPState

        with patch("esass.hooks.dashboard.ESASS_DATA_DIR", tmp_path), \
             patch("esass.hooks.dashboard.LOG_DIR", log_dir):
            state = MCPState()
            state.update_from_events()

            assert len(state.recent_executions) == 2
            assert state.recent_executions[0]["event_data"]["skill_name"] == "skill_a"
            assert state.recent_executions[1]["event_data"]["skill_name"] == "skill_b"

    def test_incremental_event_reading(self, tmp_path):
        """Test events are read incrementally (no duplicates)."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir(parents=True)

        today = datetime.now().strftime("%Y%m%d")
        event_file = log_dir / f"mcp_events_{today}.jsonl"

        from esass.hooks.dashboard import MCPState

        with patch("esass.hooks.dashboard.ESASS_DATA_DIR", tmp_path), \
             patch("esass.hooks.dashboard.LOG_DIR", log_dir):
            state = MCPState()

            # Write 2 events
            with open(event_file, "w") as f:
                f.write(json.dumps({"timestamp": "t1", "event_type": "mcp_execution", "event_data": {}}) + "\n")
                f.write(json.dumps({"timestamp": "t2", "event_type": "mcp_execution", "event_data": {}}) + "\n")

            state.update_from_events()
            assert len(state.recent_executions) == 2

            # Append 1 more event
            with open(event_file, "a") as f:
                f.write(json.dumps({"timestamp": "t3", "event_type": "mcp_execution", "event_data": {}}) + "\n")

            state.update_from_events()
            assert len(state.recent_executions) == 3  # Not 5


# ============================================================================
# Rendering Tests
# ============================================================================


class TestMCPRendering:
    """Tests for MCP dashboard rendering functions."""

    def test_format_mcp_execution_event(self):
        """Test formatting MCP execution event."""
        from esass.hooks.dashboard import format_mcp_event_line

        event = {
            "timestamp": "2026-02-14T10:30:15",
            "event_type": "mcp_execution",
            "event_data": {
                "skill_name": "fix_import",
                "tier_used": "local",
                "success": True,
                "savings": 0.0149,
            },
        }

        line = format_mcp_event_line(event)
        assert "10:30:15" in line
        assert "fix_import" in line
        assert "0.0149" in line

    def test_format_mcp_circuit_breaker_event(self):
        """Test formatting circuit breaker event."""
        from esass.hooks.dashboard import format_mcp_event_line

        event = {
            "timestamp": "2026-02-14T10:30:15",
            "event_type": "mcp_circuit_breaker",
            "event_data": {
                "name": "ollama",
                "old_state": "closed",
                "new_state": "open",
                "reason": "failures",
            },
        }

        line = format_mcp_event_line(event)
        assert "ollama" in line
        assert "open" in line

    def test_format_mcp_tier_override_event(self):
        """Test formatting tier override event."""
        from esass.hooks.dashboard import format_mcp_event_line

        event = {
            "timestamp": "2026-02-14T10:30:15",
            "event_type": "mcp_tier_override",
            "event_data": {
                "skill_name": "search_skill",
                "old_tier": "local",
                "new_tier": "huggingface",
                "reason": "failure rate",
            },
        }

        line = format_mcp_event_line(event)
        assert "search_skill" in line
        assert "huggingface" in line


# ============================================================================
# Data Path Tests
# ============================================================================


class TestDataPaths:
    """Test that MCP components use the unified data directory."""

    def test_cost_tracker_default_path(self):
        """Test CostTracker uses ESASS_DATA_DIR by default."""
        from esass.mcp.cost_tracker import CostTracker

        with patch.dict(os.environ, {"ESASS_DATA_DIR": "/tmp/test_esass_data"}):
            tracker = CostTracker()
            assert "mcp" in str(tracker.data_dir)
            assert "cost_tracking" in str(tracker.data_dir)

    def test_adaptive_router_default_path(self):
        """Test AdaptiveRouter uses ESASS_DATA_DIR by default."""
        from esass.mcp.adaptive_router import AdaptiveRouter

        with patch.dict(os.environ, {"ESASS_DATA_DIR": "/tmp/test_esass_data"}):
            router = AdaptiveRouter()
            assert "mcp" in str(router.data_dir)
            assert "adaptive_routing" in str(router.data_dir)

    def test_explicit_path_still_works(self, tmp_path):
        """Test explicit data_dir overrides default."""
        from esass.mcp.cost_tracker import CostTracker

        tracker = CostTracker(data_dir=str(tmp_path / "custom"))
        assert str(tracker.data_dir) == str(tmp_path / "custom")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
