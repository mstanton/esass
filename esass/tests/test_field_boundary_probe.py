import pytest
from datetime import datetime
from esass.probes.field_boundary_probe import FieldBoundaryProbe
from esass.probes.base import ProbeContext


class TestFieldBoundaryProbe:
    def test_classifies_core_files(self):
        """Verify core project files are identified"""
        probe = FieldBoundaryProbe()

        # Test core files
        assert probe.get_zone_for_file("README.md") == "CORE"
        assert probe.get_zone_for_file("c:/workspace/project/README.md") == "CORE"
        assert probe.get_zone_for_file("requirements.txt") == "CORE"
        assert probe.get_zone_for_file(".gitignore") == "CORE"

    def test_classifies_exploration_files(self):
        """Verify non-standard/new files are exploration"""
        probe = FieldBoundaryProbe()

        assert probe.get_zone_for_file("temp/test.py") == "EXPLORATION"
        assert probe.get_zone_for_file("sandbox/experiment.md") == "EXPLORATION"

    def test_logs_boundary_crossing(self):
        """Verify modifying core file logs an event"""
        probe = FieldBoundaryProbe()

        context = ProbeContext(
            event_type="tool_call_start",
            event_data={"tool_name": "Write", "parameters": {"file_path": "README.md"}},
            session_id="test",
            timestamp=datetime.utcnow(),
            call_stack=[],
            metadata={},
        )

        entries = probe.observe(context)
        assert len(entries) == 1
        assert entries[0].event_type == "boundary_action"
        assert entries[0].event_data["zone"] == "CORE"
        assert entries[0].event_data["action"] == "monitor"  # or 'warning'

    def test_allows_read_on_core(self):
        """Reading core files should be less severe or handled differently"""
        # For this version, maybe we just log it as an action in CORE zone,
        # but with a different 'risk_level'
        probe = FieldBoundaryProbe()

        context = ProbeContext(
            event_type="tool_call_start",
            event_data={"tool_name": "Read", "parameters": {"file_path": "README.md"}},
            session_id="test",
            timestamp=datetime.utcnow(),
            call_stack=[],
            metadata={},
        )

        entries = probe.observe(context)
        assert len(entries) == 1
        assert entries[0].event_data["risk_level"] == "low"

    def test_high_risk_on_write_core(self):
        """Writing core files should be high risk"""
        probe = FieldBoundaryProbe()

        context = ProbeContext(
            event_type="tool_call_start",
            event_data={"tool_name": "Write", "parameters": {"file_path": "README.md"}},
            session_id="test",
            timestamp=datetime.utcnow(),
            call_stack=[],
            metadata={},
        )

        entries = probe.observe(context)
        assert entries[0].event_data["risk_level"] == "high"
