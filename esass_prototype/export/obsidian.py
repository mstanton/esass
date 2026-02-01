"""
Obsidian exporter - exports ESASS data to Obsidian vault as markdown files.

Formats data with YAML frontmatter for Obsidian integration.
"""

from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import List

from esass_prototype.models import LogEntry, PatternDefinition, SkillManifest


class ObsidianExporter:
    """
    Export ESASS data to Obsidian vault as markdown files.

    Creates structured documentation with YAML frontmatter and internal links.
    """

    def __init__(self, vault_path: Path):
        """
        Initialize exporter.

        Args:
            vault_path: Path to Obsidian vault
        """
        self.vault_path = Path(vault_path)
        self.esass_dir = self.vault_path / "ESASS"

    def export_all(
        self,
        logs: List[LogEntry],
        patterns: List[PatternDefinition],
        skills: List[SkillManifest]
    ):
        """
        Export all data to Obsidian.

        Args:
            logs: List of log entries
            patterns: List of patterns
            skills: List of skills
        """
        self._ensure_directories()

        # Export logs (daily summaries)
        self._export_logs(logs)

        # Export patterns
        self._export_patterns(patterns)

        # Export skills
        self._export_skills(skills)

        # Create index
        self._create_index(len(logs), len(patterns), len(skills))

    def _ensure_directories(self):
        """Create directory structure"""
        (self.esass_dir / "logs").mkdir(parents=True, exist_ok=True)
        (self.esass_dir / "patterns").mkdir(parents=True, exist_ok=True)
        (self.esass_dir / "skills").mkdir(parents=True, exist_ok=True)

    def _export_logs(self, logs: List[LogEntry]):
        """
        Export logs as daily summary files.

        Args:
            logs: List of log entries
        """
        # Group by date
        by_date = defaultdict(list)
        for entry in logs:
            date = datetime.fromisoformat(entry.timestamp).date()
            by_date[date].append(entry)

        # Create daily summaries
        for date, entries in by_date.items():
            filename = f"{date.isoformat()}.md"
            filepath = self.esass_dir / "logs" / filename

            content = self._format_log_summary(date, entries)
            filepath.write_text(content, encoding='utf-8')

    def _format_log_summary(self, date, entries: List[LogEntry]) -> str:
        """Format daily log summary"""
        content = f"""---
date: {date.isoformat()}
type: esass-log-summary
entry_count: {len(entries)}
---

# ESASS Observation Log - {date.isoformat()}

**Total Events**: {len(entries)}

## Event Distribution

"""
        # Count by type
        type_counts = Counter([e.event_type for e in entries])
        for event_type, count in type_counts.most_common():
            content += f"- **{event_type}**: {count}\n"

        content += "\n## Sessions\n\n"

        # Group by session
        sessions = defaultdict(list)
        for entry in entries:
            sessions[entry.session_id].append(entry)

        for session_id, session_entries in sessions.items():
            content += f"### Session `{session_id[:8]}...`\n\n"
            content += f"Events: {len(session_entries)}\n\n"

            # Show event sequence
            content += "```\n"
            for entry in sorted(session_entries, key=lambda e: e.timestamp):
                time = datetime.fromisoformat(entry.timestamp).strftime("%H:%M:%S")
                tags_str = ','.join(entry.tags[:3]) if entry.tags else "none"
                content += f"{time} | {entry.event_type} | {tags_str}\n"
            content += "```\n\n"

        return content

    def _export_patterns(self, patterns: List[PatternDefinition]):
        """
        Export pattern definitions.

        Args:
            patterns: List of patterns
        """
        for pattern in patterns:
            filename = f"pattern_{pattern.pattern_id[:8]}.md"
            filepath = self.esass_dir / "patterns" / filename

            content = self._format_pattern(pattern)
            filepath.write_text(content, encoding='utf-8')

    def _format_pattern(self, pattern: PatternDefinition) -> str:
        """Format pattern as markdown"""
        skill_status = "✅ Yes" if pattern.skill_candidate else "❌ No"

        content = f"""---
pattern_id: {pattern.pattern_id}
type: {pattern.pattern_type}
support: {pattern.support}
confidence: {pattern.confidence:.2f}
stability_days: {pattern.stability_days}
skill_candidate: {pattern.skill_candidate}
first_seen: {pattern.first_seen}
last_seen: {pattern.last_seen}
---

# Pattern: {pattern.description}

## Metrics

- **Support**: {pattern.support} instances
- **Confidence**: {pattern.confidence:.1%}
- **Stability**: {pattern.stability_days} days
- **Skill Candidate**: {skill_status}

## Sequence

```
{' → '.join(pattern.sequence)}
```

## Analysis

This pattern was detected through temporal sequence mining across {pattern.support} sessions.

Pattern observed from {pattern.first_seen or 'N/A'} to {pattern.last_seen or 'N/A'}.

"""

        if pattern.skill_candidate:
            content += """### ✨ Skill Candidate

This pattern meets the criteria for skill generation:
- Support ≥ 10 instances
- Confidence ≥ 80%
- Stability ≥ 7 days

"""

        content += f"""## Tags

{', '.join([f'`{tag}`' for tag in pattern.tags]) if pattern.tags else 'None'}

## Exemplar Logs

{len(pattern.exemplar_ids)} example instances:
{chr(10).join([f"- `{eid[:8]}...`" for eid in pattern.exemplar_ids[:5]])}

---

*Generated by ESASS Pattern Recognition Engine*
"""

        return content

    def _export_skills(self, skills: List[SkillManifest]):
        """
        Export skill manifests.

        Args:
            skills: List of skills
        """
        for skill in skills:
            safe_name = skill.name.replace(' ', '_').lower()
            filename = f"{safe_name}.md"
            filepath = self.esass_dir / "skills" / filename

            content = self._format_skill(skill)
            filepath.write_text(content, encoding='utf-8')

    def _format_skill(self, skill: SkillManifest) -> str:
        """Format skill as markdown"""
        content = f"""---
skill_id: {skill.skill_id}
name: {skill.name}
version: {skill.version}
genesis_type: {skill.genesis_type}
status: {skill.validation_status}
created: {skill.created_at}
tags: [{', '.join(skill.keywords)}]
---

# Skill: {skill.name}

## Description

{skill.description}

## Lineage

**Genesis Type**: {skill.genesis_type}

**Source Patterns**:
{chr(10).join([f"- [[pattern_{pid[:8]}]]" for pid in skill.source_pattern_ids]) if skill.source_pattern_ids else '- None'}

## Specification

### Triggers

{chr(10).join([f"- `{trigger}`" for trigger in skill.triggers]) if skill.triggers else '- None'}

### Capabilities

{chr(10).join([f"- {cap}" for cap in skill.capabilities]) if skill.capabilities else '- None'}

## Implementation

{skill.implementation_summary}

## Status

**Validation**: {skill.validation_status}
**Usage Count**: {skill.usage_count}
**Success Rate**: {skill.success_rate:.1%}

## Keywords

{', '.join([f"`{kw}`" for kw in skill.keywords]) if skill.keywords else 'None'}

---

*Auto-generated by ESASS Skill Genesis Engine*
*This skill was derived from observed usage patterns.*
"""

        return content

    def _create_index(self, log_count: int, pattern_count: int, skill_count: int):
        """
        Create main index file.

        Args:
            log_count: Number of log entries
            pattern_count: Number of patterns
            skill_count: Number of skills
        """
        filepath = self.esass_dir / "README.md"

        content = f"""---
type: esass-index
last_updated: {datetime.utcnow().isoformat()}
---

# ESASS - Emergent Self-Adaptive Skill System

## Overview

This vault contains auto-generated documentation from the ESASS prototype, demonstrating the core learning loop:

**Observations → Patterns → Skills**

## Current State

- **Observation Logs**: {log_count} entries
- **Detected Patterns**: {pattern_count} patterns
- **Generated Skills**: {skill_count} skills

## Navigation

### 📊 [Observation Logs](logs/)

Daily summaries of captured events (reasoning, tool usage, decisions).

### 🔍 [Detected Patterns](patterns/)

Recurring temporal sequences identified through pattern mining.

### ⚡ [Generated Skills](skills/)

Skill manifests auto-generated from validated patterns.

## How It Works

1. **Observation**: ESASS captures events during Claude Code interactions
2. **Pattern Detection**: Temporal sequence mining identifies recurring patterns
3. **Skill Generation**: Validated patterns are crystallized into skill manifests
4. **Export**: Everything is documented in this Obsidian vault for review

## Statistics

- **Average Pattern Support**: {pattern_count > 0 and f"{log_count / pattern_count:.1f}" or "N/A"}
- **Skill Candidate Rate**: See individual pattern files for candidacy status

---

*This is a prototype demonstrating meta-cognitive learning in AI systems.*
*Generated on {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC*
"""

        filepath.write_text(content, encoding='utf-8')
