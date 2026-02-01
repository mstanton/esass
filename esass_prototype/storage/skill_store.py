"""
Skill storage using JSON files.

Provides storage and retrieval for skill manifests.
"""

from pathlib import Path
from typing import List, Optional
import json

from esass_prototype.models import SkillManifest


class SkillStore:
    """
    Storage for skill manifests using JSON files.

    Each skill is stored in its own file for easy inspection.
    """

    def __init__(self, data_dir: Path):
        """
        Initialize skill store.

        Args:
            data_dir: Base directory for data storage
        """
        self.data_dir = Path(data_dir)
        self.skills_dir = self.data_dir / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def save(self, skill: SkillManifest):
        """
        Save a skill manifest.

        Args:
            skill: SkillManifest to save
        """
        # Use skill name for filename (sanitized)
        safe_name = skill.name.replace(' ', '_').lower()
        filename = f"{safe_name}_{skill.skill_id[:8]}.json"
        filepath = self.skills_dir / filename

        with open(filepath, 'w') as f:
            f.write(skill.to_json())

    def save_many(self, skills: List[SkillManifest]):
        """
        Save multiple skills.

        Args:
            skills: List of SkillManifest objects
        """
        for skill in skills:
            self.save(skill)

    def load(self, skill_id: str) -> Optional[SkillManifest]:
        """
        Load a specific skill by ID.

        Args:
            skill_id: Skill ID to load (can be short ID)

        Returns:
            SkillManifest if found, None otherwise
        """
        # Search for file containing this ID
        for skill_file in self.skills_dir.glob(f"*{skill_id[:8]}.json"):
            with open(skill_file, 'r') as f:
                return SkillManifest.from_json(f.read())

        return None

    def load_by_name(self, name: str) -> Optional[SkillManifest]:
        """
        Load a skill by name.

        Args:
            name: Skill name

        Returns:
            SkillManifest if found, None otherwise
        """
        safe_name = name.replace(' ', '_').lower()

        for skill_file in self.skills_dir.glob(f"{safe_name}_*.json"):
            with open(skill_file, 'r') as f:
                return SkillManifest.from_json(f.read())

        return None

    def load_all(self) -> List[SkillManifest]:
        """
        Load all skills.

        Returns:
            List of all SkillManifest objects
        """
        skills = []

        for skill_file in self.skills_dir.glob("*.json"):
            with open(skill_file, 'r') as f:
                skills.append(SkillManifest.from_json(f.read()))

        # Sort by created_at
        skills.sort(key=lambda s: s.created_at, reverse=True)

        return skills

    def load_by_status(self, status: str) -> List[SkillManifest]:
        """
        Load skills by validation status.

        Args:
            status: Status to filter by (pending, validated, active, deprecated)

        Returns:
            List of SkillManifest objects with matching status
        """
        all_skills = self.load_all()
        return [s for s in all_skills if s.validation_status == status]

    def load_by_source_pattern(self, pattern_id: str) -> List[SkillManifest]:
        """
        Load skills derived from a specific pattern.

        Args:
            pattern_id: Pattern ID

        Returns:
            List of SkillManifest objects derived from that pattern
        """
        all_skills = self.load_all()
        return [
            s for s in all_skills
            if pattern_id in s.source_pattern_ids or
            pattern_id[:8] in ' '.join(s.source_pattern_ids)
        ]

    def delete(self, skill_id: str) -> bool:
        """
        Delete a skill.

        Args:
            skill_id: Skill ID to delete

        Returns:
            True if deleted, False if not found
        """
        for skill_file in self.skills_dir.glob(f"*{skill_id[:8]}.json"):
            skill_file.unlink()
            return True

        return False

    def update_status(self, skill_id: str, new_status: str) -> bool:
        """
        Update a skill's validation status.

        Args:
            skill_id: Skill ID
            new_status: New status

        Returns:
            True if updated, False if not found
        """
        skill = self.load(skill_id)

        if skill is None:
            return False

        skill.validation_status = new_status
        self.save(skill)
        return True

    def get_stats(self) -> dict:
        """
        Get skill storage statistics.

        Returns:
            Dictionary with stats
        """
        all_skills = self.load_all()

        if not all_skills:
            return {
                "total_skills": 0,
                "by_status": {},
                "by_genesis_type": {}
            }

        by_status = {}
        by_genesis_type = {}

        for skill in all_skills:
            status = skill.validation_status
            by_status[status] = by_status.get(status, 0) + 1

            genesis = skill.genesis_type
            by_genesis_type[genesis] = by_genesis_type.get(genesis, 0) + 1

        return {
            "total_skills": len(all_skills),
            "by_status": by_status,
            "by_genesis_type": by_genesis_type,
            "avg_usage_count": sum(s.usage_count for s in all_skills) / len(all_skills) if all_skills else 0
        }
