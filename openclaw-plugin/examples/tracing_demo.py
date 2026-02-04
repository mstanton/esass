#!/usr/bin/env python3
"""
Tracing demo.

Creates usage/evolution/lineage records and runs queries.
"""

import sys
import tempfile
from pathlib import Path

_root = str(Path(__file__).resolve().parents[2])
if _root not in sys.path:
    sys.path.insert(0, _root)
_plugin = str(Path(__file__).resolve().parents[1])
if _plugin not in sys.path:
    sys.path.insert(0, _plugin)

import importlib, os
if "openclaw_plugin" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "openclaw_plugin",
        os.path.join(_plugin, "__init__.py"),
        submodule_search_locations=[_plugin],
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["openclaw_plugin"] = mod
    spec.loader.exec_module(mod)

from openclaw_plugin.tracing.stores import UsageStore, EvolutionStore, LineageStore
from openclaw_plugin.tracing.usage_tracker import UsageAnalyticsTracker
from openclaw_plugin.tracing.evolution_tracker import EvolutionHistoryTracker
from openclaw_plugin.tracing.lineage_tracker import LineageTracker
from openclaw_plugin.tracing.query import TracingQueryAPI


def main():
    print("=" * 60)
    print("ESASS Tracing Demo")
    print("=" * 60)

    # Use a real directory so files persist for inspection
    base = os.path.join(".", "data", "esass", "tracing")
    print(f"\n[Tracing] Data dir: {os.path.abspath(base)}")

    usage_store = UsageStore(base_dir=os.path.join(base, "usage"))
    evo_store = EvolutionStore(base_dir=os.path.join(base, "evolution"))
    lineage_store = LineageStore(base_dir=os.path.join(base, "lineage"))

    usage = UsageAnalyticsTracker(store=usage_store)
    evo = EvolutionHistoryTracker(store=evo_store)
    lin = LineageTracker(store=lineage_store)
    api = TracingQueryAPI(
        usage_store=usage_store,
        evolution_store=evo_store,
        lineage_store=lineage_store,
    )

    # --- Usage ---
    print("\n--- Recording usage ---")
    usage.record_activation(skill_id="s1", skill_name="git-commit-helper", session_id="sess1", user_id="u1")
    usage.record_completion(skill_id="s1", skill_name="git-commit-helper", session_id="sess1", success=True, duration_ms=120)
    usage.record_activation(skill_id="s1", skill_name="git-commit-helper", session_id="sess2", user_id="u2")
    usage.record_completion(skill_id="s1", skill_name="git-commit-helper", session_id="sess2", success=False, error_type="timeout")
    print("  4 records written")

    # --- Evolution ---
    print("\n--- Recording evolution ---")
    evo.record_creation(skill_id="s1", version="0.1.0", rationale="Pattern detected")
    evo.record_version_bump(skill_id="s1", from_version="0.1.0", to_version="0.2.0",
                            changes={"description": "improved"}, rationale="user feedback")
    print("  2 events written")

    # --- Lineage ---
    print("\n--- Recording lineage ---")
    lin.record_parent_child("parent-skill", "s1", evidence="genesis")
    lin.record_influence("influencer-skill", "s1", evidence="shared patterns")
    print("  2 edges written")

    # --- Queries ---
    print("\n--- Queries ---")
    report = api.skill_report("s1")
    print(f"  Skill report for s1:")
    print(f"    Activations: {report['usage']['activation_count']}")
    print(f"    Successes: {report['usage']['success_count']}")
    print(f"    Failures: {report['usage']['failure_count']}")
    print(f"    Evolution events: {len(report['evolution_events'])}")
    print(f"    Parents: {report['lineage']['parents']}")
    print(f"    Influenced by: {report['lineage']['influenced_by']}")

    top = api.top_skills(limit=5)
    print(f"\n  Top skills: {[s['skill_id'] for s in top]}")

    print("\n" + "=" * 60)
    print("Tracing demo complete!")
    print(f"Files created in: {os.path.abspath(base)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
