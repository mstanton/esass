#!/usr/bin/env python3
"""Test real skill execution through the local LLM system."""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import Tier, get_config
from tier_router import TierRouter, get_router
from ollama_client import get_ollama_client
from cost_tracker import get_cost_tracker
from adaptive_router import get_adaptive_router


async def test_real_skill_execution():
    """Test real skill execution with cost tracking."""
    print("=" * 60)
    print("Real Skill Execution Test")
    print("=" * 60)

    router = await get_router()
    cost_tracker = get_cost_tracker()
    adaptive_router = get_adaptive_router()

    # Define test skills to execute
    test_skills = [
        {
            "name": "python_file_reader_skill",
            "description": "Read a Python file and extract function definitions",
            "capabilities": ["file_operations", "tool_orchestration"],
            "context": {"file_path": "example.py", "action": "extract_functions"},
        },
        {
            "name": "git_status_skill",
            "description": "Check git repository status and report changes",
            "capabilities": ["git_operations", "tool_orchestration"],
            "context": {"repo_path": ".", "action": "status"},
        },
        {
            "name": "test_runner_skill",
            "description": "Run pytest tests and summarize results",
            "capabilities": ["testing", "tool_orchestration"],
            "context": {"test_path": "tests/", "verbosity": "normal"},
        },
    ]

    print("\n--- Executing Skills ---\n")

    for i, skill in enumerate(test_skills, 1):
        print(f"\n[{i}] Executing: {skill['name']}")
        print(f"    Capabilities: {', '.join(skill['capabilities'])}")

        # Get routing decision
        routing = await router.route_skill(
            skill["name"],
            skill["capabilities"],
            estimated_tokens=500,
        )

        print(f"    Routed to: {routing.tier.value}")
        print(f"    Reason: {routing.reason.value} - {routing.details}")

        # Define executor
        async def executor(tier: Tier):
            if tier == Tier.LOCAL:
                client = await get_ollama_client()
                return await client.execute_skill(
                    skill["name"],
                    skill["description"],
                    skill["context"],
                )
            elif tier == Tier.HUGGINGFACE:
                # Would use HF client here
                return {"success": False, "error": "HF not configured for test"}
            else:
                return {"passthrough": True, "tier": "claude"}

        # Execute with fallback and tracking
        result = await router.execute_with_fallback(
            routing,
            executor,
            skill_name=skill["name"],
            capabilities=skill["capabilities"],
        )

        print(f"    Result: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"    Tier Used: {result.tier_used.value}")
        print(f"    Fallback: {'Yes' if result.fallback_used else 'No'}")

        if result.content and not result.content.get("passthrough"):
            content_preview = str(result.content.get("response", ""))[:100]
            if content_preview:
                print(f"    Response: {content_preview}...")

    # Show cost summary
    print("\n" + "=" * 60)
    print("Cost Summary")
    print("=" * 60)

    session = cost_tracker.get_session_summary()
    print(f"\nSession Statistics:")
    print(f"  Total Executions: {session['total_executions']}")
    print(f"  Tier Breakdown: {session['tier_breakdown']}")
    print(f"  Total Cost: ${session['total_cost']:.6f}")
    print(f"  Total Savings: ${session['total_savings']:.6f}")
    print(f"  Savings: {session['savings_percentage']:.1f}%")

    # Show adaptive learning
    print("\n" + "=" * 60)
    print("Adaptive Learning Status")
    print("=" * 60)

    overrides = adaptive_router.get_all_overrides()
    if overrides:
        print(f"\nActive Tier Overrides: {len(overrides)}")
        for o in overrides:
            print(f"  {o['skill_name']}: -> {o['tier_override']}")
    else:
        print("\nNo tier overrides active (all patterns performing well)")

    cap_learning = adaptive_router.get_capability_learning()
    print(f"\nCapability Success Rates (local tier):")
    for cap, summary in cap_learning.get('summary', {}).items():
        print(f"  {cap}: {summary['local_rate']:.0%}")

    # Full stats
    print("\n" + "=" * 60)
    print("Full Analytics")
    print("=" * 60)

    full_stats = await router.get_full_stats()
    print(f"\nCost Projection (100 exec/day):")
    proj = full_stats['costs']['projection']
    if 'projected_monthly_cost' in proj:
        print(f"  Monthly Cost: ${proj['projected_monthly_cost']:.2f}")
        print(f"  If All Claude: ${proj['projected_cost_if_all_claude']:.2f}")
        print(f"  Monthly Savings: ${proj['projected_monthly_savings']:.2f}")

    return True


async def test_skill_name_generation():
    """Test semantic skill name generation."""
    print("\n" + "=" * 60)
    print("Skill Name Generation Test")
    print("=" * 60)

    client = await get_ollama_client()

    test_patterns = [
        ("Read(python) -> Grep(function) -> Edit(refactor)", ["python", "refactor"]),
        ("Glob(test) -> Read -> Bash(pytest)", ["testing", "python"]),
        ("Read(config) -> Edit -> Bash(restart)", ["configuration", "deployment"]),
    ]

    print("\nGenerating semantic names for patterns:\n")

    for pattern, tags in test_patterns:
        print(f"Pattern: {pattern}")
        print(f"Tags: {tags}")

        name = await client.generate_skill_name(pattern, tags)
        print(f"Generated Name: {name}")
        print()

    return True


async def test_pattern_analysis():
    """Test pattern analysis with local LLM."""
    print("\n" + "=" * 60)
    print("Pattern Analysis Test")
    print("=" * 60)

    client = await get_ollama_client()

    test_pattern = "Read(python) -> Grep(class) -> Edit(add_method) -> Bash(pytest)"

    print(f"\nAnalyzing pattern: {test_pattern}")
    print(f"Support: 15, Confidence: 0.85\n")

    analysis = await client.analyze_pattern(test_pattern, support=15, confidence=0.85)

    print("Analysis Result:")
    print(json.dumps(analysis, indent=2))

    return True


async def main():
    """Run all real execution tests."""
    print("\n" + "=" * 60)
    print("LOCAL LLM REAL EXECUTION TESTS")
    print("=" * 60)

    # Check Ollama is available
    client = await get_ollama_client()
    available = await client.is_available()

    if not available:
        print("\n[ERROR] Ollama not available. Please start Ollama first:")
        print("  ollama serve")
        return 1

    print(f"\nOllama Status: AVAILABLE")
    print(f"Model: {client.model}")
    print(f"Endpoint: {client.endpoint}")

    results = {}

    # Test skill execution
    try:
        results['skill_execution'] = await test_real_skill_execution()
        print("\n[OK] Skill execution test passed")
    except Exception as e:
        results['skill_execution'] = False
        print(f"\n[FAIL] Skill execution test failed: {e}")
        import traceback
        traceback.print_exc()

    # Test skill name generation
    try:
        results['name_generation'] = await test_skill_name_generation()
        print("\n[OK] Name generation test passed")
    except Exception as e:
        results['name_generation'] = False
        print(f"\n[FAIL] Name generation test failed: {e}")

    # Test pattern analysis
    try:
        results['pattern_analysis'] = await test_pattern_analysis()
        print("\n[OK] Pattern analysis test passed")
    except Exception as e:
        results['pattern_analysis'] = False
        print(f"\n[FAIL] Pattern analysis test failed: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    all_passed = all(results.values())
    for name, passed in results.items():
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
