"""
Skill storage using JSON format.

Stores generated skill manifests with metadata and validation status.
"""

import json
from pathlib import Path
from typing import List, Optional

from ..config import ESASSConfig, get_data_dir
from ..models import SkillManifest
from .interfaces import SkillStoreInterface


class SkillStore(SkillStoreInterface):
    """Manages skill manifest storage in JSON files"""

    def __init__(self, config: Optional[ESASSConfig] = None):
        # Handle both Path and ESASSConfig
        if isinstance(config, Path):
            self.data_dir = config
        else:
            self.data_dir = get_data_dir(config)
        self.skills_dir = self.data_dir / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def _get_skill_path(self, skill_id: str) -> Path:
        """Get file path for a specific skill"""
        return self.skills_dir / f"{skill_id}.json"

    def save(self, skill: SkillManifest) -> None:
        """Save a skill manifest to storage"""
        skill_path = self._get_skill_path(skill.skill_id)
        with open(skill_path, 'w', encoding='utf-8') as f:
            json.dump(skill.to_dict(), f, indent=2)

    def save_batch(self, skills: List[SkillManifest]) -> None:
        """Save multiple skill manifests"""
        for skill in skills:
            self.save(skill)

    def save_many(self, skills: List[SkillManifest]) -> None:
        """Alias for save_batch for backward compatibility"""
        self.save_batch(skills)

    def load(self, skill_id: str) -> Optional[SkillManifest]:
        """Load a specific skill by ID"""
        skill_path = self._get_skill_path(skill_id)
        if not skill_path.exists():
            return None

        with open(skill_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return SkillManifest.from_dict(data)

    def load_all(self) -> List[SkillManifest]:
        """Load all skills from storage"""
        skills = []
        for skill_file in sorted(self.skills_dir.glob("*.json")):
            try:
                with open(skill_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    skills.append(SkillManifest.from_dict(data))
            except (json.JSONDecodeError, ValueError) as e:
                # Skip malformed or empty files
                print(f"Warning: Skipping malformed file {skill_file.name}: {e}")
                continue
        return skills

    def load_by_status(self, status: str) -> List[SkillManifest]:
        """Load skills with a specific validation status"""
        all_skills = self.load_all()
        return [s for s in all_skills if s.validation_status == status]

    def load_pending(self) -> List[SkillManifest]:
        """Load skills pending validation"""
        return self.load_by_status("pending")

    def load_validated(self) -> List[SkillManifest]:
        """Load validated skills"""
        return self.load_by_status("validated")

    def update(self, skill: SkillManifest) -> None:
        """Update an existing skill (same as save)"""
        self.save(skill)

    def update_validation_status(self, skill_id: str, status: str) -> bool:
        """Update the validation status of a skill"""
        skill = self.load(skill_id)
        if skill is None:
            return False

        skill.validation_status = status
        self.save(skill)
        return True

    def delete(self, skill_id: str) -> bool:
        """Delete a skill from storage"""
        skill_path = self._get_skill_path(skill_id)
        if skill_path.exists():
            skill_path.unlink()
            return True
        return False

    def exists(self, skill_id: str) -> bool:
        """Check if a skill exists in storage"""
        return self._get_skill_path(skill_id).exists()

    def count(self) -> int:
        """Count total number of skills"""
        return len(list(self.skills_dir.glob("*.json")))

    def count_by_status(self, status: str) -> int:
        """Count skills with a specific status"""
        return len(self.load_by_status(status))

    def get_by_pattern(self, pattern_id: str) -> List[SkillManifest]:
        """Find skills generated from a specific pattern"""
        all_skills = self.load_all()
        return [
            s for s in all_skills
            if pattern_id in s.source_pattern_ids
        ]

    def get_by_capability(self, capability: str) -> List[SkillManifest]:
        """Find skills with a specific capability"""
        all_skills = self.load_all()
        return [
            s for s in all_skills
            if capability in s.capabilities
        ]

    def clear_all(self) -> None:
        """Delete all skills (use with caution!)"""
        for skill_file in self.skills_dir.glob("*.json"):
            skill_file.unlink()

    def export_summary(self) -> dict:
        """Export summary statistics about stored skills"""
        skills = self.load_all()
        if not skills:
            return {
                "total_skills": 0,
                "pending": 0,
                "validated": 0,
                "rejected": 0,
                "unique_capabilities": 0
            }

        all_capabilities = set()
        for skill in skills:
            all_capabilities.update(skill.capabilities)

        status_counts = {
            "pending": len([s for s in skills if s.validation_status == "pending"]),
            "validated": len([s for s in skills if s.validation_status == "validated"]),
            "rejected": len([s for s in skills if s.validation_status == "rejected"])
        }

        return {
            "total_skills": len(skills),
            "by_status": status_counts,
            "unique_capabilities": len(all_capabilities),
            "capabilities": sorted(all_capabilities)
        }

    def get_stats(self) -> dict:
        """Get statistics about stored skills (alias for export_summary)"""
        return self.export_summary()
