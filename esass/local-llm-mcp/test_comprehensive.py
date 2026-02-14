#!/usr/bin/env python3
"""Comprehensive test of Phase 5 features: Cost Tracking & Adaptive Routing."""

import asyncio
import json
import sys
import os
import time
import pytest

sys.path.insert(0, os.path.dirname(__file__))

from config import Tier, get_config
from tier_router import TierRouter
from ollama_client import OllamaClient
from cost_tracker import CostTracker
from adaptive_router import AdaptiveRouter


@pytest.mark.asyncio
async def test_multiple_skill_executions():
    """Test multiple skill executions with cost tracking."""
    print("\n" + "=" * 70)
    print("TEST 1: Multiple Skill Executions with Cost Tracking")
    print("=" * 70)

    # Fresh instances for clean test
    router = TierRouter()
    cost_tracker = CostTracker(data_dir="./data/test_comprehensive/costs")

    # Inject trackers
    router._cost_tracker = cost_tracker
    router._adaptive_router = AdaptiveRouter(data_dir="./data/test_comprehensive/adaptive")

    skills = [
        ("file_scanner_skill", ["file_operations"], "Scan directory for Python files"),
        ("code_search_skill", ["file_operations", "tool_orchestration"], "Search for function definitions"),
        ("git_commit_skill", ["git_operations", "tool_orchestration"], "Stage and commit changes"),
        ("test_suite_skill", ["testing"], "Run pytest with coverage"),
        ("doc_generator_skill", ["documentation", "file_operations"], "Generate docstrings"),
        ("config_updater_skill", ["file_operations"], "Update configuration file"),
        ("security_audit_skill", ["security"], "Audit code for vulnerabilities"),  # Should route to Claude
        ("refactor_skill", ["file_operations", "tool_orchestration"], "Refactor function"),
    ]

    print(f"\nExecuting {len(skills)} skills...\n")

    for skill_name, capabilities, description in skills:
        # Get routing
        routing = await router.route_skill(skill_name, capabilities, estimated_tokens=400)

        tier_symbol = {"local": "[L]", "huggingface": "[H]", "claude": "[C]"}
        print(f"  {tier_symbol.get(routing.tier.value, '[?]')} {skill_name}")
        print(f"      Capabilities: {capabilities}")
        print(f"      Route: {routing.tier.value} ({routing.reason.value})")

        # Execute
        async def executor(tier: Tier):
            if tier == Tier.LOCAL:
                client = OllamaClient()
                return await client.execute_skill(skill_name, description, {"test": True})
            elif tier == Tier.HUGGINGFACE:
                return {"success": False, "error": "HF not configured"}
            else:
                return {"passthrough": True, "tier": "claude"}

        result = await router.execute_with_fallback(
            routing, executor,
            skill_name=skill_name,
            capabilities=capabilities,
        )

        status = "OK" if result.success else "FAIL"
        print(f"      Result: {status} (tier_used: {result.tier_used.value})")
        print()

    # Show cost summary
    summary = cost_tracker.get_session_summary()
    tier_summary = cost_tracker.get_tier_summary()

    print("\n" + "-" * 70)
    print("COST SUMMARY")
    print("-" * 70)
    print(f"Total Executions: {summary['total_executions']}")
    print(f"Tier Breakdown: {summary['tier_breakdown']}")
    print(f"Total Cost: ${summary['total_cost']:.6f}")
    print(f"If All Claude: ${summary['total_cost'] + summary['total_savings']:.6f}")
    print(f"Savings: ${summary['total_savings']:.6f} ({summary['savings_percentage']:.1f}%)")

    return cost_tracker, router._adaptive_router


@pytest.mark.asyncio
async def test_adaptive_learning_simulation():
    """Test adaptive learning by simulating failures."""
    print("\n" + "=" * 70)
    print("TEST 2: Adaptive Learning (Failure Simulation)")
    print("=" * 70)

    adaptive = AdaptiveRouter(data_dir="./data/test_comprehensive/adaptive_sim")

    skill_name = "flaky_api_skill"
    capabilities = ["tool_orchestration", "problem_analysis"]

    print(f"\nSimulating executions for: {skill_name}")
    print(f"Capabilities: {capabilities}")

    # Phase 1: Initial successes
    print("\nPhase 1: 3 successful local executions")
    for i in range(3):
        adaptive.record_execution(skill_name, capabilities, Tier.LOCAL, success=True, latency_ms=100)

    tier, reason = adaptive.get_tier_recommendation(skill_name, capabilities, Tier.LOCAL)
    print(f"  Recommendation: {tier.value} (reason: {reason or 'using default'})")

    # Phase 2: Failures start
    print("\nPhase 2: 4 failed local executions")
    for i in range(4):
        adaptive.record_execution(skill_name, capabilities, Tier.LOCAL, success=False, latency_ms=5000)

    tier, reason = adaptive.get_tier_recommendation(skill_name, capabilities, Tier.LOCAL)
    print(f"  Recommendation: {tier.value}")
    print(f"  Reason: {reason}")

    # Check stats
    stats = adaptive.get_pattern_stats(skill_name, capabilities)
    print(f"\nPattern Statistics:")
    print(f"  Local attempts: {stats['local']['attempts']}")
    print(f"  Local successes: {stats['local']['successes']}")
    print(f"  Local success rate: {stats['local']['success_rate']:.0%}")
    print(f"  Tier override: {stats['tier_override']}")

    # Phase 3: Recovery on HuggingFace
    print("\nPhase 3: 5 successful HuggingFace executions")
    for i in range(5):
        adaptive.record_execution(skill_name, capabilities, Tier.HUGGINGFACE, success=True, latency_ms=500)

    stats = adaptive.get_pattern_stats(skill_name, capabilities)
    print(f"  HF attempts: {stats['huggingface']['attempts']}")
    print(f"  HF success rate: {stats['huggingface']['success_rate']:.0%}")

    return adaptive


@pytest.mark.asyncio
async def test_cost_projections():
    """Test cost projection calculations."""
    print("\n" + "=" * 70)
    print("TEST 3: Cost Projections")
    print("=" * 70)

    tracker = CostTracker(data_dir="./data/test_comprehensive/projections")

    # Simulate a realistic day of mixed executions
    print("\nSimulating a typical day of skill executions...")

    # 70 local executions (file ops, testing, docs)
    for i in range(70):
        tracker.log_execution(
            skill_name=f"local_skill_{i}",
            tier_requested=Tier.LOCAL,
            tier_used=Tier.LOCAL,
            fallback_used=False,
            success=True,
            tokens_used=400 + (i % 200),
            latency_ms=150 + (i % 100),
        )

    # 20 HuggingFace executions (complex analysis)
    for i in range(20):
        tracker.log_execution(
            skill_name=f"hf_skill_{i}",
            tier_requested=Tier.LOCAL,
            tier_used=Tier.HUGGINGFACE,
            fallback_used=True,
            success=True,
            tokens_used=800 + (i % 400),
            latency_ms=800 + (i % 200),
        )

    # 10 Claude executions (security, architecture)
    for i in range(10):
        tracker.log_execution(
            skill_name=f"claude_skill_{i}",
            tier_requested=Tier.CLAUDE,
            tier_used=Tier.CLAUDE,
            fallback_used=False,
            success=True,
            tokens_used=1500 + (i % 500),
            latency_ms=2000 + (i % 500),
        )

    # Get projections
    projection = tracker.get_cost_projection(daily_executions=100)

    print(f"\nDaily Execution Mix (simulated):")
    summary = tracker.get_session_summary()
    print(f"  Local: {summary['tier_breakdown'].get('local', 0)} executions")
    print(f"  HuggingFace: {summary['tier_breakdown'].get('huggingface', 0)} executions")
    print(f"  Claude: {summary['tier_breakdown'].get('claude', 0)} executions")

    print(f"\nCost Analysis:")
    print(f"  Today's Cost: ${summary['total_cost']:.4f}")
    print(f"  Today's Savings: ${summary['total_savings']:.4f}")
    print(f"  Savings Rate: {summary['savings_percentage']:.1f}%")

    print(f"\nMonthly Projection (at 100 exec/day):")
    print(f"  Tier Distribution: {projection['assumptions']['tier_distribution']}")
    print(f"  Projected Cost: ${projection['projected_monthly_cost']:.2f}")
    print(f"  If All Claude: ${projection['projected_cost_if_all_claude']:.2f}")
    print(f"  Monthly Savings: ${projection['projected_monthly_savings']:.2f}")
    print(f"  Savings Rate: {projection['projected_savings_percentage']:.1f}%")

    return tracker


@pytest.mark.asyncio
async def test_real_ollama_execution():
    """Test real Ollama execution with different task types."""
    print("\n" + "=" * 70)
    print("TEST 4: Real Ollama Executions")
    print("=" * 70)

    client = OllamaClient()

    if not await client.is_available():
        print("\n[SKIP] Ollama not available")
        return None

    print(f"\nModel: {client.model}")
    print(f"Endpoint: {client.endpoint}")

    tasks = [
        {
            "name": "Code Analysis",
            "skill": "analyze_imports_skill",
            "description": "Analyze Python imports and suggest optimizations",
            "context": {"file": "main.py", "focus": "unused_imports"},
        },
        {
            "name": "Git Workflow",
            "skill": "prepare_commit_skill",
            "description": "Prepare a git commit with proper message",
            "context": {"changes": ["fixed bug", "added tests"], "type": "fix"},
        },
        {
            "name": "Test Generation",
            "skill": "generate_test_skill",
            "description": "Generate pytest test cases for a function",
            "context": {"function": "calculate_total", "params": ["items", "tax_rate"]},
        },
    ]

    print(f"\nExecuting {len(tasks)} real tasks...\n")

    for task in tasks:
        print(f"  Task: {task['name']}")
        start = time.time()

        result = await client.execute_skill(
            task["skill"],
            task["description"],
            task["context"],
        )

        elapsed = (time.time() - start) * 1000

        success = result.get("success", False)
        tokens = result.get("tokens", 0)

        print(f"    Success: {success}")
        print(f"    Tokens: {tokens}")
        print(f"    Latency: {elapsed:.0f}ms")

        if success and result.get("actions"):
            print(f"    Actions: {len(result['actions'])} planned")
            for action in result["actions"][:2]:  # Show first 2
                print(f"      - {action.get('tool', 'unknown')}")
        print()

    return client


@pytest.mark.asyncio
async def test_full_dashboard():
    """Test the full analytics dashboard."""
    print("\n" + "=" * 70)
    print("TEST 5: Full Analytics Dashboard")
    print("=" * 70)

    router = TierRouter()

    # Run a few executions first
    for i in range(5):
        routing = await router.route_skill(f"test_skill_{i}", ["file_operations"], 500)

        async def executor(tier: Tier):
            return {"success": True, "tokens": 400}

        await router.execute_with_fallback(
            routing, executor,
            skill_name=f"test_skill_{i}",
            capabilities=["file_operations"],
        )

    # Get full dashboard
    dashboard = await router.get_cost_dashboard()
    full_stats = await router.get_full_stats()

    print("\n--- Session Summary ---")
    session = dashboard["session_summary"]
    print(f"Duration: {session['session_duration_seconds']:.1f}s")
    print(f"Executions: {session['total_executions']}")
    print(f"Tiers: {session['tier_breakdown']}")
    print(f"Cost: ${session['total_cost']:.6f}")
    print(f"Savings: {session['savings_percentage']:.1f}%")

    print("\n--- Tier Statistics ---")
    for tier_name, stats in dashboard["tier_summary"]["tiers"].items():
        if stats["executions"] > 0:
            print(f"{tier_name}:")
            print(f"  Executions: {stats['executions']}")
            print(f"  Success Rate: {stats['success_rate']*100:.0f}%")
            print(f"  Avg Latency: {stats['avg_latency_ms']:.0f}ms")

    print("\n--- Adaptive Learning ---")
    adaptive = full_stats["adaptive_learning"]
    print(f"Active Overrides: {len(adaptive['active_overrides'])}")
    cap_summary = adaptive["capability_learning"].get("summary", {})
    if cap_summary:
        print("Capability Success Rates (local):")
        for cap, data in list(cap_summary.items())[:5]:
            print(f"  {cap}: {data['local_rate']:.0%}")

    print("\n--- Monthly Projection ---")
    proj = dashboard["projection"]
    if "projected_monthly_cost" in proj:
        print(f"Projected Cost: ${proj['projected_monthly_cost']:.2f}/month")
        print(f"Projected Savings: ${proj['projected_monthly_savings']:.2f}/month")

    return dashboard


async def main():
    """Run all comprehensive tests."""
    print("\n" + "=" * 70)
    print("COMPREHENSIVE PHASE 5 TEST SUITE")
    print("Cost Tracking & Adaptive Routing")
    print("=" * 70)

    results = {}

    # Test 1: Multiple executions
    try:
        await test_multiple_skill_executions()
        results["multiple_executions"] = True
        print("\n[PASS] Test 1: Multiple Skill Executions")
    except Exception as e:
        results["multiple_executions"] = False
        print(f"\n[FAIL] Test 1: {e}")

    # Test 2: Adaptive learning
    try:
        await test_adaptive_learning_simulation()
        results["adaptive_learning"] = True
        print("\n[PASS] Test 2: Adaptive Learning")
    except Exception as e:
        results["adaptive_learning"] = False
        print(f"\n[FAIL] Test 2: {e}")

    # Test 3: Cost projections
    try:
        await test_cost_projections()
        results["cost_projections"] = True
        print("\n[PASS] Test 3: Cost Projections")
    except Exception as e:
        results["cost_projections"] = False
        print(f"\n[FAIL] Test 3: {e}")

    # Test 4: Real Ollama
    try:
        result = await test_real_ollama_execution()
        results["real_ollama"] = result is not None
        status = "PASS" if result else "SKIP"
        print(f"\n[{status}] Test 4: Real Ollama Execution")
    except Exception as e:
        results["real_ollama"] = False
        print(f"\n[FAIL] Test 4: {e}")

    # Test 5: Dashboard
    try:
        await test_full_dashboard()
        results["dashboard"] = True
        print("\n[PASS] Test 5: Full Dashboard")
    except Exception as e:
        results["dashboard"] = False
        print(f"\n[FAIL] Test 5: {e}")

    # Final Summary
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        status = "PASS" if passed_test else "FAIL"
        print(f"  {test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
