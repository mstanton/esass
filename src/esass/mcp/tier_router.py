"""3-Tier routing logic for skill execution.

Enhanced with:
- Cost tracking for tier usage analytics
- Adaptive routing that learns from execution history
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable

from esass.mcp.mcp_config import Tier, get_config, LocalLLMConfig
from esass.mcp.ollama_client import OllamaClient, get_ollama_client
from esass.mcp.huggingface_client import HuggingFaceClient, get_huggingface_client
from esass.mcp.cost_tracker import CostTracker, get_cost_tracker
from esass.mcp.adaptive_router import AdaptiveRouter, get_adaptive_router

logger = logging.getLogger(__name__)


class RoutingDecision(Enum):
    """Reason for routing decision."""
    TASK_TYPE = "task_type"           # Routed based on task type rules
    CAPABILITY = "capability"          # Routed based on skill capability
    TOKEN_LIMIT = "token_limit"        # Exceeded local token limit
    AVAILABILITY = "availability"      # Tier unavailable, using fallback
    ERROR_FALLBACK = "error_fallback"  # Previous tier failed
    ADAPTIVE_LEARNING = "adaptive"    # Learned from execution history


@dataclass
class RoutingResult:
    """Result of a routing decision."""
    tier: Tier
    reason: RoutingDecision
    details: str
    fallback_chain: List[Tier]  # Ordered fallback tiers if this fails


@dataclass
class ExecutionResult:
    """Result of skill execution."""
    success: bool
    tier_used: Tier
    content: Any
    tokens_used: int | None = None
    fallback_used: bool = False
    error: str | None = None


class TierRouter:
    """Routes skill execution to appropriate tier based on task and availability.

    Enhanced with:
    - Cost tracking for every execution
    - Adaptive routing that learns from failures/successes
    - Historical analytics and projections
    """

    def __init__(self, config: LocalLLMConfig | None = None):
        self.config = config or get_config()
        self._ollama: OllamaClient | None = None
        self._huggingface: HuggingFaceClient | None = None

        # Track tier availability
        self._tier_available: Dict[Tier, bool | None] = {
            Tier.LOCAL: None,
            Tier.HUGGINGFACE: None,
            Tier.CLAUDE: True,  # Always available (passthrough)
        }

        # Track failure counts for adaptive routing
        self._failure_counts: Dict[Tier, int] = {
            Tier.LOCAL: 0,
            Tier.HUGGINGFACE: 0,
            Tier.CLAUDE: 0,
        }

        # Cost tracking and adaptive routing
        self._cost_tracker: CostTracker | None = None
        self._adaptive_router: AdaptiveRouter | None = None

    async def _get_cost_tracker(self) -> CostTracker:
        """Get cost tracker instance."""
        if self._cost_tracker is None:
            self._cost_tracker = get_cost_tracker()
        return self._cost_tracker

    async def _get_adaptive_router(self) -> AdaptiveRouter:
        """Get adaptive router instance."""
        if self._adaptive_router is None:
            self._adaptive_router = get_adaptive_router()
        return self._adaptive_router

    async def _get_ollama(self) -> OllamaClient:
        """Get Ollama client instance."""
        if self._ollama is None:
            self._ollama = await get_ollama_client()
        return self._ollama

    async def _get_huggingface(self) -> HuggingFaceClient:
        """Get HuggingFace client instance."""
        if self._huggingface is None:
            self._huggingface = await get_huggingface_client()
        return self._huggingface

    async def check_tier_availability(self, tier: Tier) -> bool:
        """Check if a tier is available for execution."""
        if tier == Tier.CLAUDE:
            return True  # Always available (passthrough)

        if tier == Tier.LOCAL:
            ollama = await self._get_ollama()
            available = await ollama.is_available()
            self._tier_available[tier] = available
            return available

        if tier == Tier.HUGGINGFACE:
            hf = await self._get_huggingface()
            available = await hf.is_available()
            self._tier_available[tier] = available
            return available

        return False

    def route_by_task_type(self, task_type: str) -> RoutingResult:
        """Route based on task type from config rules."""
        tier = self.config.get_tier_for_task(task_type)

        # Build fallback chain
        if tier == Tier.LOCAL:
            fallback_chain = [Tier.HUGGINGFACE, Tier.CLAUDE]
        elif tier == Tier.HUGGINGFACE:
            fallback_chain = [Tier.LOCAL, Tier.CLAUDE]
        else:
            fallback_chain = []  # Claude has no fallback

        return RoutingResult(
            tier=tier,
            reason=RoutingDecision.TASK_TYPE,
            details=f"Task type '{task_type}' routes to {tier.value}",
            fallback_chain=fallback_chain,
        )

    def route_by_capability(self, capabilities: List[str]) -> RoutingResult:
        """Route based on skill capabilities."""
        if not capabilities:
            return RoutingResult(
                tier=Tier.LOCAL,
                reason=RoutingDecision.CAPABILITY,
                details="No capabilities specified, defaulting to local",
                fallback_chain=[Tier.HUGGINGFACE, Tier.CLAUDE],
            )

        # Average the capability scores
        scores = [self.config.capability_tiers.get(cap, 0.5) for cap in capabilities]
        avg_score = sum(scores) / len(scores)

        if avg_score >= 0.7:
            tier = Tier.LOCAL
            fallback_chain = [Tier.HUGGINGFACE, Tier.CLAUDE]
        elif avg_score >= 0.4:
            tier = Tier.HUGGINGFACE
            fallback_chain = [Tier.LOCAL, Tier.CLAUDE]
        else:
            tier = Tier.CLAUDE
            fallback_chain = []

        return RoutingResult(
            tier=tier,
            reason=RoutingDecision.CAPABILITY,
            details=f"Capability score {avg_score:.2f} routes to {tier.value}",
            fallback_chain=fallback_chain,
        )

    def route_by_token_estimate(self, estimated_tokens: int) -> RoutingResult:
        """Route based on estimated token count."""
        if estimated_tokens <= self.config.max_local_tokens:
            return RoutingResult(
                tier=Tier.LOCAL,
                reason=RoutingDecision.TOKEN_LIMIT,
                details=f"{estimated_tokens} tokens within local limit",
                fallback_chain=[Tier.HUGGINGFACE, Tier.CLAUDE],
            )
        else:
            return RoutingResult(
                tier=Tier.HUGGINGFACE,
                reason=RoutingDecision.TOKEN_LIMIT,
                details=f"{estimated_tokens} tokens exceeds local limit ({self.config.max_local_tokens})",
                fallback_chain=[Tier.CLAUDE],
            )

    async def route_skill(
        self,
        skill_name: str,
        capabilities: List[str],
        estimated_tokens: int = 500,
    ) -> RoutingResult:
        """Determine the best tier for executing a skill.

        Considers:
        1. Adaptive learning from execution history (first priority)
        2. Skill capabilities
        3. Token estimate
        4. Tier availability
        """
        # First, route by capability (baseline)
        cap_route = self.route_by_capability(capabilities)

        # Check adaptive routing - learned from execution history
        adaptive_router = await self._get_adaptive_router()
        adaptive_tier, adaptive_reason = adaptive_router.get_tier_recommendation(
            skill_name, capabilities, cap_route.tier
        )

        if adaptive_tier != cap_route.tier and adaptive_reason:
            # Adaptive learning overrides baseline routing
            if adaptive_tier == Tier.LOCAL:
                fallback_chain = [Tier.HUGGINGFACE, Tier.CLAUDE]
            elif adaptive_tier == Tier.HUGGINGFACE:
                fallback_chain = [Tier.LOCAL, Tier.CLAUDE]
            else:
                fallback_chain = []

            cap_route = RoutingResult(
                tier=adaptive_tier,
                reason=RoutingDecision.ADAPTIVE_LEARNING,
                details=f"Adaptive: {adaptive_reason}",
                fallback_chain=fallback_chain,
            )

        # Check token limit
        if estimated_tokens > self.config.max_local_tokens and cap_route.tier == Tier.LOCAL:
            # Override to HuggingFace for long context
            cap_route = RoutingResult(
                tier=Tier.HUGGINGFACE,
                reason=RoutingDecision.TOKEN_LIMIT,
                details=f"Token count {estimated_tokens} exceeds local limit",
                fallback_chain=[Tier.CLAUDE],
            )

        # Check if chosen tier is available
        if not await self.check_tier_availability(cap_route.tier):
            # Find first available tier in fallback chain
            for fallback_tier in cap_route.fallback_chain:
                if await self.check_tier_availability(fallback_tier):
                    return RoutingResult(
                        tier=fallback_tier,
                        reason=RoutingDecision.AVAILABILITY,
                        details=f"{cap_route.tier.value} unavailable, falling back to {fallback_tier.value}",
                        fallback_chain=[t for t in cap_route.fallback_chain if t != fallback_tier],
                    )

            # All tiers unavailable except Claude
            return RoutingResult(
                tier=Tier.CLAUDE,
                reason=RoutingDecision.AVAILABILITY,
                details="All local tiers unavailable, using Claude",
                fallback_chain=[],
            )

        return cap_route

    async def execute_with_fallback(
        self,
        routing: RoutingResult,
        executor: Callable[[Tier], Awaitable[Dict[str, Any]]],
        skill_name: str = "unknown",
        capabilities: Optional[List[str]] = None,
    ) -> ExecutionResult:
        """Execute on the routed tier with automatic fallback on failure.

        Args:
            routing: The routing decision
            executor: Async function that takes a Tier and returns execution result
            skill_name: Name of skill being executed (for tracking)
            capabilities: Skill capabilities (for adaptive learning)

        Returns:
            ExecutionResult with the final outcome
        """
        tiers_to_try = [routing.tier] + routing.fallback_chain
        last_error = None
        fallback_used = False
        capabilities = capabilities or []

        cost_tracker = await self._get_cost_tracker()
        adaptive_router = await self._get_adaptive_router()

        for i, tier in enumerate(tiers_to_try):
            if tier == Tier.CLAUDE:
                # Claude is passthrough - return indication to use Claude
                return ExecutionResult(
                    success=True,
                    tier_used=Tier.CLAUDE,
                    content={"passthrough": True, "reason": "Use Claude API"},
                    fallback_used=fallback_used,
                )

            try:
                if not await self.check_tier_availability(tier):
                    fallback_used = True
                    continue

                # Track execution time
                start_time = time.time()
                result = await executor(tier)
                latency_ms = (time.time() - start_time) * 1000

                tokens_used = result.get("tokens", 500)  # Estimate if not provided
                success = result.get("success", True)

                if success:
                    # Reset failure count on success
                    self._failure_counts[tier] = 0

                    # Log cost
                    cost_tracker.log_execution(
                        skill_name=skill_name,
                        tier_requested=routing.tier,
                        tier_used=tier,
                        fallback_used=fallback_used,
                        success=True,
                        tokens_used=tokens_used,
                        latency_ms=latency_ms,
                        routing_reason=routing.reason.value,
                    )

                    # Record for adaptive learning
                    adaptive_router.record_execution(
                        skill_name=skill_name,
                        capabilities=capabilities,
                        tier_used=tier,
                        success=True,
                        latency_ms=latency_ms,
                    )

                    return ExecutionResult(
                        success=True,
                        tier_used=tier,
                        content=result,
                        tokens_used=tokens_used,
                        fallback_used=fallback_used,
                    )
                else:
                    # Execution returned failure
                    self._failure_counts[tier] += 1
                    last_error = result.get("error", "Execution failed")

                    # Log failed attempt
                    cost_tracker.log_execution(
                        skill_name=skill_name,
                        tier_requested=routing.tier,
                        tier_used=tier,
                        fallback_used=fallback_used,
                        success=False,
                        tokens_used=tokens_used,
                        latency_ms=latency_ms,
                        error=last_error,
                        routing_reason=routing.reason.value,
                    )

                    # Record for adaptive learning
                    adaptive_router.record_execution(
                        skill_name=skill_name,
                        capabilities=capabilities,
                        tier_used=tier,
                        success=False,
                        latency_ms=latency_ms,
                    )

                    fallback_used = True

            except Exception as e:
                self._failure_counts[tier] += 1
                last_error = str(e)
                fallback_used = True
                logger.warning(f"Tier {tier.value} failed: {e}")

                # Record exception for adaptive learning
                adaptive_router.record_execution(
                    skill_name=skill_name,
                    capabilities=capabilities,
                    tier_used=tier,
                    success=False,
                    latency_ms=0,
                )

        # All tiers failed
        return ExecutionResult(
            success=False,
            tier_used=Tier.CLAUDE,
            content={"passthrough": True, "reason": "All local tiers failed"},
            fallback_used=True,
            error=last_error,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get basic routing statistics (synchronous)."""
        return {
            "availability": {t.value: v for t, v in self._tier_available.items()},
            "failure_counts": {t.value: v for t, v in self._failure_counts.items()},
        }

    async def get_full_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics including costs and adaptive learning."""
        cost_tracker = await self._get_cost_tracker()
        adaptive_router = await self._get_adaptive_router()

        return {
            "routing": self.get_stats(),
            "costs": {
                "session": cost_tracker.get_session_summary(),
                "tier_summary": cost_tracker.get_tier_summary(),
                "projection": cost_tracker.get_cost_projection(),
            },
            "adaptive_learning": {
                "active_overrides": adaptive_router.get_all_overrides(),
                "capability_learning": adaptive_router.get_capability_learning(),
            },
        }

    async def get_cost_dashboard(self) -> Dict[str, Any]:
        """Get cost tracking dashboard data."""
        cost_tracker = await self._get_cost_tracker()

        return {
            "session_summary": cost_tracker.get_session_summary(),
            "tier_summary": cost_tracker.get_tier_summary(),
            "today": cost_tracker.get_daily_report().to_dict(),
            "weekly": [r.to_dict() for r in cost_tracker.get_weekly_report()],
            "projection": cost_tracker.get_cost_projection(),
        }

    async def flush_tracking(self) -> None:
        """Force save all tracking data to disk."""
        cost_tracker = await self._get_cost_tracker()
        adaptive_router = await self._get_adaptive_router()
        cost_tracker.flush()
        adaptive_router.flush()


# Singleton instance
_router: TierRouter | None = None


async def get_router() -> TierRouter:
    """Get the global router instance."""
    global _router
    if _router is None:
        _router = TierRouter()
    return _router
