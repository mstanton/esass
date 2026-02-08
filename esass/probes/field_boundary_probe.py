"""
Field Boundary Probe

Implements the "Protection Gradient" concept, observing agent interactions
with different project zones (Core, Trusted, Learning, Exploration).
"""

import os
from typing import Dict, List, Optional, Any

from esass.probes.base import FilteringProbe, ProbeContext, LogEntry


class FieldBoundaryProbe(FilteringProbe):
    """
    Monitors operations across project zones.

    Zones:
    - CORE: Critical configuration and documentation (High Risk)
    - TRUSTED: Validated code and tests (Medium Risk)
    - LEARNING: Active development areas (Medium Risk)
    - EXPLORATION: Sandbox and temporary files (Low Risk)
    """

    CORE_FILES = {
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        ".gitignore",
        ".dockerignore",
        "requirements.txt",
        "pyproject.toml",
        "setup.py",
        "Dockerfile",
        "docker-compose.yml",
    }

    CORE_DIRS = {".github", ".git", ".vscode", ".idea"}

    TRUSTED_DIRS = {"tests", "docs", "examples"}

    def can_observe(self, event_type: str) -> bool:
        return event_type in ["tool_call_start", "tool_call_complete"]

    def observe_filtered(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        tool_name = context.event_data.get("tool_name")
        if not tool_name:
            return None

        # Only interested in file operations for now
        if tool_name not in ["Read", "Write", "Edit", "Delete"]:
            return None

        file_path = context.event_data.get("parameters", {}).get("file_path")
        if not file_path:
            return None

        zone = self.get_zone_for_file(file_path)
        risk_level = self._assess_risk(zone, tool_name)

        # Log boundary crossing event
        entry = LogEntry.create(
            event_type="boundary_action",
            event_data={
                "file_path": file_path,
                "zone": zone,
                "tool": tool_name,
                "risk_level": risk_level,
                "action": "monitor",
            },
            session_id=context.session_id,
            tags=["boundary", zone.lower(), risk_level + "_risk"],
        )

        return [entry]

    def get_zone_for_file(self, file_path: str) -> str:
        """Determine the zone for a given file path"""
        # Normalize path
        file_path = file_path.replace("\\", "/")
        basename = os.path.basename(file_path)

        # Check explicit core files
        if basename in self.CORE_FILES:
            return "CORE"

        # Check directories
        parts = file_path.split("/")

        # Check if any part matches core dirs
        for part in parts:
            if part in self.CORE_DIRS:
                return "CORE"

        # Check trusted dirs (usually top-level)
        # We look at the first few parts relative to workspace root
        # Assuming relative path or absolute path containing workspace
        # For simplicity, check if any of top-level folders match
        for part in parts:
            if part in self.TRUSTED_DIRS:
                return "TRUSTED"

        # Default to EXPLORATION for now as per test expectation for 'temp/test.py'
        # In reality, 'src' might be LEARNING
        if "src" in parts or "lib" in parts or "app" in parts:
            return "LEARNING"

        return "EXPLORATION"

    def _assess_risk(self, zone: str, tool_name: str) -> str:
        """Calculate risk level based on zone and action"""
        if tool_name == "Read":
            return "low"

        if zone == "CORE":
            return "high"

        if zone == "TRUSTED":
            return "medium"

        if zone == "LEARNING":
            return "medium"

        return "low"
