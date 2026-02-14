"""
ESASS Skill to OpenClaw SKILL.md Converter

Transforms ESASS SkillManifest objects into OpenClaw-compatible SKILL.md files.
"""

import yaml
import os
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

# Assuming ESASS models
from esass_prototype.models import SkillManifest, PatternDefinition


@dataclass
class OpenClawSkillMetadata:
    """OpenClaw SKILL.md frontmatter structure"""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "esass-genesis"
    genesis_type: str = "emergent"
    pattern_id: Optional[str] = None
    confidence: float = 0.0
    support: int = 0
    first_observed: Optional[str] = None
    triggers: list = None
    capabilities: list = None
    parent_skills: list = None
    child_skills: list = None
    generation: int = 1

    def __post_init__(self):
        if self.triggers is None:
            self.triggers = []
        if self.capabilities is None:
            self.capabilities = []
        if self.parent_skills is None:
            self.parent_skills = []
        if self.child_skills is None:
            self.child_skills = []


class SkillFormatter:
    """
    Converts ESASS skills to OpenClaw SKILL.md format.

    This adapter ensures generated skills are compatible with OpenClaw's
    skill loading system and can be published to ClawHub.
    """

    def __init__(self, output_dir: str = "./skills/generated"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def format_skill(
        self,
        manifest: SkillManifest,
        pattern: Optional[PatternDefinition] = None
    ) -> str:
        """
        Convert ESASS SkillManifest to SKILL.md content.

        Args:
            manifest: ESASS skill manifest
            pattern: Optional source pattern for additional context

        Returns:
            Complete SKILL.md file content
        """
        metadata = self._build_metadata(manifest, pattern)
        frontmatter = self._format_frontmatter(metadata)
        body = self._generate_body(manifest, pattern, metadata)

        return f"{frontmatter}\n{body}"

    def _build_metadata(
        self,
        manifest: SkillManifest,
        pattern: Optional[PatternDefinition]
    ) -> OpenClawSkillMetadata:
        """Extract metadata for frontmatter"""

        # Parse triggers from manifest
        triggers = []
        for trigger in manifest.triggers:
            if trigger.startswith("intent_match:"):
                # Convert "intent_match:git,commit" to "git commit"
                intent = trigger.replace("intent_match:", "").replace(",", " ")
                triggers.append(intent)

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
            parent_skills=getattr(manifest, 'parent_skills', []),
            child_skills=getattr(manifest, 'child_skills', []),
            generation=getattr(manifest, 'generation', 1)
        )

    def _format_skill_name(self, name: str) -> str:
        """Convert skill name to kebab-case for OpenClaw"""
        return name.replace("_", "-").lower()

    def _infer_triggers(self, manifest: SkillManifest) -> list:
        """Infer natural language triggers from skill"""
        triggers = []

        # Extract from capabilities
        capability_triggers = {
            "git_operations": ["git", "commit", "push", "pull"],
            "file_operations": ["read file", "write file", "edit"],
            "code_analysis": ["analyze code", "review", "check"],
            "testing": ["run tests", "test", "coverage"],
            "documentation": ["document", "docs", "readme"]
        }

        for cap in manifest.capabilities:
            if cap in capability_triggers:
                triggers.extend(capability_triggers[cap])

        return triggers[:5]  # Limit to 5 triggers

    def _format_frontmatter(self, metadata: OpenClawSkillMetadata) -> str:
        """Generate YAML frontmatter"""
        data = {
            "name": metadata.name,
            "description": metadata.description,
            "version": metadata.version,
            "author": metadata.author,
            "genesis": {
                "type": metadata.genesis_type,
                "pattern_id": metadata.pattern_id,
                "confidence": round(metadata.confidence, 2),
                "support": metadata.support,
                "first_observed": metadata.first_observed
            },
            "metadata": {
                "openclaw": {
                    "triggers": metadata.triggers,
                    "capabilities": metadata.capabilities,
                    "evolution": {
                        "parent_skills": metadata.parent_skills,
                        "child_skills": metadata.child_skills,
                        "generation": metadata.generation
                    }
                }
            }
        }

        yaml_content = yaml.dump(data, default_flow_style=False, sort_keys=False)
        return f"---\n{yaml_content}---"

    def _generate_body(
        self,
        manifest: SkillManifest,
        pattern: Optional[PatternDefinition],
        metadata: OpenClawSkillMetadata
    ) -> str:
        """Generate the markdown body of the skill"""

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
            self._generate_evolution_history(manifest, metadata)
        ]

        return "\n".join(sections)

    def _title_case(self, text: str) -> str:
        """Convert text to title case"""
        return " ".join(word.capitalize() for word in text.split())

    def _generate_when_to_use(self, metadata: OpenClawSkillMetadata) -> str:
        """Generate when-to-use section"""
        triggers_text = ", ".join(f'"{t}"' for t in metadata.triggers[:3])
        return f"""Use this skill when the user wants to {metadata.description.lower()}.
This skill is triggered by phrases like {triggers_text}."""

    def _generate_workflow(
        self,
        manifest: SkillManifest,
        pattern: Optional[PatternDefinition]
    ) -> str:
        """Generate workflow section from pattern sequence"""
        if pattern and pattern.sequence:
            steps = []
            for i, step in enumerate(pattern.sequence, 1):
                # Parse step like "tool_usage:git,status"
                parts = step.split(":")
                event_type = parts[0]
                details = parts[1] if len(parts) > 1 else ""

                step_text = self._format_workflow_step(event_type, details)
                steps.append(f"{i}. **{step_text['title']}**\n   {step_text['description']}")

            return "\n\n".join(steps)

        return manifest.implementation_summary or "See implementation details."

    def _format_workflow_step(self, event_type: str, details: str) -> dict:
        """Format a single workflow step"""
        templates = {
            "reasoning": {
                "title": "Analyze Context",
                "description": f"Evaluate the situation: {details.replace(',', ', ')}"
            },
            "tool_usage": {
                "title": f"Execute {details.split(',')[0].title() if details else 'Tool'}",
                "description": f"```bash\n{details.replace(',', ' ')}\n```"
            },
            "decision": {
                "title": "Make Decision",
                "description": f"Choose approach based on: {details.replace(',', ', ')}"
            },
            "outcome": {
                "title": "Verify Result",
                "description": "Confirm successful execution and report to user"
            }
        }

        return templates.get(event_type, {
            "title": event_type.replace("_", " ").title(),
            "description": details
        })

    def _generate_error_handling(self, manifest: SkillManifest) -> str:
        """Generate error handling section"""
        # Infer from capabilities
        handlers = []

        if "git_operations" in manifest.capabilities:
            handlers.extend([
                "- **No staged changes**: Prompt user to stage or offer `git add -A`",
                "- **Merge conflicts**: Detect and guide resolution",
                "- **Detached HEAD**: Warn and suggest branch creation"
            ])

        if "file_operations" in manifest.capabilities:
            handlers.extend([
                "- **File not found**: Search for alternatives or prompt for path",
                "- **Permission denied**: Suggest chmod or elevated permissions",
                "- **Encoding issues**: Detect and handle non-UTF8 files"
            ])

        if "code_analysis" in manifest.capabilities:
            handlers.extend([
                "- **Syntax errors**: Report location and suggest fixes",
                "- **Large files**: Warn about performance and offer chunking"
            ])

        return "\n".join(handlers) if handlers else "- Handle errors gracefully and report to user"

    def _generate_examples(
        self,
        manifest: SkillManifest,
        metadata: OpenClawSkillMetadata
    ) -> str:
        """Generate example usage"""
        examples = []

        for i, trigger in enumerate(metadata.triggers[:2], 1):
            examples.append(f"""### Example {i}
User: "{trigger.title()}"
Action: {manifest.description}""")

        return "\n\n".join(examples) if examples else "See workflow for usage examples."

    def _generate_dependencies(self, manifest: SkillManifest) -> str:
        """Generate dependencies section"""
        deps = []

        capability_deps = {
            "git_operations": "- git (required)",
            "file_operations": "- filesystem access (required)",
            "web_operations": "- curl or web tool (required)",
            "code_analysis": "- language-specific linters (optional)",
            "testing": "- test framework (project-dependent)"
        }

        for cap in manifest.capabilities:
            if cap in capability_deps:
                deps.append(capability_deps[cap])

        return "\n".join(deps) if deps else "- None"

    def _generate_evolution_history(
        self,
        manifest: SkillManifest,
        metadata: OpenClawSkillMetadata
    ) -> str:
        """Generate evolution history"""
        history = [
            f"- v{metadata.version}: Initial emergent pattern detection (ESASS genesis)"
        ]

        if metadata.parent_skills:
            history.append(f"- Derived from: {', '.join(metadata.parent_skills)}")

        return "\n".join(history)

    def save_skill(
        self,
        manifest: SkillManifest,
        pattern: Optional[PatternDefinition] = None
    ) -> Path:
        """Save skill to file system"""
        content = self.format_skill(manifest, pattern)
        skill_name = self._format_skill_name(manifest.name)

        # Create skill directory
        skill_dir = self.output_dir / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Write SKILL.md
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(content)

        return skill_file

    def batch_convert(
        self,
        manifests: list[SkillManifest],
        patterns: Optional[dict[str, PatternDefinition]] = None
    ) -> list[Path]:
        """Convert multiple skills"""
        patterns = patterns or {}
        saved = []

        for manifest in manifests:
            pattern = None
            if manifest.source_pattern_ids:
                pattern = patterns.get(manifest.source_pattern_ids[0])

            path = self.save_skill(manifest, pattern)
            saved.append(path)

        return saved
