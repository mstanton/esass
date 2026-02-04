"""
Recursive Learning Loop Controller (rewritten).

Orchestrates the complete ESASS → OpenClaw → ClawHub → OpenClaw cycle,
with integrated tracing for evolution and lineage tracking.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .phases import LoopPhase

logger = logging.getLogger(__name__)


@dataclass
class LoopMetrics:
    """Metrics for loop health monitoring."""
    cycles_completed: int = 0
    events_observed: int = 0
    patterns_detected: int = 0
    skills_generated: int = 0
    skills_published: int = 0
    publish_failures: int = 0
    last_cycle_start: Optional[datetime] = None
    last_cycle_end: Optional[datetime] = None
    last_cycle_duration_seconds: float = 0.0
    avg_patterns_per_cycle: float = 0.0
    avg_skills_per_cycle: float = 0.0


@dataclass
class LoopConfig:
    """Configuration for the recursive loop."""
    observation_window_hours: int = 24
    cycle_interval_hours: int = 6
    min_events_for_detection: int = 100
    min_support: int = 10
    min_confidence: float = 0.8
    min_stability_days: int = 7
    auto_generate: bool = True
    max_skills_per_cycle: int = 5
    auto_publish: bool = True
    publish_confidence_threshold: float = 0.85
    publish_support_threshold: int = 15
    require_human_approval: bool = False
    rate_limit_skills_per_day: int = 10


class RecursiveLoopController:
    """
    Main controller for the ESASS × OpenClaw × ClawHub recursive learning loop.

    Orchestrates:
    1. Event observation from OpenClaw via ESASS bridge
    2. Pattern detection from accumulated logs
    3. Skill generation from validated patterns
    4. Automatic publishing to ClawHub
    5. Skill sync back to OpenClaw workspaces
    6. Evolution / lineage tracing on every skill lifecycle event
    """

    def __init__(
        self,
        config: Optional[LoopConfig] = None,
        bridge: Optional[Any] = None,
        formatter: Optional[Any] = None,
        clawhub_client: Optional[Any] = None,
        evolution_tracker: Optional[Any] = None,
        lineage_tracker: Optional[Any] = None,
    ):
        self.config = config or LoopConfig()

        # Lazy imports to avoid circular deps when running without full ESASS
        self._bridge = bridge
        self._formatter = formatter
        self._clawhub = clawhub_client

        # Tracing
        self._evolution_tracker = evolution_tracker
        self._lineage_tracker = lineage_tracker

        # Stores (lazy)
        self._log_store: Optional[Any] = None
        self._pattern_store: Optional[Any] = None
        self._skill_store: Optional[Any] = None

        # State
        self.phase = LoopPhase.IDLE
        self.metrics = LoopMetrics()
        self._running = False
        self._skills_published_today = 0
        self._last_publish_date: Optional[datetime] = None

        # Callbacks
        self._on_skill_generated: Optional[Callable] = None
        self._on_skill_published: Optional[Callable] = None
        self._on_cycle_complete: Optional[Callable] = None

    # ---- Lazy accessors ----

    @property
    def bridge(self) -> Any:
        if self._bridge is None:
            from openclaw_plugin.bridge.hooks import get_bridge
            self._bridge = get_bridge()
        return self._bridge

    @property
    def formatter(self) -> Any:
        if self._formatter is None:
            from openclaw_plugin.adapters.skill_formatter import SkillFormatter
            self._formatter = SkillFormatter()
        return self._formatter

    @property
    def clawhub(self) -> Any:
        if self._clawhub is None:
            from openclaw_plugin.adapters.clawhub_client import ClawHubClient
            self._clawhub = ClawHubClient()
        return self._clawhub

    @property
    def log_store(self) -> Any:
        if self._log_store is None:
            from esass_prototype.storage.log_store import LogStore
            self._log_store = LogStore()
        return self._log_store

    @property
    def pattern_store(self) -> Any:
        if self._pattern_store is None:
            from esass_prototype.storage.pattern_store import PatternStore
            self._pattern_store = PatternStore()
        return self._pattern_store

    @property
    def skill_store(self) -> Any:
        if self._skill_store is None:
            from esass_prototype.storage.skill_store import SkillStore
            self._skill_store = SkillStore()
        return self._skill_store

    # ---- Callbacks ----

    def on_skill_generated(self, callback: Callable) -> None:
        self._on_skill_generated = callback

    def on_skill_published(self, callback: Callable) -> None:
        self._on_skill_published = callback

    def on_cycle_complete(self, callback: Callable) -> None:
        self._on_cycle_complete = callback

    # ---- Main loop ----

    async def start(self) -> None:
        self._running = True
        logger.info("Starting recursive learning loop")
        while self._running:
            try:
                await self.run_cycle()
                await asyncio.sleep(self.config.cycle_interval_hours * 3600)
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                await asyncio.sleep(60)

    async def stop(self) -> None:
        self._running = False
        self.bridge.shutdown()
        logger.info("Stopped recursive learning loop")

    async def run_cycle(self) -> Dict[str, Any]:
        """Execute one complete learning cycle."""
        self.metrics.last_cycle_start = datetime.utcnow()
        logger.info(f"Starting learning cycle {self.metrics.cycles_completed + 1}")

        results: Dict[str, Any] = {
            "events_processed": 0,
            "patterns_detected": 0,
            "skills_generated": 0,
            "skills_published": 0,
            "errors": [],
        }

        try:
            # Phase 1: Flush observation buffer
            self.phase = LoopPhase.OBSERVING
            self.bridge.flush()

            # Phase 2: Load and analyse logs
            self.phase = LoopPhase.DETECTING
            logs = self.log_store.read_last_n_days(
                self.config.observation_window_hours // 24 or 1
            )
            results["events_processed"] = len(logs)

            if len(logs) < self.config.min_events_for_detection:
                logger.info(
                    f"Insufficient events ({len(logs)}) for detection, "
                    f"need {self.config.min_events_for_detection}"
                )
                return results

            from esass_prototype.analysis.pattern_detector import TemporalPatternDetector
            detector = TemporalPatternDetector(
                min_support=self.config.min_support,
                min_confidence=self.config.min_confidence,
                min_stability_days=self.config.min_stability_days,
            )
            patterns = detector.detect_patterns(logs)
            results["patterns_detected"] = len(patterns)

            candidates = [p for p in patterns if p.skill_candidate]
            logger.info(f"Detected {len(patterns)} patterns, {len(candidates)} candidates")

            for pattern in patterns:
                self.pattern_store.save(pattern)

            # Phase 3: Generate skills
            if self.config.auto_generate and candidates:
                self.phase = LoopPhase.GENERATING

                from esass_prototype.genesis.template import SkillTemplateGenerator
                generator = SkillTemplateGenerator()
                skills = generator.generate_from_patterns(
                    candidates[: self.config.max_skills_per_cycle]
                )
                results["skills_generated"] = len(skills)

                for skill in skills:
                    self.skill_store.save(skill)

                    # Tracing: record creation
                    if self._evolution_tracker:
                        self._evolution_tracker.record_creation(
                            skill_id=skill.skill_id,
                            version=skill.version,
                            rationale="Pattern-based genesis",
                            triggered_by="loop_cycle",
                            related_pattern_ids=skill.source_pattern_ids,
                        )

                    # Tracing: lineage parent-child from parent_skill_ids
                    if self._lineage_tracker and getattr(skill, "parent_skill_ids", None):
                        for parent_id in skill.parent_skill_ids:
                            self._lineage_tracker.record_parent_child(
                                parent_id=parent_id,
                                child_id=skill.skill_id,
                                evidence="genesis",
                            )

                    if self._on_skill_generated:
                        self._on_skill_generated(skill)

                # Phase 4: Publish to ClawHub
                if self.config.auto_publish:
                    self.phase = LoopPhase.PUBLISHING
                    published = await self._publish_skills(skills, candidates)
                    results["skills_published"] = published

            # Phase 5: Sync
            self.phase = LoopPhase.SYNCING
            await self._sync_to_openclaw()

        except Exception as e:
            logger.error(f"Cycle error: {e}")
            results["errors"].append(str(e))

        finally:
            self.phase = LoopPhase.IDLE
            self.metrics.last_cycle_end = datetime.utcnow()
            if self.metrics.last_cycle_start:
                self.metrics.last_cycle_duration_seconds = (
                    self.metrics.last_cycle_end - self.metrics.last_cycle_start
                ).total_seconds()
            self.metrics.cycles_completed += 1
            self._update_rolling_metrics(results)
            if self._on_cycle_complete:
                self._on_cycle_complete(results)

        return results

    # ---- Publishing ----

    async def _publish_skills(self, skills: List[Any], patterns: List[Any]) -> int:
        today = datetime.utcnow().date()
        if self._last_publish_date != today:
            self._skills_published_today = 0
            self._last_publish_date = today

        if self._skills_published_today >= self.config.rate_limit_skills_per_day:
            logger.warning("Daily skill publish limit reached")
            return 0

        from openclaw_plugin.adapters.clawhub_client import ESASSClawHubPublisher, PublishResult
        pattern_map = {p.pattern_id: p for p in patterns}

        publisher = ESASSClawHubPublisher(
            formatter=self.formatter,
            client=self.clawhub,
            require_confidence=self.config.publish_confidence_threshold,
            require_support=self.config.publish_support_threshold,
        )

        published_count = 0
        for skill in skills:
            if self._skills_published_today >= self.config.rate_limit_skills_per_day:
                break
            pattern = pattern_map.get(skill.source_pattern_ids[0]) if skill.source_pattern_ids else None
            if self.config.require_human_approval:
                logger.info(f"Skill {skill.name} awaiting human approval")
                continue
            response = publisher.publish_skill(skill, pattern)
            if response.result == PublishResult.SUCCESS:
                published_count += 1
                self._skills_published_today += 1
                self.metrics.skills_published += 1
                logger.info(f"Published skill: {response.skill_slug} v{response.version}")
                if self._on_skill_published:
                    self._on_skill_published(skill, response)
            elif response.result == PublishResult.ALREADY_EXISTS:
                logger.debug(f"Skill already exists: {response.skill_slug}")
            else:
                self.metrics.publish_failures += 1
                logger.warning(f"Failed to publish {skill.name}: {response.message}")

        return published_count

    async def _sync_to_openclaw(self) -> None:
        try:
            result = self.clawhub.update(all_skills=True)
            if result:
                logger.info("Synced skills to OpenClaw workspace")
            else:
                logger.warning("Skill sync may have failed")
        except Exception as e:
            logger.error(f"Sync error: {e}")

    # ---- Metrics ----

    def _update_rolling_metrics(self, results: Dict[str, Any]) -> None:
        n = self.metrics.cycles_completed
        self.metrics.events_observed += results["events_processed"]
        self.metrics.patterns_detected += results["patterns_detected"]
        self.metrics.skills_generated += results["skills_generated"]
        if n > 0:
            self.metrics.avg_patterns_per_cycle = self.metrics.patterns_detected / n
            self.metrics.avg_skills_per_cycle = self.metrics.skills_generated / n

    def get_status(self) -> Dict[str, Any]:
        return {
            "phase": self.phase.value,
            "running": self._running,
            "metrics": {
                "cycles_completed": self.metrics.cycles_completed,
                "events_observed": self.metrics.events_observed,
                "patterns_detected": self.metrics.patterns_detected,
                "skills_generated": self.metrics.skills_generated,
                "skills_published": self.metrics.skills_published,
                "publish_failures": self.metrics.publish_failures,
                "avg_patterns_per_cycle": round(self.metrics.avg_patterns_per_cycle, 2),
                "avg_skills_per_cycle": round(self.metrics.avg_skills_per_cycle, 2),
                "last_cycle_duration": self.metrics.last_cycle_duration_seconds,
            },
            "rate_limits": {
                "skills_published_today": self._skills_published_today,
                "daily_limit": self.config.rate_limit_skills_per_day,
            },
        }


def create_recursive_loop(
    observation_hours: int = 24,
    cycle_hours: int = 6,
    auto_publish: bool = True,
    evolution_tracker: Optional[Any] = None,
    lineage_tracker: Optional[Any] = None,
) -> RecursiveLoopController:
    """Create and configure a recursive loop controller."""
    config = LoopConfig(
        observation_window_hours=observation_hours,
        cycle_interval_hours=cycle_hours,
        auto_publish=auto_publish,
    )
    return RecursiveLoopController(
        config=config,
        evolution_tracker=evolution_tracker,
        lineage_tracker=lineage_tracker,
    )
