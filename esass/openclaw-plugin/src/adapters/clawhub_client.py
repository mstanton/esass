"""
ClawHub Publishing Client

Automates skill publication to ClawHub registry with versioning and metadata.
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum


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
    """
    Client for interacting with ClawHub skill registry.

    Supports publish, search, and sync operations for ESASS-generated skills.
    """

    def __init__(
        self,
        registry_url: str = "https://clawhub.com",
        token: Optional[str] = None,
        auto_bump: str = "patch"  # patch, minor, major
    ):
        self.registry_url = registry_url
        self.token = token or os.environ.get("CLAWHUB_TOKEN")
        self.auto_bump = auto_bump

        # Verify clawhub CLI is installed
        self._verify_cli()

    def _verify_cli(self) -> None:
        """Check if clawhub CLI is available"""
        try:
            subprocess.run(
                ["clawhub", "--version"],
                capture_output=True,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "clawhub CLI not found. Install with: npm i -g clawhub"
            )

    def _run_clawhub(self, args: list, capture: bool = True) -> subprocess.CompletedProcess:
        """Run clawhub CLI command"""
        cmd = ["clawhub"] + args

        if self.token:
            cmd.extend(["--token", self.token])

        return subprocess.run(
            cmd,
            capture_output=capture,
            text=True
        )

    def authenticate(self, token: Optional[str] = None) -> bool:
        """Authenticate with ClawHub"""
        token = token or self.token
        if not token:
            # Browser-based login
            result = self._run_clawhub(["login"])
            return result.returncode == 0

        # Token-based login
        result = self._run_clawhub(["login", "--token", token])
        return result.returncode == 0

    def whoami(self) -> Optional[str]:
        """Get current authenticated user"""
        result = self._run_clawhub(["whoami"])
        if result.returncode == 0:
            return result.stdout.strip()
        return None

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search for skills on ClawHub"""
        result = self._run_clawhub([
            "search", query,
            "--limit", str(limit),
            "--json"  # If supported
        ])

        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                # Parse text output
                return self._parse_search_output(result.stdout)

        return []

    def _parse_search_output(self, output: str) -> list[dict]:
        """Parse search output if not JSON"""
        skills = []
        for line in output.strip().split("\n"):
            if line.strip():
                # Basic parsing - adjust based on actual output format
                parts = line.split(" - ", 1)
                if len(parts) == 2:
                    skills.append({
                        "slug": parts[0].strip(),
                        "description": parts[1].strip()
                    })
        return skills

    def skill_exists(self, slug: str) -> bool:
        """Check if skill exists on ClawHub"""
        results = self.search(slug, limit=1)
        return any(r.get("slug") == slug for r in results)

    def publish(
        self,
        skill_path: Path,
        slug: Optional[str] = None,
        name: Optional[str] = None,
        version: Optional[str] = None,
        changelog: str = "ESASS auto-generated skill",
        tags: list[str] = None
    ) -> PublishResponse:
        """
        Publish a skill to ClawHub.

        Args:
            skill_path: Path to skill directory containing SKILL.md
            slug: Skill slug (derived from directory name if not provided)
            name: Display name
            version: Semver version
            changelog: Version changelog
            tags: Tags for the skill (default: ["latest", "esass-generated"])

        Returns:
            PublishResponse with result status
        """
        skill_path = Path(skill_path)

        if not (skill_path / "SKILL.md").exists():
            return PublishResponse(
                result=PublishResult.VALIDATION_FAILED,
                skill_slug=slug or skill_path.name,
                version=version or "0.0.0",
                message="SKILL.md not found"
            )

        # Determine slug from path if not provided
        slug = slug or skill_path.name

        # Read SKILL.md for metadata
        metadata = self._read_skill_metadata(skill_path / "SKILL.md")
        name = name or metadata.get("name", slug)
        version = version or metadata.get("version", "1.0.0")

        # Default tags
        tags = tags or ["latest", "esass-generated"]

        # Build command
        args = [
            "publish", str(skill_path),
            "--slug", slug,
            "--name", name,
            "--version", version,
            "--changelog", changelog,
            "--tags", ",".join(tags)
        ]

        result = self._run_clawhub(args)

        if result.returncode == 0:
            return PublishResponse(
                result=PublishResult.SUCCESS,
                skill_slug=slug,
                version=version,
                url=f"{self.registry_url}/skills/{slug}",
                message="Successfully published"
            )

        # Parse error
        error_msg = result.stderr or result.stdout

        if "already exists" in error_msg.lower():
            return PublishResponse(
                result=PublishResult.ALREADY_EXISTS,
                skill_slug=slug,
                version=version,
                message="Version already exists"
            )

        if "unauthorized" in error_msg.lower() or "auth" in error_msg.lower():
            return PublishResponse(
                result=PublishResult.AUTH_FAILED,
                skill_slug=slug,
                version=version,
                message="Authentication failed"
            )

        return PublishResponse(
            result=PublishResult.UNKNOWN_ERROR,
            skill_slug=slug,
            version=version,
            message=error_msg
        )

    def _read_skill_metadata(self, skill_file: Path) -> dict:
        """Read metadata from SKILL.md frontmatter"""
        import yaml

        content = skill_file.read_text()

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    return yaml.safe_load(parts[1])
                except yaml.YAMLError:
                    pass

        return {}

    def install(self, slug: str, version: Optional[str] = None) -> bool:
        """Install a skill from ClawHub"""
        args = ["install", slug]
        if version:
            args.extend(["--version", version])

        result = self._run_clawhub(args)
        return result.returncode == 0

    def update(self, slug: Optional[str] = None, all_skills: bool = False) -> bool:
        """Update installed skills"""
        if all_skills:
            args = ["update", "--all"]
        else:
            args = ["update", slug]

        result = self._run_clawhub(args)
        return result.returncode == 0

    def sync(
        self,
        skill_dirs: list[Path],
        dry_run: bool = False,
        bump: Optional[str] = None
    ) -> list[PublishResponse]:
        """
        Sync multiple skill directories to ClawHub.

        Args:
            skill_dirs: List of skill directories to sync
            dry_run: Preview without publishing
            bump: Version bump type (patch, minor, major)

        Returns:
            List of publish responses
        """
        responses = []
        bump = bump or self.auto_bump

        for skill_dir in skill_dirs:
            if not skill_dir.is_dir():
                continue

            if not (skill_dir / "SKILL.md").exists():
                continue

            if dry_run:
                print(f"Would publish: {skill_dir.name}")
                continue

            # Check if update needed
            slug = skill_dir.name
            metadata = self._read_skill_metadata(skill_dir / "SKILL.md")
            current_version = metadata.get("version", "1.0.0")

            if self.skill_exists(slug):
                # Bump version for update
                new_version = self._bump_version(current_version, bump)
                response = self.publish(
                    skill_dir,
                    version=new_version,
                    changelog=f"ESASS auto-update ({bump})"
                )
            else:
                # New skill
                response = self.publish(skill_dir)

            responses.append(response)

        return responses

    def _bump_version(self, version: str, bump: str) -> str:
        """Bump semver version"""
        parts = version.split(".")
        if len(parts) != 3:
            return "1.0.0"

        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

        if bump == "major":
            return f"{major + 1}.0.0"
        elif bump == "minor":
            return f"{major}.{minor + 1}.0"
        else:  # patch
            return f"{major}.{minor}.{patch + 1}"


class ESASSClawHubPublisher:
    """
    High-level publisher for ESASS-generated skills.

    Handles the full workflow from skill manifest to published skill.
    """

    def __init__(
        self,
        formatter: "SkillFormatter",
        client: ClawHubClient,
        require_confidence: float = 0.85,
        require_support: int = 15
    ):
        self.formatter = formatter
        self.client = client
        self.require_confidence = require_confidence
        self.require_support = require_support

    def publish_skill(
        self,
        manifest: "SkillManifest",
        pattern: Optional["PatternDefinition"] = None,
        auto_authenticate: bool = True
    ) -> PublishResponse:
        """
        Publish an ESASS skill manifest to ClawHub.

        Args:
            manifest: ESASS skill manifest
            pattern: Source pattern (for metadata)
            auto_authenticate: Attempt auth if needed

        Returns:
            PublishResponse
        """
        # Validate quality thresholds
        if pattern:
            if pattern.confidence < self.require_confidence:
                return PublishResponse(
                    result=PublishResult.VALIDATION_FAILED,
                    skill_slug=manifest.name,
                    version=manifest.version,
                    message=f"Confidence {pattern.confidence} below threshold {self.require_confidence}"
                )

            if pattern.support < self.require_support:
                return PublishResponse(
                    result=PublishResult.VALIDATION_FAILED,
                    skill_slug=manifest.name,
                    version=manifest.version,
                    message=f"Support {pattern.support} below threshold {self.require_support}"
                )

        # Convert to SKILL.md
        skill_path = self.formatter.save_skill(manifest, pattern)

        # Authenticate if needed
        if auto_authenticate and not self.client.whoami():
            self.client.authenticate()

        # Publish
        return self.client.publish(skill_path.parent)

    def publish_batch(
        self,
        manifests: list["SkillManifest"],
        patterns: Optional[dict[str, "PatternDefinition"]] = None
    ) -> list[PublishResponse]:
        """Publish multiple skills"""
        patterns = patterns or {}
        responses = []

        for manifest in manifests:
            pattern = None
            if manifest.source_pattern_ids:
                pattern = patterns.get(manifest.source_pattern_ids[0])

            response = self.publish_skill(manifest, pattern)
            responses.append(response)

        return responses
