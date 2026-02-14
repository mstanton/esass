"""
Tracing storage layer.

JSONL-based append-only stores for usage records, evolution events,
and lineage edges.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .models import EvolutionEvent, LineageEdge, UsageRecord


class UsageStore:
    """Daily-partitioned JSONL store for usage records."""

    def __init__(self, base_dir: str = "./data/esass/tracing/usage"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for_date(self, date_str: str) -> Path:
        """Return path for a given YYYYMMDD string."""
        return self.base_dir / f"usage_{date_str}.jsonl"

    @staticmethod
    def _date_key(iso_ts: str) -> str:
        """Extract YYYYMMDD from ISO timestamp."""
        return iso_ts[:10].replace("-", "")

    def append(self, record: UsageRecord) -> None:
        path = self._path_for_date(self._date_key(record.timestamp))
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    def append_batch(self, records: List[UsageRecord]) -> None:
        for record in records:
            self.append(record)

    def read_date(self, date_str: str) -> List[UsageRecord]:
        """Read all records for a YYYYMMDD date."""
        path = self._path_for_date(date_str)
        if not path.exists():
            return []
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(UsageRecord.from_dict(json.loads(line)))
        return records

    def read_date_range(self, start: str, end: str) -> List[UsageRecord]:
        """Read records for a date range (inclusive, YYYYMMDD format)."""
        records = []
        for path in sorted(self.base_dir.glob("usage_*.jsonl")):
            date_part = path.stem.replace("usage_", "")
            if start <= date_part <= end:
                records.extend(self.read_date(date_part))
        return records

    def read_all(self) -> List[UsageRecord]:
        """Read all usage records across all dates."""
        records = []
        for path in sorted(self.base_dir.glob("usage_*.jsonl")):
            date_part = path.stem.replace("usage_", "")
            records.extend(self.read_date(date_part))
        return records

    def read_for_skill(self, skill_id: str) -> List[UsageRecord]:
        """Read all records for a specific skill."""
        return [r for r in self.read_all() if r.skill_id == skill_id]


class EvolutionStore:
    """Per-skill JSONL store for evolution events."""

    def __init__(self, base_dir: str = "./data/esass/tracing/evolution"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for_skill(self, skill_id: str) -> Path:
        safe_id = skill_id.replace("/", "_").replace("\\", "_")
        return self.base_dir / f"evolution_{safe_id}.jsonl"

    def append(self, event: EvolutionEvent) -> None:
        path = self._path_for_skill(event.skill_id)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def read_for_skill(self, skill_id: str) -> List[EvolutionEvent]:
        """Read all evolution events for a skill, ordered by timestamp."""
        path = self._path_for_skill(skill_id)
        if not path.exists():
            return []
        events = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(EvolutionEvent.from_dict(json.loads(line)))
        events.sort(key=lambda e: e.timestamp)
        return events

    def read_all(self) -> List[EvolutionEvent]:
        """Read all evolution events across all skills."""
        events = []
        for path in sorted(self.base_dir.glob("evolution_*.jsonl")):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(EvolutionEvent.from_dict(json.loads(line)))
        events.sort(key=lambda e: e.timestamp)
        return events

    def read_date_range(self, start: str, end: str) -> List[EvolutionEvent]:
        """Read events within ISO date range (YYYY-MM-DD)."""
        all_events = self.read_all()
        return [
            e for e in all_events
            if start <= e.timestamp[:10] <= end
        ]


class LineageStore:
    """Append-only JSONL store for lineage edges."""

    def __init__(self, base_dir: str = "./data/esass/tracing/lineage"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.base_dir / "lineage_edges.jsonl"

    def append(self, edge: LineageEdge) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(edge.to_dict()) + "\n")

    def read_all(self) -> List[LineageEdge]:
        """Read all lineage edges."""
        if not self._path.exists():
            return []
        edges = []
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    edges.append(LineageEdge.from_dict(json.loads(line)))
        return edges

    def read_for_skill(self, skill_id: str) -> List[LineageEdge]:
        """Read all edges involving a skill (source or target)."""
        return [
            e for e in self.read_all()
            if e.source_skill_id == skill_id or e.target_skill_id == skill_id
        ]

    def read_outgoing(self, skill_id: str) -> List[LineageEdge]:
        """Read edges where skill is the source."""
        return [e for e in self.read_all() if e.source_skill_id == skill_id]

    def read_incoming(self, skill_id: str) -> List[LineageEdge]:
        """Read edges where skill is the target."""
        return [e for e in self.read_all() if e.target_skill_id == skill_id]
