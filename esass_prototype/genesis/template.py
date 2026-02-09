"""
Skill template generator - creates skill manifests from validated patterns.

Template-based generation following §6.3 of specification.
"""

from collections import Counter
from typing import List

from esass_prototype.models import PatternDefinition, SkillManifest


class SkillTemplateGenerator:
    """
    Generate skill manifests from validated patterns.

    Simplified from §6.3 of specification using template-based approach.
    """

    def generate_from_pattern(self, pattern: PatternDefinition) -> SkillManifest:
        """
        Create skill manifest from pattern.

        Args:
            pattern: PatternDefinition to convert

        Returns:
            SkillManifest object
        """
        # Extract triggers from pattern
        triggers = self._extract_triggers(pattern)

        # Infer capabilities
        capabilities = self._infer_capabilities(pattern)

        # Generate name
        name = self._generate_name(pattern)

        # Generate implementation summary
        implementation_summary = self._generate_implementation_summary(pattern)

        # Create manifest
        skill = SkillManifest(
            genesis_type="derived",
            name=name,
            description=pattern.description,
            keywords=pattern.tags,
            source_pattern_ids=[pattern.pattern_id],
            triggers=triggers,
            capabilities=capabilities,
            implementation_summary=implementation_summary,
            validation_status="pending",
            tags=pattern.tags
        )

        return skill

    def generate_from_patterns(
        self,
        patterns: List[PatternDefinition]
    ) -> List[SkillManifest]:
        """
        Generate multiple skills from patterns.

        Args:
            patterns: List of PatternDefinition objects

        Returns:
            List of SkillManifest objects
        """
        return [self.generate_from_pattern(p) for p in patterns]

    def _extract_triggers(self, pattern: PatternDefinition) -> List[str]:
        """
        Extract trigger conditions from pattern.

        Args:
            pattern: PatternDefinition

        Returns:
            List of trigger strings
        """
        triggers = []

        # Get first event in sequence
        if pattern.sequence:
            first_event = pattern.sequence[0]

            # Handle both "event_type:tags" and "event_type" formats
            if ':' in first_event:
                event_type, tags = first_event.split(':', 1)
            else:
                event_type = first_event
                tags = "none"

            # Create semantic trigger from tags
            if tags != "none":
                tag_list = tags.split(',')
                triggers.append(f"intent_match:{','.join(tag_list[:3])}")

            # Create event type trigger
            triggers.append(f"event_type:{event_type}")

            # Add context trigger based on pattern tags
            if pattern.tags:
                triggers.append(f"context:{','.join(pattern.tags[:3])}")

        return triggers

    def _infer_capabilities(self, pattern: PatternDefinition) -> List[str]:
        """
        Infer capabilities from pattern structure.

        Args:
            pattern: PatternDefinition

        Returns:
            List of capability strings
        """
        capabilities = []

        # Analyze sequence for capability indicators
        for event in pattern.sequence:
            # Handle both "event_type:tags" and "event_type" formats
            if ':' in event:
                event_type, tags = event.split(':', 1)
            else:
                event_type = event
                tags = ""

            # Git operations
            if "git" in tags:
                capabilities.append("git_operations")

            # Tool orchestration
            if event_type == "tool_usage":
                capabilities.append("tool_orchestration")

            # Problem analysis
            if event_type == "reasoning":
                capabilities.append("problem_analysis")

            # Decision making
            if event_type == "decision":
                capabilities.append("decision_making")

            # File operations
            if any(tag in tags for tag in ["read", "write", "edit"]):
                capabilities.append("file_operations")

            # Testing
            if any(tag in tags for tag in ["test", "pytest", "validation"]):
                capabilities.append("testing")

            # Documentation
            if any(tag in tags for tag in ["documentation", "readme", "markdown"]):
                capabilities.append("documentation")

            # Debugging
            if any(tag in tags for tag in ["bug", "error", "debug", "fix"]):
                capabilities.append("debugging")

        # Deduplicate and return
        return list(set(capabilities))

    def _generate_name(self, pattern: PatternDefinition) -> str:
        """
        Generate skill name from pattern.

        Args:
            pattern: PatternDefinition

        Returns:
            Skill name
        """
        # Extract dominant tags
        all_tags = []
        for event in pattern.sequence:
            if ':' in event:
                _, tags = event.split(':', 1)
                if tags != "none":
                    all_tags.extend(tags.split(','))

        # Find most common tags
        tag_counts = Counter(all_tags)
        top_tags = [tag for tag, _ in tag_counts.most_common(2)]

        if len(top_tags) >= 2:
            return f"{top_tags[0]}_{top_tags[1]}_skill"
        elif len(top_tags) == 1:
            return f"{top_tags[0]}_workflow_skill"
        else:
            return f"pattern_{pattern.pattern_id[:8]}_skill"

    def _generate_implementation_summary(
        self,
        pattern: PatternDefinition
    ) -> str:
        """
        Generate implementation summary from pattern.

        Args:
            pattern: PatternDefinition

        Returns:
            Implementation summary as string
        """
        # Build step-by-step summary
        steps = []

        for i, event in enumerate(pattern.sequence, 1):
            # Handle both "event_type:tags" and "event_type" formats
            if ':' in event:
                event_type, tags = event.split(':', 1)
            else:
                event_type = event
                tags = "none"

            # Create human-readable step
            tag_list = tags.split(',') if tags != "none" else []

            if event_type == "reasoning":
                step = f"Step {i}: Analyze and reason about {', '.join(tag_list[:2])}"
            elif event_type == "tool_usage":
                step = f"Step {i}: Execute tools for {', '.join(tag_list[:2])}"
            elif event_type == "decision":
                step = f"Step {i}: Make decision regarding {', '.join(tag_list[:2])}"
            elif event_type == "output":
                step = f"Step {i}: Generate output"
            else:
                step = f"Step {i}: {event_type}"

            steps.append(step)

        summary = "\n".join(steps)

        # Add context
        summary = (
            f"This skill implements a {len(pattern.sequence)}-step workflow:\n\n"
            f"{summary}\n\n"
            f"Observed {pattern.support} times with {pattern.confidence:.0%} confidence.\n"
            f"Pattern stable for {pattern.stability_days} days."
        )

        return summary
