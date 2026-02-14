#!/usr/bin/env python3
"""Test Phase 5: Cost Tracking and Adaptive Routing."""

import asyncio
import sys
import os

# Add parent dir to path for imports

from esass.mcp.mcp_config import Tier, get_config
from esass.mcp.cost_tracker import CostTracker, get_cost_tracker
from esass.mcp.adaptive_router import AdaptiveRouter, get_adaptive_router
from esass.mcp.tier_router import TierRouter, get_router


async def test_cost_tracker():
    """Test cost tracking functionality."""
    print("\n=== Testing Cost Tracker ===")

    tracker = CostTracker(data_dir="./data/test_cost_tracking")

    # Log some test executions
    tracker.log_execution(
        skill_name="test_file_skill",
        tier_requested=Tier.LOCAL,
        tier_used=Tier.LOCAL,
        fallback_used=False,
        success=True,
        tokens_used=500,
        latency_ms=150.0,
        routing_reason="capability",
    )

    tracker.log_execution(
        skill_name="test_complex_skill",
        tier_requested=Tier.LOCAL,
        tier_used=Tier.HUGGINGFACE,
        fallback_used=True,
        success=True,
        tokens_used=1200,
        latency_ms=800.0,
        routing_reason="capability",
    )

    tracker.log_execution(
        skill_name="test_security_skill",
        tier_requested=Tier.CLAUDE,
        tier_used=Tier.CLAUDE,
        fallback_used=False,
        success=True,
        tokens_used=2000,
        latency_ms=1500.0,
        routing_reason="capability",
    )

    # Get session summary
    summary = tracker.get_session_summary()
    print(f"\nSession Summary:")
    print(f"  Total Executions: {summary['total_executions']}")
    print(f"  Tier Breakdown: {summary['tier_breakdown']}")
    print(f"  Total Cost: ${summary['total_cost']:.6f}")
    print(f"  Total Savings: ${summary['total_savings']:.6f}")
    print(f"  Savings %: {summary['savings_percentage']:.1f}%")

    # Get tier summary
    tier_summary = tracker.get_tier_summary()
    print(f"\nTier Summary:")
    for tier_name, stats in tier_summary['tiers'].items():
        if stats['executions'] > 0:
            print(f"  {tier_name}:")
            print(f"    Executions: {stats['executions']}")
            print(f"    Success Rate: {stats['success_rate']*100:.1f}%")
            print(f"    Cost: ${stats['total_cost']:.6f}")

    # Get projection
    projection = tracker.get_cost_projection(daily_executions=100)
    print(f"\nMonthly Cost Projection (100 exec/day):")
    print(f"  Projected Cost: ${projection['projected_monthly_cost']:.2f}")
    print(f"  If All Claude: ${projection['projected_cost_if_all_claude']:.2f}")
    print(f"  Projected Savings: ${projection['projected_monthly_savings']:.2f} ({projection['projected_savings_percentage']:.1f}%)")

    return True


async def test_adaptive_router():
    """Test adaptive routing functionality."""
    print("\n=== Testing Adaptive Router ===")

    router = AdaptiveRouter(data_dir="./data/test_adaptive_routing")

    # Simulate successful local executions
    skill_name = "file_operations_skill"
    capabilities = ["file_operations", "tool_orchestration"]

    print(f"\nSimulating executions for: {skill_name}")

    # Record 5 successful local executions
    for i in range(5):
        router.record_execution(
            skill_name=skill_name,
            capabilities=capabilities,
            tier_used=Tier.LOCAL,
            success=True,
            latency_ms=100 + i * 10,
        )
    print(f"  Recorded 5 successful local executions")

    # Get tier recommendation (should stay local)
    tier, reason = router.get_tier_recommendation(skill_name, capabilities, Tier.LOCAL)
    print(f"  Recommendation: {tier.value} (reason: {reason or 'default'})")

    # Now simulate failures
    failing_skill = "unstable_skill"
    failing_caps = ["problem_analysis"]

    print(f"\nSimulating failures for: {failing_skill}")

    # Record 3 failed local executions
    for i in range(3):
        router.record_execution(
            skill_name=failing_skill,
            capabilities=failing_caps,
            tier_used=Tier.LOCAL,
            success=False,
            latency_ms=5000,
        )
    print(f"  Recorded 3 failed local executions")

    # Get tier recommendation (should be demoted)
    tier, reason = router.get_tier_recommendation(failing_skill, failing_caps, Tier.LOCAL)
    print(f"  Recommendation: {tier.value} (reason: {reason or 'default'})")

    # Check overrides
    overrides = router.get_all_overrides()
    print(f"\nActive Tier Overrides: {len(overrides)}")
    for override in overrides:
        print(f"  {override['skill_name']}: -> {override['tier_override']} ({override['reason']})")

    # Check capability learning
    cap_learning = router.get_capability_learning()
    print(f"\nCapability Learning Summary:")
    for cap, summary in cap_learning.get('summary', {}).items():
        print(f"  {cap}: best_tier={summary['best_tier']}, local_rate={summary['local_rate']:.2f}")

    return True


async def test_integrated_routing():
    """Test integrated tier router with cost tracking and adaptive learning."""
    print("\n=== Testing Integrated Routing ===")

    router = TierRouter()

    # Test route_skill with adaptive learning
    skill_name = "python_edit_skill"
    capabilities = ["file_operations", "tool_orchestration"]

    routing = await router.route_skill(skill_name, capabilities, estimated_tokens=500)
    print(f"\nRouting Decision for '{skill_name}':")
    print(f"  Tier: {routing.tier.value}")
    print(f"  Reason: {routing.reason.value}")
    print(f"  Details: {routing.details}")

    # Test with a security skill (should route to Claude)
    security_skill = "security_review_skill"
    security_caps = ["security"]

    routing = await router.route_skill(security_skill, security_caps, estimated_tokens=500)
    print(f"\nRouting Decision for '{security_skill}':")
    print(f"  Tier: {routing.tier.value}")
    print(f"  Reason: {routing.reason.value}")
    print(f"  Details: {routing.details}")

    # Get full stats
    stats = await router.get_full_stats()
    print(f"\nFull Statistics Available:")
    print(f"  Has routing stats: {'routing' in stats}")
    print(f"  Has cost stats: {'costs' in stats}")
    print(f"  Has adaptive learning: {'adaptive_learning' in stats}")

    return True


async def test_ollama_connection():
    """Test Ollama connection."""
    print("\n=== Testing Ollama Connection ===")

    from ollama_client import get_ollama_client

    client = await get_ollama_client()
    available = await client.is_available()

    print(f"\nOllama Status:")
    print(f"  Endpoint: {client.endpoint}")
    print(f"  Model: {client.model}")
    print(f"  Available: {available}")

    if available:
        # Quick generation test
        result = await client.generate("Say 'hello' in one word.")
        print(f"  Test Generation: {result.content[:50]}...")

    return available


async def main():
    """Run all Phase 5 tests."""
    print("=" * 60)
    print("Phase 5: Cost Tracking & Adaptive Routing - Test Suite")
    print("=" * 60)

    results = {}

    # Test cost tracker
    try:
        results['cost_tracker'] = await test_cost_tracker()
        print("\n[OK] Cost Tracker tests passed")
    except Exception as e:
        results['cost_tracker'] = False
        print(f"\n[FAIL] Cost Tracker tests failed: {e}")

    # Test adaptive router
    try:
        results['adaptive_router'] = await test_adaptive_router()
        print("\n[OK] Adaptive Router tests passed")
    except Exception as e:
        results['adaptive_router'] = False
        print(f"\n[FAIL] Adaptive Router tests failed: {e}")

    # Test integrated routing
    try:
        results['integrated_routing'] = await test_integrated_routing()
        print("\n[OK] Integrated Routing tests passed")
    except Exception as e:
        results['integrated_routing'] = False
        print(f"\n[FAIL] Integrated Routing tests failed: {e}")

    # Test Ollama connection
    try:
        results['ollama'] = await test_ollama_connection()
        status = "OK" if results['ollama'] else "WARN"
        print(f"\n[{status}] Ollama connection: {'available' if results['ollama'] else 'unavailable'}")
    except Exception as e:
        results['ollama'] = False
        print(f"\n[FAIL] Ollama connection test failed: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)

    all_passed = all(results.values())
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")

    print("\n" + ("All tests passed!" if all_passed else "Some tests failed."))

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
