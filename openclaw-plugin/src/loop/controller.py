"""
Recursive Learning Loop Controller

Orchestrates the complete ESASS → OpenClaw → ClawHub → OpenClaw cycle.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

# Internal imports
from ..bridge.openclaw_hooks import OpenClawESASSBridge, get_bridge
from ..adapters.skill_formatter import SkillFormatter
from ..adapters.clawhub_client import ClawHubClient, ESASSClawHubPublisher, PublishResult

# ESASS imports
from esass_prototype.storage.log_store import LogStore
from esass_prototype.storage.pattern_store import PatternStore
from esass_prototype.storage.skill_store import SkillStore
from esass_prototype.analysis.pattern_detector import TemporalPatternDetector
from esass_prototype.genesis.template import SkillTemplateGenerator


logger = logging.getLogger(__name__)


class LoopPhase(Enum):
    """Current phase of the recursive loop"""
    IDLE = "idle"
    OBSERVING = "observing"
    DETECTING = "detecting"
    GENERATING = "generating"
    PUBLISHING = "publishing"
    SYNCING = "syncing"


@dataclass
class LoopMetrics:
    """Metrics for loop health monitoring"""
    cycles_completed: int = 0
    events_observed: int = 0
    patterns_detected: int = 0
    skills_generated: int = 0
    skills_published: int = 0
    publish_failures: int = 0
    last_cycle_start: Optional[datetime] = None
    last_cycle_end: Optional[datetime] = None
    last_cycle_duration_seconds: float = 0.0

    # Rolling averages
    avg_patterns_per_cycle: float = 0.0
    avg_skills_per_cycle: float = 0.0


@dataclass
class LoopConfig:
    """Configuration for the recursive loop"""
    # Timing
    observation_window_hours: int = 24
    cycle_interval_hours: int = 6
    min_events_for_detection: int = 100

    # Pattern detection
    min_support: int = 10
    min_confidence: float = 0.8
    min_stability_days: int = 7

    # Skill generation
    auto_generate: bool = True
    max_skills_per_cycle: int = 5

    # Publishing
    auto_publish: bool = True
    publish_confidence_threshold: float = 0.85
    publish_support_threshold: int = 15

    # Safety
    require_human_approval: bool = False
    rate_limit_skills_per_day: int = 10


class RecursiveLoopController:
    """
    Main controller for the ESASS × OpenClaw × ClawHub recursive learning loop.

    This controller orchestrates:
    1. Event observation from OpenClaw via ESASS bridge
    2. Pattern detection from accumulated logs
    3. Skill generation from validated patterns
    4. Automatic publishing to ClawHub
    5. Skill sync back to OpenClaw workspaces
    """

    def __init__(
        self,
        config: Optional[LoopConfig] = None,
        bridge: Optional[OpenClawESASSBridge] = None,
        formatter: Optional[SkillFormatter] = None,
        clawhub_client: Optional[ClawHubClient] = None
    ):
        self.config = config or LoopConfig()
        self.bridge = bridge or get_bridge()
        self.formatter = formatter or SkillFormatter()
        self.clawhub = clawhub_client or ClawHubClient()

        # Stores
        self.log_store = LogStore()
        self.pattern_store = PatternStore()
        self.skill_store = SkillStore()

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

    def on_skill_generated(self, callback: Callable) -> None:
        """Register callback for skill generation events"""
        self._on_skill_generated = callback

    def on_skill_published(self, callback: Callable) -> None:
        """Register callback for skill publish events"""
        self._on_skill_published = callback

    def on_cycle_complete(self, callback: Callable) -> None:
        """Register callback for cycle completion"""
        self._on_cycle_complete = callback

    async def start(self) -> None:
        """Start the recursive loop"""
        self._running = True
        logger.info("Starting recursive learning loop")

        while self._running:
            try:
                await self.run_cycle()

                # Wait for next cycle
                await asyncio.sleep(self.config.cycle_interval_hours * 3600)

            except Exception as e:
                logger.error(f"Cycle error: {e}")
                await asyncio.sleep(60)  # Brief pause on error

    async def stop(self) -> None:
        """Stop the recursive loop"""
        self._running = False
        self.bridge.shutdown()
        logger.info("Stopped recursive learning loop")

    async def run_cycle(self) -> dict:
        """
        Execute one complete learning cycle.

        Returns:
            Cycle results summary
        """
        self.metrics.last_cycle_start = datetime.utcnow()
        logger.info(f"Starting learning cycle {self.metrics.cycles_completed + 1}")

        results = {
            "events_processed": 0,
            "patterns_detected": 0,
            "skills_generated": 0,
            "skills_published": 0,
            "errors": []
        }

        try:
            # Phase 1: Flush observation buffer
            self.phase = LoopPhase.OBSERVING
            self.bridge.flush()

            # Phase 2: Load and analyze logs
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

            # Detect patterns
            detector = TemporalPatternDetector(
                min_support=self.config.min_support,
                min_confidence=self.config.min_confidence,
                min_stability_days=self.config.min_stability_days
            )
            patterns = detector.detect_patterns(logs)
            results["patterns_detected"] = len(patterns)

            # Filter to skill candidates
            candidates = [p for p in patterns if p.skill_candidate]
            logger.info(f"Detected {len(patterns)} patterns, {len(candidates)} candidates")

            # Save patterns
            for pattern in patterns:
                self.pattern_store.save(pattern)

            # Phase 3: Generate skills
            if self.config.auto_generate and candidates:
                self.phase = LoopPhase.GENERATING

                generator = SkillTemplateGenerator()
                skills = generator.generate_from_patterns(
                    candidates[:self.config.max_skills_per_cycle]
                )
                results["skills_generated"] = len(skills)

                # Save skills
                for skill in skills:
                    self.skill_store.save(skill)

                    if self._on_skill_generated:
                        self._on_skill_generated(skill)

                # Phase 4: Publish to ClawHub
                if self.config.auto_publish:
                    self.phase = LoopPhase.PUBLISHING
                    published = await self._publish_skills(skills, candidates)
                    results["skills_published"] = published

            # Phase 5: Sync to OpenClaw
            self.phase = LoopPhase.SYNCING
            await self._sync_to_openclaw()

        except Exception as e:
            logger.error(f"Cycle error: {e}")
            results["errors"].append(str(e))

        finally:
            self.phase = LoopPhase.IDLE
            self.metrics.last_cycle_end = datetime.utcnow()
            self.metrics.last_cycle_duration_seconds = (
                self.metrics.last_cycle_end - self.metrics.last_cycle_start
            ).total_seconds()
            self.metrics.cycles_completed += 1

            # Update rolling metrics
            self._update_rolling_metrics(results)

            if self._on_cycle_complete:
                self._on_cycle_complete(results)

        return results

    async def _publish_skills(
        self,
        skills: list,
        patterns: list
    ) -> int:
        """Publish generated skills to ClawHub"""
        # Check rate limit
        today = datetime.utcnow().date()
        if self._last_publish_date != today:
            self._skills_published_today = 0
            self._last_publish_date = today

        if self._skills_published_today >= self.config.rate_limit_skills_per_day:
            logger.warning("Daily skill publish limit reached")
            return 0

        # Create pattern lookup
        pattern_map = {p.pattern_id: p for p in patterns}

        # Create publisher
        publisher = ESASSClawHubPublisher(
            formatter=self.formatter,
            client=self.clawhub,
            require_confidence=self.config.publish_confidence_threshold,
            require_support=self.config.publish_support_threshold
        )

        published_count = 0

        for skill in skills:
            # Check rate limit
            if self._skills_published_today >= self.config.rate_limit_skills_per_day:
                break

            # Get source pattern
            pattern = None
            if skill.source_pattern_ids:
                pattern = pattern_map.get(skill.source_pattern_ids[0])

            # Human approval check
            if self.config.require_human_approval:
                logger.info(f"Skill {skill.name} awaiting human approval")
                continue

            # Publish
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
        """Sync ClawHub skills to OpenClaw workspace"""
        try:
            # Use clawhub CLI sync
            result = self.clawhub.update(all_skills=True)
            if result:
                logger.info("Synced skills to OpenClaw workspace")
            else:
                logger.warning("Skill sync may have failed")
        except Exception as e:
            logger.error(f"Sync error: {e}")

    def _update_rolling_metrics(self, results: dict) -> None:
        """Update rolling average metrics"""
        n = self.metrics.cycles_completed

        # Update totals
        self.metrics.events_observed += results["events_processed"]
        self.metrics.patterns_detected += results["patterns_detected"]
        self.metrics.skills_generated += results["skills_generated"]

        # Rolling averages
        if n > 0:
            self.metrics.avg_patterns_per_cycle = (
                self.metrics.patterns_detected / n
            )
            self.metrics.avg_skills_per_cycle = (
                self.metrics.skills_generated / n
            )

    def get_status(self) -> dict:
        """Get current loop status"""
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
                "last_cycle_duration": self.metrics.last_cycle_duration_seconds
            },
            "rate_limits": {
                "skills_published_today": self._skills_published_today,
                "daily_limit": self.config.rate_limit_skills_per_day
            }
        }


# Convenience function for quick setup
def create_recursive_loop(
    observation_hours: int = 24,
    cycle_hours: int = 6,
    auto_publish: bool = True
) -> RecursiveLoopController:
    """Create and configure a recursive loop controller"""
    config = LoopConfig(
        observation_window_hours=observation_hours,
        cycle_interval_hours=cycle_hours,
        auto_publish=auto_publish
    )
    return RecursiveLoopController(config=config)
