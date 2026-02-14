import pytest
from datetime import datetime, timedelta
from esass.probes.reliability_probe import ReliabilityProbe
from esass.probes.base import ProbeContext, LogEntry


class TestReliabilityProbe:
    def test_tracks_success_rate(self):
        """Verify rolling success rate calculation"""
        probe = ReliabilityProbe(window_size=10)

        # Simulate 8 successes and 2 failures
        context = ProbeContext(
            event_type="tool_call_complete",
            event_data={"tool_name": "Read", "success": True},
            session_id="test",
            timestamp=datetime.utcnow(),
            call_stack=[],
            metadata={},
        )
        for _ in range(8):
            probe.observe(context)

        fail_context = ProbeContext(
            event_type="tool_call_complete",
            event_data={
                "tool_name": "Read",
                "success": False,
                "error": "File not found",
            },
            session_id="test",
            timestamp=datetime.utcnow(),
            call_stack=[],
            metadata={},
        )
        for _ in range(2):
            probe.observe(fail_context)

        stats = probe.get_tool_stats("Read")
        assert stats["total_calls"] == 10
        assert stats["success_rate"] == 0.8
        assert stats["failure_count"] == 2

    def test_detects_consecutive_failures(self):
        """Verify alert on consecutive failures"""
        probe = ReliabilityProbe(alert_threshold=3)

        context = ProbeContext(
            event_type="tool_call_complete",
            event_data={"tool_name": "Read", "success": False, "error": "Error"},
            session_id="test",
            timestamp=datetime.utcnow(),
            call_stack=[],
            metadata={},
        )

        # 2 failures - no alert
        entries = probe.observe(context)
        assert not entries
        probe.observe(context)

        # 3rd failure - should alert
        entries = probe.observe(context)
        assert len(entries) == 1
        assert entries[0].event_type == "reliability_alert"
        assert entries[0].event_data["alert_type"] == "consecutive_failures"

    def test_resets_streak_on_success(self):
        """Verify success resets the failure streak"""
        probe = ReliabilityProbe(alert_threshold=3)

        fail_context = ProbeContext(
            event_type="tool_call_complete",
            event_data={"tool_name": "Read", "success": False, "error": "Error"},
            session_id="test",
            timestamp=datetime.utcnow(),
            call_stack=[],
            metadata={},
        )

        # 2 failures
        probe.observe(fail_context)
        probe.observe(fail_context)

        # 1 success
        success_context = ProbeContext(
            event_type="tool_call_complete",
            event_data={"tool_name": "Read", "success": True},
            session_id="test",
            timestamp=datetime.utcnow(),
            call_stack=[],
            metadata={},
        )
        probe.observe(success_context)

        # 1 more failure (total 3 failures but interrupted)
        entries = probe.observe(fail_context)
        assert not entries  # Should NOT alert because streak was broken

    def test_tracks_error_distribution(self):
        """Verify error types are categorized"""
        probe = ReliabilityProbe()

        errors = ["FileNotFoundError", "PermissionError", "FileNotFoundError"]

        for err in errors:
            context = ProbeContext(
                event_type="tool_call_complete",
                event_data={"tool_name": "Read", "success": False, "error": err},
                session_id="test",
                timestamp=datetime.utcnow(),
                call_stack=[],
                metadata={},
            )
            probe.observe(context)

        stats = probe.get_tool_stats("Read")
        # Check that FileNotFoundError appears twice
        assert stats["errors"]["FileNotFoundError"] == 2
        assert stats["errors"]["PermissionError"] == 1
