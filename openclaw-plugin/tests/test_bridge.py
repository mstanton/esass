"""
Tests for the bridge module (~10 tests).
"""

from datetime import datetime

import pytest

from openclaw_plugin.bridge.events import OpenClawEvent, OpenClawEventType
from openclaw_plugin.bridge.event_router import EventRouter
from openclaw_plugin.bridge.hooks import OpenClawESASSBridge


class TestOpenClawEventType:
    def test_all_expected_types_exist(self):
        expected = [
            "session_start", "session_end", "thinking_block",
            "tool_call_start", "tool_call_complete", "tool_call_error",
            "skill_activated", "skill_completed", "funding_notice",
        ]
        for val in expected:
            assert OpenClawEventType(val) is not None

    def test_funding_notice_type(self):
        assert OpenClawEventType.FUNDING_NOTICE.value == "funding_notice"


class TestEventRouter:
    def test_register_and_dispatch(self):
        router = EventRouter()
        calls = []
        router.register(OpenClawEventType.SESSION_START, lambda e: calls.append(e))
        event = OpenClawEvent(
            event_type=OpenClawEventType.SESSION_START,
            timestamp=datetime.utcnow(),
            session_id="test",
        )
        router.dispatch(event)
        assert len(calls) == 1

    def test_dispatch_unregistered_type(self):
        router = EventRouter()
        event = OpenClawEvent(
            event_type=OpenClawEventType.SESSION_END,
            timestamp=datetime.utcnow(),
            session_id="test",
        )
        # Should not raise
        router.dispatch(event)

    def test_handler_error_isolation(self):
        router = EventRouter()
        good_calls = []

        def bad_handler(e):
            raise RuntimeError("boom")

        def good_handler(e):
            good_calls.append(e)

        router.register(OpenClawEventType.SESSION_START, bad_handler)
        router.register(OpenClawEventType.SESSION_START, good_handler)

        event = OpenClawEvent(
            event_type=OpenClawEventType.SESSION_START,
            timestamp=datetime.utcnow(),
            session_id="test",
        )
        router.dispatch(event)
        # Good handler still called despite bad handler error
        assert len(good_calls) == 1

    def test_registered_types(self):
        router = EventRouter()
        router.register(OpenClawEventType.THINKING_BLOCK, lambda e: None)
        assert OpenClawEventType.THINKING_BLOCK in router.registered_types

    def test_unregister(self):
        router = EventRouter()
        handler = lambda e: None
        router.register(OpenClawEventType.SESSION_START, handler)
        router.unregister(OpenClawEventType.SESSION_START, handler)
        assert OpenClawEventType.SESSION_START not in router.registered_types


class TestOpenClawESASSBridge:
    def test_session_tracking(self):
        bridge = OpenClawESASSBridge()
        start = OpenClawEvent(
            event_type=OpenClawEventType.SESSION_START,
            timestamp=datetime.utcnow(),
            session_id="sess1",
            channel="test",
        )
        bridge.on_event(start)
        assert "sess1" in bridge._sessions

        end = OpenClawEvent(
            event_type=OpenClawEventType.SESSION_END,
            timestamp=datetime.utcnow(),
            session_id="sess1",
        )
        bridge.on_event(end)
        assert "sess1" not in bridge._sessions

    def test_skill_activation_tracking(self):
        bridge = OpenClawESASSBridge()
        event = OpenClawEvent(
            event_type=OpenClawEventType.SKILL_ACTIVATED,
            timestamp=datetime.utcnow(),
            session_id="sess1",
            data={"skill_name": "test-skill", "skill_id": "s1"},
        )
        bridge.on_event(event)
        assert "test-skill" in bridge._skill_activations

    def test_skill_feedback(self):
        bridge = OpenClawESASSBridge()
        # No activations
        fb = bridge.get_skill_feedback("nonexistent")
        assert fb["activations"] == 0

        # With activation and completion
        bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.SKILL_ACTIVATED,
            timestamp=datetime.utcnow(),
            session_id="sess1",
            data={"skill_name": "my-skill"},
        ))
        bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.SKILL_COMPLETED,
            timestamp=datetime.utcnow(),
            session_id="sess1",
            data={"skill_name": "my-skill", "success": True},
        ))
        fb = bridge.get_skill_feedback("my-skill")
        assert fb["activations"] == 1
        assert fb["success_rate"] == 1.0

    def test_donation_notice_emission(self):
        from openclaw_plugin.donation.models import DonationConfig
        cfg = DonationConfig(enabled=True, show_on_activation=True)
        bridge = OpenClawESASSBridge(donation_config=cfg)

        funding_events = []
        bridge.router.register(
            OpenClawEventType.FUNDING_NOTICE,
            lambda e: funding_events.append(e),
        )

        bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.SKILL_ACTIVATED,
            timestamp=datetime.utcnow(),
            session_id="sess1",
            data={"skill_name": "my-skill"},
        ))
        assert len(funding_events) == 1
        assert funding_events[0].data["donation_enabled"] is True

    def test_usage_tracking_integration(self, tmp_data_dir):
        from openclaw_plugin.tracing.stores import UsageStore
        from openclaw_plugin.tracing.usage_tracker import UsageAnalyticsTracker
        store = UsageStore(base_dir=tmp_data_dir["usage"])
        tracker = UsageAnalyticsTracker(store=store)
        bridge = OpenClawESASSBridge(usage_tracker=tracker)

        bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.SKILL_ACTIVATED,
            timestamp=datetime.utcnow(),
            session_id="sess1",
            data={"skill_name": "tracked-skill", "skill_id": "s1"},
            user_id="u1",
        ))
        records = store.read_all()
        assert len(records) == 1
        assert records[0].skill_name == "tracked-skill"
