"""Adaptive routing that learns from execution history.

Provides:
- Learning from failures: demote patterns that fail on lower tiers
- Learning from successes: promote patterns that work well on local
- Semantic caching of routing decisions
- Automatic tier adjustment based on historical performance
"""

import hashlib
import json
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from config import Tier

logger = logging.getLogger(__name__)


@dataclass
class PatternHistory:
    """Execution history for a pattern/skill."""
    pattern_hash: str
    skill_name: str
    capabilities: List[str]

    # Execution counts by tier
    local_attempts: int = 0
    local_successes: int = 0
    hf_attempts: int = 0
    hf_successes: int = 0
    claude_attempts: int = 0
    claude_successes: int = 0

    # Override tier (if learned from failures)
    tier_override: Optional[str] = None
    override_reason: Optional[str] = None
    override_timestamp: Optional[float] = None

    # Performance metrics
    avg_local_latency_ms: float = 0.0
    avg_hf_latency_ms: float = 0.0
    last_execution: Optional[float] = None

    def local_success_rate(self) -> float:
        """Calculate local tier success rate."""
        if self.local_attempts == 0:
            return 1.0  # Optimistic default
        return self.local_successes / self.local_attempts

    def hf_success_rate(self) -> float:
        """Calculate HuggingFace tier success rate."""
        if self.hf_attempts == 0:
            return 1.0
        return self.hf_successes / self.hf_attempts

    def total_attempts(self) -> int:
        """Total attempts across all tiers."""
        return self.local_attempts + self.hf_attempts + self.claude_attempts

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatternHistory":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class AdaptiveConfig:
    """Configuration for adaptive routing."""
    # Failure thresholds
    min_attempts_before_override: int = 3
    failure_rate_threshold: float = 0.5  # Demote if failure rate > 50%

    # Success thresholds
    success_rate_for_promotion: float = 0.9  # Promote if > 90% success
    min_successes_for_promotion: int = 5

    # Decay settings
    override_decay_hours: float = 168.0  # 1 week
    history_retention_days: int = 30

    # Learning rate
    latency_ema_alpha: float = 0.3  # Exponential moving average for latency


class AdaptiveRouter:
    """Learns from execution history to improve routing decisions.

    Features:
    - Tracks success/failure rates per pattern
    - Demotes patterns that fail consistently on lower tiers
    - Promotes patterns that succeed consistently on local
    - Time-decaying overrides (learned decisions fade over time)
    - Semantic similarity for similar patterns
    """

    def __init__(
        self,
        data_dir: str = "./data/adaptive_routing",
        config: Optional[AdaptiveConfig] = None,
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.config = config or AdaptiveConfig()

        # Pattern history cache
        self.pattern_history: Dict[str, PatternHistory] = {}

        # Capability-based learning
        self.capability_success_rates: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"local": 1.0, "huggingface": 1.0, "claude": 1.0}
        )

        # Load persisted history
        self._load_history()

    def _get_history_file(self) -> Path:
        """Get history file path."""
        return self.data_dir / "pattern_history.json"

    def _get_capability_file(self) -> Path:
        """Get capability learning file path."""
        return self.data_dir / "capability_learning.json"

    def _load_history(self) -> None:
        """Load persisted pattern history."""
        history_file = self._get_history_file()
        if history_file.exists():
            try:
                with open(history_file, "r") as f:
                    data = json.load(f)

                for pattern_hash, history_data in data.get("patterns", {}).items():
                    self.pattern_history[pattern_hash] = PatternHistory.from_dict(history_data)

                logger.info(f"Loaded {len(self.pattern_history)} pattern histories")

            except Exception as e:
                logger.warning(f"Failed to load pattern history: {e}")

        # Load capability learning
        capability_file = self._get_capability_file()
        if capability_file.exists():
            try:
                with open(capability_file, "r") as f:
                    data = json.load(f)
                self.capability_success_rates = defaultdict(
                    lambda: {"local": 1.0, "huggingface": 1.0, "claude": 1.0},
                    data.get("capabilities", {})
                )
            except Exception as e:
                logger.warning(f"Failed to load capability learning: {e}")

    def _save_history(self) -> None:
        """Save pattern history to disk."""
        history_file = self._get_history_file()
        try:
            data = {
                "updated_at": time.time(),
                "patterns": {
                    h: p.to_dict() for h, p in self.pattern_history.items()
                },
            }
            with open(history_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save pattern history: {e}")

        # Save capability learning
        capability_file = self._get_capability_file()
        try:
            data = {
                "updated_at": time.time(),
                "capabilities": dict(self.capability_success_rates),
            }
            with open(capability_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save capability learning: {e}")

    def _pattern_hash(self, skill_name: str, capabilities: List[str]) -> str:
        """Generate hash for a skill/capability pattern."""
        key = f"{skill_name}:{','.join(sorted(capabilities))}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _get_or_create_history(
        self,
        skill_name: str,
        capabilities: List[str],
    ) -> PatternHistory:
        """Get or create pattern history."""
        pattern_hash = self._pattern_hash(skill_name, capabilities)

        if pattern_hash not in self.pattern_history:
            self.pattern_history[pattern_hash] = PatternHistory(
                pattern_hash=pattern_hash,
                skill_name=skill_name,
                capabilities=capabilities,
            )

        return self.pattern_history[pattern_hash]

    def record_execution(
        self,
        skill_name: str,
        capabilities: List[str],
        tier_used: Tier,
        success: bool,
        latency_ms: float,
    ) -> None:
        """Record an execution outcome for learning.

        Args:
            skill_name: Name of the executed skill
            capabilities: Skill capabilities
            tier_used: Tier that was actually used
            success: Whether execution succeeded
            latency_ms: Execution latency
        """
        history = self._get_or_create_history(skill_name, capabilities)
        history.last_execution = time.time()

        # Update tier-specific stats
        alpha = self.config.latency_ema_alpha

        if tier_used == Tier.LOCAL:
            history.local_attempts += 1
            if success:
                history.local_successes += 1
            history.avg_local_latency_ms = (
                alpha * latency_ms + (1 - alpha) * history.avg_local_latency_ms
            )

        elif tier_used == Tier.HUGGINGFACE:
            history.hf_attempts += 1
            if success:
                history.hf_successes += 1
            history.avg_hf_latency_ms = (
                alpha * latency_ms + (1 - alpha) * history.avg_hf_latency_ms
            )

        elif tier_used == Tier.CLAUDE:
            history.claude_attempts += 1
            if success:
                history.claude_successes += 1

        # Update capability-based learning
        for cap in capabilities:
            tier_key = tier_used.value
            current_rate = self.capability_success_rates[cap][tier_key]
            # Bayesian update with prior weight
            prior_weight = 10
            new_rate = (
                current_rate * prior_weight + (1 if success else 0)
            ) / (prior_weight + 1)
            self.capability_success_rates[cap][tier_key] = new_rate

        # Check for tier override
        self._evaluate_tier_override(history)

        # Periodically save
        if history.total_attempts() % 10 == 0:
            self._save_history()

    def _evaluate_tier_override(self, history: PatternHistory) -> None:
        """Evaluate if tier override is needed based on history."""
        min_attempts = self.config.min_attempts_before_override

        # Check if local tier should be demoted
        if history.local_attempts >= min_attempts:
            failure_rate = 1 - history.local_success_rate()
            if failure_rate > self.config.failure_rate_threshold:
                # Demote to HuggingFace
                history.tier_override = Tier.HUGGINGFACE.value
                history.override_reason = (
                    f"Local failure rate {failure_rate:.1%} > {self.config.failure_rate_threshold:.1%}"
                )
                history.override_timestamp = time.time()
                logger.info(
                    f"Demoting {history.skill_name} to HuggingFace: {history.override_reason}"
                )
                return

        # Check if HuggingFace should be demoted
        if history.hf_attempts >= min_attempts:
            failure_rate = 1 - history.hf_success_rate()
            if failure_rate > self.config.failure_rate_threshold:
                # Demote to Claude
                history.tier_override = Tier.CLAUDE.value
                history.override_reason = (
                    f"HuggingFace failure rate {failure_rate:.1%} > {self.config.failure_rate_threshold:.1%}"
                )
                history.override_timestamp = time.time()
                logger.info(
                    f"Demoting {history.skill_name} to Claude: {history.override_reason}"
                )
                return

        # Check if local tier can be promoted (remove override)
        if history.tier_override and history.local_attempts >= self.config.min_successes_for_promotion:
            if history.local_success_rate() >= self.config.success_rate_for_promotion:
                logger.info(
                    f"Promoting {history.skill_name} back to local: "
                    f"success rate {history.local_success_rate():.1%}"
                )
                history.tier_override = None
                history.override_reason = None
                history.override_timestamp = None

    def get_tier_recommendation(
        self,
        skill_name: str,
        capabilities: List[str],
        default_tier: Tier,
    ) -> Tuple[Tier, Optional[str]]:
        """Get tier recommendation based on learning.

        Args:
            skill_name: Name of the skill
            capabilities: Skill capabilities
            default_tier: Default tier from static routing

        Returns:
            Tuple of (recommended tier, reason or None if using default)
        """
        history = self._get_or_create_history(skill_name, capabilities)

        # Check for tier override (with decay)
        if history.tier_override and history.override_timestamp:
            decay_hours = self.config.override_decay_hours
            age_hours = (time.time() - history.override_timestamp) / 3600

            if age_hours < decay_hours:
                return Tier(history.tier_override), history.override_reason
            else:
                # Override has decayed - reset and try again
                logger.debug(f"Override for {skill_name} has decayed, resetting")
                history.tier_override = None
                history.override_reason = None
                history.override_timestamp = None

        # Check capability-based recommendations
        if capabilities:
            avg_local_rate = sum(
                self.capability_success_rates[cap]["local"]
                for cap in capabilities
            ) / len(capabilities)

            if avg_local_rate < 0.5 and default_tier == Tier.LOCAL:
                # Low success rate for these capabilities - recommend HF
                return Tier.HUGGINGFACE, f"Capability success rate {avg_local_rate:.1%} on local"

        return default_tier, None

    def get_pattern_stats(self, skill_name: str, capabilities: List[str]) -> Dict[str, Any]:
        """Get detailed statistics for a pattern."""
        pattern_hash = self._pattern_hash(skill_name, capabilities)

        if pattern_hash not in self.pattern_history:
            return {"status": "no_history", "pattern_hash": pattern_hash}

        history = self.pattern_history[pattern_hash]

        return {
            "pattern_hash": pattern_hash,
            "skill_name": history.skill_name,
            "capabilities": history.capabilities,
            "local": {
                "attempts": history.local_attempts,
                "successes": history.local_successes,
                "success_rate": round(history.local_success_rate(), 3),
                "avg_latency_ms": round(history.avg_local_latency_ms, 2),
            },
            "huggingface": {
                "attempts": history.hf_attempts,
                "successes": history.hf_successes,
                "success_rate": round(history.hf_success_rate(), 3),
                "avg_latency_ms": round(history.avg_hf_latency_ms, 2),
            },
            "claude": {
                "attempts": history.claude_attempts,
                "successes": history.claude_successes,
            },
            "tier_override": history.tier_override,
            "override_reason": history.override_reason,
            "last_execution": history.last_execution,
        }

    def get_all_overrides(self) -> List[Dict[str, Any]]:
        """Get all active tier overrides."""
        overrides = []
        for pattern_hash, history in self.pattern_history.items():
            if history.tier_override:
                overrides.append({
                    "pattern_hash": pattern_hash,
                    "skill_name": history.skill_name,
                    "tier_override": history.tier_override,
                    "reason": history.override_reason,
                    "timestamp": history.override_timestamp,
                })
        return overrides

    def get_capability_learning(self) -> Dict[str, Any]:
        """Get learned capability success rates."""
        return {
            "capabilities": dict(self.capability_success_rates),
            "summary": {
                cap: {
                    "best_tier": max(rates, key=rates.get),
                    "local_rate": round(rates["local"], 3),
                    "hf_rate": round(rates["huggingface"], 3),
                }
                for cap, rates in self.capability_success_rates.items()
            },
        }

    def clear_history(self, older_than_days: Optional[int] = None) -> int:
        """Clear old pattern history.

        Args:
            older_than_days: Only clear patterns older than this (None = all)

        Returns:
            Number of patterns cleared
        """
        if older_than_days is None:
            count = len(self.pattern_history)
            self.pattern_history.clear()
            self._save_history()
            return count

        cutoff = time.time() - (older_than_days * 86400)
        to_remove = [
            h for h, p in self.pattern_history.items()
            if p.last_execution and p.last_execution < cutoff
        ]

        for h in to_remove:
            del self.pattern_history[h]

        self._save_history()
        return len(to_remove)

    def flush(self) -> None:
        """Force save all history to disk."""
        self._save_history()


# Singleton instance
_router: Optional[AdaptiveRouter] = None


def get_adaptive_router(data_dir: Optional[str] = None) -> AdaptiveRouter:
    """Get the global adaptive router instance."""
    global _router
    if _router is None:
        _router = AdaptiveRouter(
            data_dir=data_dir or os.environ.get(
                "ADAPTIVE_ROUTING_DIR",
                "./data/adaptive_routing"
            )
        )
    return _router
