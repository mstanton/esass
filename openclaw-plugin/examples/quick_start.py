"""
Quick Start: ESASS × OpenClaw × ClawHub Integration

Run this to see the recursive learning loop in action.
"""

import asyncio
from datetime import datetime
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import integration components
from loop.controller import RecursiveLoopController, LoopConfig
from bridge.openclaw_hooks import OpenClawESASSBridge, OpenClawEvent, OpenClawEventType


async def main():
    print("=" * 70)
    print("ESASS × OpenClaw × ClawHub - Recursive Learning Loop")
    print("=" * 70)
    print()

    # Configure the loop
    config = LoopConfig(
        observation_window_hours=1,  # Short window for demo
        cycle_interval_hours=1,
        min_events_for_detection=10,  # Lower threshold for demo
        min_support=3,
        min_confidence=0.7,
        auto_publish=False,  # Disable for demo
        require_human_approval=False
    )

    # Create controller
    controller = RecursiveLoopController(config=config)

    # Register callbacks
    controller.on_skill_generated(lambda skill: print(f"✓ Generated: {skill.name}"))
    controller.on_cycle_complete(lambda results: print(f"✓ Cycle complete: {results}"))

    print("[1] Simulating OpenClaw events...")
    print("-" * 70)

    # Simulate some OpenClaw events
    bridge = controller.bridge

    for session_num in range(5):
        session_id = f"demo-session-{session_num}"

        # Session start
        await bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.SESSION_START,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            channel="telegram"
        ))

        # Thinking
        await bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.THINKING_BLOCK,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            data={
                "content": "I'll check the git status first to see what files have changed",
                "type": "planning"
            }
        ))

        # Tool call
        await bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.TOOL_CALL_START,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            data={
                "call_id": f"call-{session_num}-1",
                "tool_name": "Bash",
                "parameters": {"command": "git status"}
            }
        ))

        await bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.TOOL_CALL_COMPLETE,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            data={
                "call_id": f"call-{session_num}-1",
                "success": True,
                "result": "On branch main\nChanges not staged..."
            }
        ))

        # Decision
        await bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.APPROACH_SELECTED,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            data={
                "approach": "stage_and_commit",
                "alternatives": ["commit_all", "stage_selective"],
                "rationale": "User has specific files to commit"
            }
        ))

        # Session end
        await bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.SESSION_END,
            timestamp=datetime.utcnow(),
            session_id=session_id
        ))

        print(f"  Session {session_num + 1}: ✓ Generated git workflow events")

    print()
    print("[2] Running learning cycle...")
    print("-" * 70)

    # Run one cycle
    results = await controller.run_cycle()

    print()
    print("[3] Results")
    print("-" * 70)
    print(f"  Events processed: {results['events_processed']}")
    print(f"  Patterns detected: {results['patterns_detected']}")
    print(f"  Skills generated: {results['skills_generated']}")

    print()
    print("[4] Loop Status")
    print("-" * 70)
    status = controller.get_status()
    for key, value in status["metrics"].items():
        print(f"  {key}: {value}")

    print()
    print("=" * 70)
    print("Demo complete! In production, the loop runs continuously.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
