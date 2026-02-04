"""
Tests for the loop controller module (~8 tests).
"""

import pytest

from openclaw_plugin.loop.phases import LoopPhase
from openclaw_plugin.loop.controller import (
    LoopConfig,
    LoopMetrics,
    RecursiveLoopController,
    create_recursive_loop,
)


class TestLoopPhase:
    def test_all_phases(self):
        phases = [p.value for p in LoopPhase]
        assert "idle" in phases
        assert "observing" in phases
        assert "generating" in phases
        assert "publishing" in phases


class TestLoopConfig:
    def test_defaults(self):
        cfg = LoopConfig()
        assert cfg.observation_window_hours == 24
        assert cfg.rate_limit_skills_per_day == 10
        assert cfg.auto_generate is True


class TestLoopMetrics:
    def test_defaults(self):
        m = LoopMetrics()
        assert m.cycles_completed == 0
        assert m.skills_published == 0


class TestRecursiveLoopController:
    def test_initial_state(self):
        ctrl = RecursiveLoopController()
        assert ctrl.phase == LoopPhase.IDLE
        assert ctrl.metrics.cycles_completed == 0
        assert ctrl._running is False

    def test_get_status(self):
        ctrl = RecursiveLoopController()
        status = ctrl.get_status()
        assert status["phase"] == "idle"
        assert status["running"] is False
        assert "metrics" in status
        assert "rate_limits" in status

    def test_callbacks_registration(self):
        ctrl = RecursiveLoopController()
        called = []
        ctrl.on_skill_generated(lambda s: called.append("gen"))
        ctrl.on_skill_published(lambda s, r: called.append("pub"))
        ctrl.on_cycle_complete(lambda r: called.append("cycle"))
        assert ctrl._on_skill_generated is not None
        assert ctrl._on_skill_published is not None
        assert ctrl._on_cycle_complete is not None

    def test_rate_limit_reset(self):
        ctrl = RecursiveLoopController()
        from datetime import datetime
        ctrl._skills_published_today = 5
        ctrl._last_publish_date = datetime(2020, 1, 1).date()
        # Rate limit resets on new date in _publish_skills

    def test_create_recursive_loop(self):
        ctrl = create_recursive_loop(observation_hours=12, cycle_hours=3)
        assert ctrl.config.observation_window_hours == 12
        assert ctrl.config.cycle_interval_hours == 3

    def test_tracing_integration_params(self):
        ctrl = RecursiveLoopController(
            evolution_tracker="mock_evo",
            lineage_tracker="mock_lin",
        )
        assert ctrl._evolution_tracker == "mock_evo"
        assert ctrl._lineage_tracker == "mock_lin"

    def test_rolling_metrics_update(self):
        ctrl = RecursiveLoopController()
        ctrl.metrics.cycles_completed = 1
        ctrl._update_rolling_metrics({
            "events_processed": 100,
            "patterns_detected": 5,
            "skills_generated": 2,
            "skills_published": 1,
            "errors": [],
        })
        assert ctrl.metrics.events_observed == 100
        assert ctrl.metrics.avg_patterns_per_cycle == 5.0

    def test_phase_transitions_in_get_status(self):
        ctrl = RecursiveLoopController()
        ctrl.phase = LoopPhase.DETECTING
        assert ctrl.get_status()["phase"] == "detecting"
