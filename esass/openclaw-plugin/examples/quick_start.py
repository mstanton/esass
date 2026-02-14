#!/usr/bin/env python3
"""
Quick-start demo for the ESASS OpenClaw plugin.

Shows basic bridge usage, skill formatting, and tracing.
"""

import sys
from pathlib import Path

# Ensure project root is importable
_root = str(Path(__file__).resolve().parents[2])
if _root not in sys.path:
    sys.path.insert(0, _root)

_plugin = str(Path(__file__).resolve().parents[1])
if _plugin not in sys.path:
    sys.path.insert(0, _plugin)

# Bootstrap the openclaw_plugin package
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

from datetime import datetime

from openclaw_plugin.config.settings import IntegrationConfig
from openclaw_plugin.bridge.events import OpenClawEvent, OpenClawEventType
from openclaw_plugin.bridge.hooks import OpenClawESASSBridge
from openclaw_plugin.donation.models import DonationConfig
from openclaw_plugin.donation.display import DonationDisplay
from openclaw_plugin.tracing.stores import UsageStore, EvolutionStore, LineageStore
from openclaw_plugin.tracing.usage_tracker import UsageAnalyticsTracker
from openclaw_plugin.tracing.evolution_tracker import EvolutionHistoryTracker
from openclaw_plugin.tracing.lineage_tracker import LineageTracker
from openclaw_plugin.tracing.query import TracingQueryAPI


def main():
    print("=" * 60)
    print("ESASS OpenClaw Plugin - Quick Start Demo")
    print("=" * 60)

    # 1. Configuration
    config = IntegrationConfig()
    print(f"\n[Config] Donation enabled: {config.donation.enabled}")
    print(f"[Config] Tracing enabled: {config.tracing.enabled}")

    # 2. Tracing setup (temp dir)
    import tempfile
    tmp = tempfile.mkdtemp(prefix="esass_demo_")
    usage_store = UsageStore(base_dir=f"{tmp}/usage")
    evo_store = EvolutionStore(base_dir=f"{tmp}/evolution")
    lineage_store = LineageStore(base_dir=f"{tmp}/lineage")
    usage_tracker = UsageAnalyticsTracker(store=usage_store)
    evo_tracker = EvolutionHistoryTracker(store=evo_store)
    lin_tracker = LineageTracker(store=lineage_store)

    # 3. Bridge with tracing
    bridge = OpenClawESASSBridge(
        donation_config=DonationConfig(),
        usage_tracker=usage_tracker,
    )

    # 4. Simulate events
    print("\n--- Simulating events ---")
    bridge.on_event(OpenClawEvent(
        event_type=OpenClawEventType.SESSION_START,
        timestamp=datetime.utcnow(),
        session_id="demo-sess",
        channel="cli",
    ))

    bridge.on_event(OpenClawEvent(
        event_type=OpenClawEventType.SKILL_ACTIVATED,
        timestamp=datetime.utcnow(),
        session_id="demo-sess",
        data={"skill_name": "git-commit-helper", "skill_id": "s1"},
        user_id="demo-user",
    ))

    bridge.on_event(OpenClawEvent(
        event_type=OpenClawEventType.SKILL_COMPLETED,
        timestamp=datetime.utcnow(),
        session_id="demo-sess",
        data={"skill_name": "git-commit-helper", "skill_id": "s1", "success": True, "duration_ms": 42},
        user_id="demo-user",
    ))

    bridge.on_event(OpenClawEvent(
        event_type=OpenClawEventType.SESSION_END,
        timestamp=datetime.utcnow(),
        session_id="demo-sess",
    ))

    # 5. Record evolution
    evo_tracker.record_creation(skill_id="s1", version="0.1.0", rationale="demo genesis")

    # 6. Query
    api = TracingQueryAPI(
        usage_store=usage_store,
        evolution_store=evo_store,
        lineage_store=lineage_store,
    )
    report = api.skill_report("s1")
    print(f"\n[Query] Skill report for s1:")
    print(f"  Activations: {report['usage']['activation_count']}")
    print(f"  Successes:   {report['usage']['success_count']}")
    print(f"  Evolution events: {len(report['evolution_events'])}")

    # 7. Donation display
    display = DonationDisplay()
    print(f"\n[Donation] {display.render_activation_message('git-commit-helper')}")

    print("\n" + "=" * 60)
    print("Quick start complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
