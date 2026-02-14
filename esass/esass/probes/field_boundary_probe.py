"""
Field Boundary Probe

Implements the "Protection Gradient" concept, observing agent interactions
with different project zones (Core, Trusted, Learning, Exploration).

Supports configuration via .esass.json in project root (ENHANCEMENT.md 1.2).
"""

import fnmatch
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

from esass.probes.base import FilteringProbe, ProbeContext, LogEntry


class ZoneConfig:
    """
    Configurable zone definitions loaded from .esass.json.

    Example .esass.json:
    {
        "zones": {
            "CORE": ["pyproject.toml", ".env", "config/", "*.secret"],
            "TRUSTED": ["src/", "tests/", "lib/"],
            "LEARNING": ["drafts/", "experiments/"],
            "EXPLORATION": ["temp/", "scratch/"]
        }
    }
    """

    DEFAULT_CORE_FILES = {
        "README.md", "LICENSE", "CONTRIBUTING.md", ".gitignore",
        ".dockerignore", "requirements.txt", "pyproject.toml",
        "setup.py", "Dockerfile", "docker-compose.yml", ".env",
        "credentials.json", "secrets.yaml",
    }

    DEFAULT_CORE_DIRS = {".github", ".git", ".vscode", ".idea", "config"}

    DEFAULT_TRUSTED_DIRS = {"tests", "docs", "examples", "src", "lib"}

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.core_patterns: List[str] = []
        self.trusted_patterns: List[str] = []
        self.learning_patterns: List[str] = []
        self.exploration_patterns: List[str] = []

        # Load configuration
        self._load_config()

    def _load_config(self) -> None:
        """Load zone configuration from .esass.json or use defaults."""
        config_file = self.project_root / ".esass.json"

        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)

                zones = config.get("zones", {})
                self.core_patterns = zones.get("CORE", [])
                self.trusted_patterns = zones.get("TRUSTED", [])
                self.learning_patterns = zones.get("LEARNING", [])
                self.exploration_patterns = zones.get("EXPLORATION", [])
                return
            except Exception:
                pass  # Fall back to defaults

        # Use defaults if no config or load failed
        self.core_patterns = (
            list(self.DEFAULT_CORE_FILES) +
            [f"{d}/*" for d in self.DEFAULT_CORE_DIRS]
        )
        self.trusted_patterns = [f"{d}/*" for d in self.DEFAULT_TRUSTED_DIRS]

    def match_zone(self, file_path: str) -> str:
        """
        Determine which zone a file path belongs to.

        Args:
            file_path: Relative or absolute file path

        Returns:
            Zone name: CORE, TRUSTED, LEARNING, or EXPLORATION
        """
        # Normalize path
        file_path = file_path.replace("\\", "/")
        basename = os.path.basename(file_path)
        has_directory = "/" in file_path

        # For files in directories, check directory-based patterns first
        if has_directory:
            # Check trusted directories first (e.g., docs/, tests/, src/)
            if self._matches_directory_patterns(file_path, self.trusted_patterns):
                return "TRUSTED"

            if self._matches_directory_patterns(file_path, self.learning_patterns):
                return "LEARNING"

            if self._matches_directory_patterns(file_path, self.exploration_patterns):
                return "EXPLORATION"

        # Check core patterns (for root-level files and core directories)
        if self._matches_patterns(file_path, basename, self.core_patterns):
            return "CORE"

        # Check remaining patterns for root-level files
        if self._matches_patterns(file_path, basename, self.trusted_patterns):
            return "TRUSTED"

        if self._matches_patterns(file_path, basename, self.learning_patterns):
            return "LEARNING"

        # Default fallback
        return "EXPLORATION"

    def _matches_directory_patterns(self, file_path: str, patterns: List[str]) -> bool:
        """Check if file is inside a directory matching any pattern."""
        for pattern in patterns:
            pattern = pattern.replace("\\", "/")

            # Directory pattern (ends with / or /*)
            if pattern.endswith("/") or pattern.endswith("/*"):
                dir_name = pattern.rstrip("/*")
                # Check if file is inside this directory
                if f"/{dir_name}/" in f"/{file_path}" or file_path.startswith(f"{dir_name}/"):
                    return True

        return False

    def _matches_patterns(self, file_path: str, basename: str,
                         patterns: List[str]) -> bool:
        """Check if file matches any pattern in the list."""
        for pattern in patterns:
            pattern = pattern.replace("\\", "/")

            # Directory pattern (ends with /)
            if pattern.endswith("/"):
                dir_name = pattern.rstrip("/")
                if f"/{dir_name}/" in f"/{file_path}" or file_path.startswith(f"{dir_name}/"):
                    return True
                continue

            # Directory wildcard pattern (e.g., config/*)
            if pattern.endswith("/*"):
                dir_name = pattern[:-2]
                if f"/{dir_name}/" in f"/{file_path}" or file_path.startswith(f"{dir_name}/"):
                    return True
                continue

            # Glob pattern
            if "*" in pattern or "?" in pattern:
                if fnmatch.fnmatch(basename, pattern):
                    return True
                if fnmatch.fnmatch(file_path, pattern):
                    return True
                continue

            # Exact file match
            if basename == pattern or file_path.endswith(f"/{pattern}"):
                return True

        return False


class FieldBoundaryProbe(FilteringProbe):
    """
    Monitors operations across project zones.

    Zones:
    - CORE: Critical configuration and documentation (High Risk)
    - TRUSTED: Validated code and tests (Medium Risk)
    - LEARNING: Active development areas (Medium Risk)
    - EXPLORATION: Sandbox and temporary files (Low Risk)

    Zone configuration can be customized via .esass.json in project root.
    """

    # Legacy class attributes for backward compatibility
    CORE_FILES = ZoneConfig.DEFAULT_CORE_FILES
    CORE_DIRS = ZoneConfig.DEFAULT_CORE_DIRS
    TRUSTED_DIRS = ZoneConfig.DEFAULT_TRUSTED_DIRS

    def __init__(self, project_root: Optional[Path] = None, **kwargs):
        super().__init__(**kwargs)
        self.zone_config = ZoneConfig(project_root)

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
        """
        Determine the zone for a given file path.

        Uses ZoneConfig for pattern matching, with fallback to legacy behavior.
        """
        return self.zone_config.match_zone(file_path)

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
