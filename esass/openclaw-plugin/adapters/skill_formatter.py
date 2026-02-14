"""
ESASS Skill → OpenClaw SKILL.md Converter (rewritten).

Transforms ESASS SkillManifest objects into OpenClaw-compatible SKILL.md files,
with funding block injection and lineage metadata.
"""

from __future__ import annotations

import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from esass_prototype.models import SkillManifest, PatternDefinition

from .metadata import OpenClawSkillMetadata


class SkillFormatter:
    """Converts ESASS skills to OpenClaw SKILL.md format."""

    def __init__(
        self,
        output_dir: str = "./skills/generated",
        funding_injector: Optional[Any] = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._funding_injector = funding_injector

    # ---- Public API ----

    def format_skill(
        self,
        manifest: SkillManifest,
        pattern: Optional[PatternDefinition] = None,
    ) -> str:
        """Convert SkillManifest to full SKILL.md content."""
        metadata = self._build_metadata(manifest, pattern)
        frontmatter = self._format_frontmatter(metadata)
        body = self._generate_body(manifest, pattern, metadata)
        return f"{frontmatter}\n{body}"

    def save_skill(
        self,
        manifest: SkillManifest,
        pattern: Optional[PatternDefinition] = None,
    ) -> Path:
        """Save skill to filesystem and return SKILL.md path."""
        content = self.format_skill(manifest, pattern)
        skill_name = self._format_skill_name(manifest.name)
        skill_dir = self.output_dir / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(content, encoding="utf-8")
        return skill_file

    def batch_convert(
        self,
        manifests: List[SkillManifest],
        patterns: Optional[Dict[str, PatternDefinition]] = None,
    ) -> List[Path]:
        """Convert multiple skills."""
        patterns = patterns or {}
        saved: List[Path] = []
        for manifest in manifests:
            pattern = None
            if manifest.source_pattern_ids:
                pattern = patterns.get(manifest.source_pattern_ids[0])
            saved.append(self.save_skill(manifest, pattern))
        return saved

    # ---- Metadata ----

    def _build_metadata(
        self,
        manifest: SkillManifest,
        pattern: Optional[PatternDefinition],
    ) -> OpenClawSkillMetadata:
        triggers: List[str] = []
        for trigger in manifest.triggers:
            t_str = trigger if isinstance(trigger, str) else f"{trigger.trigger_type}:{trigger.pattern}"
            if t_str.startswith("intent_match:"):
                intent = t_str.replace("intent_match:", "").replace(",", " ")
                triggers.append(intent)

        funding_dict = None
        if self._funding_injector:
            block = self._funding_injector.get_frontmatter_block()
            funding_dict = block.get("funding")

        # Also pick up funding already on manifest
        if not funding_dict and manifest.funding:
            funding_dict = manifest.funding

        return OpenClawSkillMetadata(
            name=self._format_skill_name(manifest.name),
            description=manifest.description,
            version=manifest.version,
            author="esass-genesis",
            genesis_type=manifest.genesis_type,
            pattern_id=manifest.source_pattern_ids[0] if manifest.source_pattern_ids else None,
            confidence=pattern.confidence if pattern else 0.9,
            support=pattern.support if pattern else 0,
            first_observed=pattern.first_seen if pattern else datetime.utcnow().isoformat(),
            triggers=triggers or self._infer_triggers(manifest),
            capabilities=list(manifest.capabilities),
            parent_skills=getattr(manifest, "parent_skill_ids", []),
            child_skills=getattr(manifest, "child_skill_ids", []),
            generation=1,
            parent_skill_ids=getattr(manifest, "parent_skill_ids", []),
            child_skill_ids=getattr(manifest, "child_skill_ids", []),
            derived_from_unification=getattr(manifest, "derived_from_unification", None),
            funding=funding_dict,
        )

    # ---- Frontmatter ----

    def _format_frontmatter(self, metadata: OpenClawSkillMetadata) -> str:
        data: Dict[str, Any] = {
            "name": metadata.name,
            "description": metadata.description,
            "version": metadata.version,
            "author": metadata.author,
            "genesis": {
                "type": metadata.genesis_type,
                "pattern_id": metadata.pattern_id,
                "confidence": round(metadata.confidence, 2),
                "support": metadata.support,
                "first_observed": metadata.first_observed,
            },
            "metadata": {
                "openclaw": {
                    "triggers": metadata.triggers,
                    "capabilities": metadata.capabilities,
                    "evolution": {
                        "parent_skills": metadata.parent_skills,
                        "child_skills": metadata.child_skills,
                        "generation": metadata.generation,
                    },
                },
            },
        }

        # Lineage
        if metadata.parent_skill_ids or metadata.child_skill_ids or metadata.derived_from_unification:
            data["lineage"] = {}
            if metadata.parent_skill_ids:
                data["lineage"]["parent_skill_ids"] = metadata.parent_skill_ids
            if metadata.child_skill_ids:
                data["lineage"]["child_skill_ids"] = metadata.child_skill_ids
            if metadata.derived_from_unification:
                data["lineage"]["derived_from_unification"] = metadata.derived_from_unification

        # Funding block
        if metadata.funding:
            data["funding"] = metadata.funding

        yaml_content = yaml.dump(data, default_flow_style=False, sort_keys=False)
        return f"---\n{yaml_content}---"

    # ---- Body generation ----

    def _generate_body(
        self,
        manifest: SkillManifest,
        pattern: Optional[PatternDefinition],
        metadata: OpenClawSkillMetadata,
    ) -> str:
        title = self._title_case(metadata.name.replace("-", " "))
        sections = [
            f"# {title}",
            "",
            "## Overview",
            manifest.description,
            "",
            "## When to Use",
            self._generate_when_to_use(metadata),
            "",
            "## Workflow",
            self._generate_workflow(manifest, pattern),
            "",
            "## Error Handling",
            self._generate_error_handling(manifest),
            "",
            "## Examples",
            self._generate_examples(manifest, metadata),
            "",
            "## Dependencies",
            self._generate_dependencies(manifest),
            "",
            "## Evolution History",
            self._generate_evolution_history(manifest, metadata),
        ]

        # Donation badge
        if metadata.funding:
            from openclaw_plugin.donation.display import DonationDisplay
            display = DonationDisplay()
            badge = display.render_markdown_badge()
            if badge:
                sections.extend(["", "## Support", badge])

        return "\n".join(sections)

    # ---- Helpers ----

    @staticmethod
    def _format_skill_name(name: str) -> str:
        return name.replace("_", "-").lower()

    @staticmethod
    def _title_case(text: str) -> str:
        return " ".join(word.capitalize() for word in text.split())

    @staticmethod
    def _infer_triggers(manifest: SkillManifest) -> List[str]:
        capability_triggers = {
            "git_operations": ["git", "commit", "push", "pull"],
            "file_operations": ["read file", "write file", "edit"],
            "code_analysis": ["analyze code", "review", "check"],
            "testing": ["run tests", "test", "coverage"],
            "documentation": ["document", "docs", "readme"],
        }
        triggers: List[str] = []
        for cap in manifest.capabilities:
            if cap in capability_triggers:
                triggers.extend(capability_triggers[cap])
        return triggers[:5]

    def _generate_when_to_use(self, metadata: OpenClawSkillMetadata) -> str:
        triggers_text = ", ".join(f'"{t}"' for t in metadata.triggers[:3])
        return (
            f"Use this skill when the user wants to {metadata.description.lower()}.\n"
            f"This skill is triggered by phrases like {triggers_text}."
        )

    def _generate_workflow(
        self, manifest: SkillManifest, pattern: Optional[PatternDefinition]
    ) -> str:
        if pattern and pattern.sequence:
            steps = []
            for i, step in enumerate(pattern.sequence, 1):
                parts = step.split(":")
                event_type = parts[0]
                details = parts[1] if len(parts) > 1 else ""
                s = self._format_workflow_step(event_type, details)
                steps.append(f"{i}. **{s['title']}**\n   {s['description']}")
            return "\n\n".join(steps)
        return manifest.implementation_summary or "See implementation details."

    @staticmethod
    def _format_workflow_step(event_type: str, details: str) -> Dict[str, str]:
        templates = {
            "reasoning": {
                "title": "Analyze Context",
                "description": f"Evaluate the situation: {details.replace(',', ', ')}",
            },
            "tool_usage": {
                "title": f"Execute {details.split(',')[0].title() if details else 'Tool'}",
                "description": f"```bash\n{details.replace(',', ' ')}\n```",
            },
            "decision": {
                "title": "Make Decision",
                "description": f"Choose approach based on: {details.replace(',', ', ')}",
            },
            "outcome": {
                "title": "Verify Result",
                "description": "Confirm successful execution and report to user",
            },
        }
        return templates.get(event_type, {
            "title": event_type.replace("_", " ").title(),
            "description": details,
        })

    @staticmethod
    def _generate_error_handling(manifest: SkillManifest) -> str:
        handlers: List[str] = []
        if "git_operations" in manifest.capabilities:
            handlers.extend([
                "- **No staged changes**: Prompt user to stage or offer `git add -A`",
                "- **Merge conflicts**: Detect and guide resolution",
                "- **Detached HEAD**: Warn and suggest branch creation",
            ])
        if "file_operations" in manifest.capabilities:
            handlers.extend([
                "- **File not found**: Search for alternatives or prompt for path",
                "- **Permission denied**: Suggest chmod or elevated permissions",
                "- **Encoding issues**: Detect and handle non-UTF8 files",
            ])
        if "code_analysis" in manifest.capabilities:
            handlers.extend([
                "- **Syntax errors**: Report location and suggest fixes",
                "- **Large files**: Warn about performance and offer chunking",
            ])
        return "\n".join(handlers) if handlers else "- Handle errors gracefully and report to user"

    @staticmethod
    def _generate_examples(manifest: SkillManifest, metadata: OpenClawSkillMetadata) -> str:
        examples = []
        for i, trigger in enumerate(metadata.triggers[:2], 1):
            examples.append(
                f"### Example {i}\nUser: \"{trigger.title()}\"\nAction: {manifest.description}"
            )
        return "\n\n".join(examples) if examples else "See workflow for usage examples."

    @staticmethod
    def _generate_dependencies(manifest: SkillManifest) -> str:
        cap_deps = {
            "git_operations": "- git (required)",
            "file_operations": "- filesystem access (required)",
            "web_operations": "- curl or web tool (required)",
            "code_analysis": "- language-specific linters (optional)",
            "testing": "- test framework (project-dependent)",
        }
        deps = [cap_deps[cap] for cap in manifest.capabilities if cap in cap_deps]
        return "\n".join(deps) if deps else "- None"

    @staticmethod
    def _generate_evolution_history(
        manifest: SkillManifest, metadata: OpenClawSkillMetadata
    ) -> str:
        history = [f"- v{metadata.version}: Initial emergent pattern detection (ESASS genesis)"]
        if metadata.parent_skills:
            history.append(f"- Derived from: {', '.join(metadata.parent_skills)}")
        return "\n".join(history)
