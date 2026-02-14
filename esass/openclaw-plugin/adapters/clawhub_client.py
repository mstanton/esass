"""
ClawHub Publishing Client (rewritten).

Automates skill publication to ClawHub registry with versioning and metadata.
"""

from __future__ import annotations

import json
import os
import subprocess
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml


class PublishResult(Enum):
    SUCCESS = "success"
    ALREADY_EXISTS = "already_exists"
    VALIDATION_FAILED = "validation_failed"
    AUTH_FAILED = "auth_failed"
    NETWORK_ERROR = "network_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class PublishResponse:
    result: PublishResult
    skill_slug: str
    version: str
    url: Optional[str] = None
    message: Optional[str] = None


class ClawHubClient:
    """Client for interacting with ClawHub skill registry."""

    def __init__(
        self,
        registry_url: str = "https://clawhub.com",
        token: Optional[str] = None,
        auto_bump: str = "patch",
    ):
        self.registry_url = registry_url
        self.token = token or os.environ.get("CLAWHUB_TOKEN")
        self.auto_bump = auto_bump
        self._cli_available: Optional[bool] = None

    def _verify_cli(self) -> bool:
        if self._cli_available is not None:
            return self._cli_available
        try:
            subprocess.run(["clawhub", "--version"], capture_output=True, check=True)
            self._cli_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self._cli_available = False
        return self._cli_available

    def _run_clawhub(self, args: List[str], capture: bool = True) -> subprocess.CompletedProcess:
        cmd = ["clawhub"] + args
        if self.token:
            cmd.extend(["--token", self.token])
        return subprocess.run(cmd, capture_output=capture, text=True)

    def authenticate(self, token: Optional[str] = None) -> bool:
        if not self._verify_cli():
            return False
        token = token or self.token
        if not token:
            result = self._run_clawhub(["login"])
            return result.returncode == 0
        result = self._run_clawhub(["login", "--token", token])
        return result.returncode == 0

    def whoami(self) -> Optional[str]:
        if not self._verify_cli():
            return None
        result = self._run_clawhub(["whoami"])
        return result.stdout.strip() if result.returncode == 0 else None

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        if not self._verify_cli():
            return []
        result = self._run_clawhub(["search", query, "--limit", str(limit), "--json"])
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return self._parse_search_output(result.stdout)
        return []

    @staticmethod
    def _parse_search_output(output: str) -> List[Dict]:
        skills = []
        for line in output.strip().split("\n"):
            if line.strip():
                parts = line.split(" - ", 1)
                if len(parts) == 2:
                    skills.append({"slug": parts[0].strip(), "description": parts[1].strip()})
        return skills

    def skill_exists(self, slug: str) -> bool:
        results = self.search(slug, limit=1)
        return any(r.get("slug") == slug for r in results)

    def publish(
        self,
        skill_path: Path,
        slug: Optional[str] = None,
        name: Optional[str] = None,
        version: Optional[str] = None,
        changelog: str = "ESASS auto-generated skill",
        tags: Optional[List[str]] = None,
    ) -> PublishResponse:
        skill_path = Path(skill_path)
        slug = slug or skill_path.name

        if not (skill_path / "SKILL.md").exists():
            return PublishResponse(
                result=PublishResult.VALIDATION_FAILED,
                skill_slug=slug,
                version=version or "0.0.0",
                message="SKILL.md not found",
            )

        if not self._verify_cli():
            return PublishResponse(
                result=PublishResult.UNKNOWN_ERROR,
                skill_slug=slug,
                version=version or "0.0.0",
                message="clawhub CLI not available",
            )

        metadata = self._read_skill_metadata(skill_path / "SKILL.md")
        name = name or metadata.get("name", slug)
        version = version or metadata.get("version", "1.0.0")
        tags = tags or ["latest", "esass-generated"]

        args = [
            "publish", str(skill_path),
            "--slug", slug,
            "--name", name,
            "--version", version,
            "--changelog", changelog,
            "--tags", ",".join(tags),
        ]

        result = self._run_clawhub(args)
        if result.returncode == 0:
            return PublishResponse(
                result=PublishResult.SUCCESS,
                skill_slug=slug,
                version=version,
                url=f"{self.registry_url}/skills/{slug}",
                message="Successfully published",
            )

        error_msg = result.stderr or result.stdout
        if "already exists" in error_msg.lower():
            return PublishResponse(
                result=PublishResult.ALREADY_EXISTS, skill_slug=slug,
                version=version, message="Version already exists",
            )
        if "unauthorized" in error_msg.lower() or "auth" in error_msg.lower():
            return PublishResponse(
                result=PublishResult.AUTH_FAILED, skill_slug=slug,
                version=version, message="Authentication failed",
            )
        return PublishResponse(
            result=PublishResult.UNKNOWN_ERROR, skill_slug=slug,
            version=version, message=error_msg,
        )

    @staticmethod
    def _read_skill_metadata(skill_file: Path) -> Dict:
        content = skill_file.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    return yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError:
                    pass
        return {}

    def install(self, slug: str, version: Optional[str] = None) -> bool:
        if not self._verify_cli():
            return False
        args = ["install", slug]
        if version:
            args.extend(["--version", version])
        return self._run_clawhub(args).returncode == 0

    def update(self, slug: Optional[str] = None, all_skills: bool = False) -> bool:
        if not self._verify_cli():
            return False
        args = ["update", "--all"] if all_skills else ["update", slug or ""]
        return self._run_clawhub(args).returncode == 0

    def sync(
        self,
        skill_dirs: List[Path],
        dry_run: bool = False,
        bump: Optional[str] = None,
    ) -> List[PublishResponse]:
        responses = []
        bump = bump or self.auto_bump
        for skill_dir in skill_dirs:
            if not skill_dir.is_dir() or not (skill_dir / "SKILL.md").exists():
                continue
            if dry_run:
                continue
            slug = skill_dir.name
            metadata = self._read_skill_metadata(skill_dir / "SKILL.md")
            current_version = metadata.get("version", "1.0.0")
            if self.skill_exists(slug):
                new_version = self._bump_version(current_version, bump)
                response = self.publish(skill_dir, version=new_version, changelog=f"ESASS auto-update ({bump})")
            else:
                response = self.publish(skill_dir)
            responses.append(response)
        return responses

    @staticmethod
    def _bump_version(version: str, bump: str) -> str:
        parts = version.split(".")
        if len(parts) != 3:
            return "1.0.0"
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        if bump == "major":
            return f"{major + 1}.0.0"
        elif bump == "minor":
            return f"{major}.{minor + 1}.0"
        return f"{major}.{minor}.{patch + 1}"


class ESASSClawHubPublisher:
    """High-level publisher for ESASS-generated skills."""

    def __init__(
        self,
        formatter: "SkillFormatter",
        client: ClawHubClient,
        require_confidence: float = 0.85,
        require_support: int = 15,
    ):
        self.formatter = formatter
        self.client = client
        self.require_confidence = require_confidence
        self.require_support = require_support

    def publish_skill(
        self,
        manifest: "SkillManifest",
        pattern: Optional["PatternDefinition"] = None,
        auto_authenticate: bool = True,
    ) -> PublishResponse:
        if pattern:
            if pattern.confidence < self.require_confidence:
                return PublishResponse(
                    result=PublishResult.VALIDATION_FAILED,
                    skill_slug=manifest.name,
                    version=manifest.version,
                    message=f"Confidence {pattern.confidence} below threshold {self.require_confidence}",
                )
            if pattern.support < self.require_support:
                return PublishResponse(
                    result=PublishResult.VALIDATION_FAILED,
                    skill_slug=manifest.name,
                    version=manifest.version,
                    message=f"Support {pattern.support} below threshold {self.require_support}",
                )
        skill_path = self.formatter.save_skill(manifest, pattern)
        if auto_authenticate and not self.client.whoami():
            self.client.authenticate()
        return self.client.publish(skill_path.parent)

    def publish_batch(
        self,
        manifests: List["SkillManifest"],
        patterns: Optional[Dict[str, "PatternDefinition"]] = None,
    ) -> List[PublishResponse]:
        patterns = patterns or {}
        responses = []
        for manifest in manifests:
            pattern = None
            if manifest.source_pattern_ids:
                pattern = patterns.get(manifest.source_pattern_ids[0])
            responses.append(self.publish_skill(manifest, pattern))
        return responses
