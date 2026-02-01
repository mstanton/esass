"""
Log storage using JSON Lines (JSONL) format.

Provides efficient append-only storage for observation logs.
"""

from pathlib import Path
from datetime import datetime
from typing import List, Optional
import json

from esass_prototype.models import LogEntry


class LogStore:
    """
    Storage for observation logs using JSONL format.

    Features:
    - Append-only writes (efficient for streaming)
    - Daily log files for easy management
    - Line-based reading (incremental processing)
    """

    def __init__(self, data_dir: Path):
        """
        Initialize log store.

        Args:
            data_dir: Base directory for data storage
        """
        self.data_dir = Path(data_dir)
        self.logs_dir = self.data_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def save(self, entry: LogEntry):
        """
        Save a single log entry.

        Args:
            entry: LogEntry to save
        """
        # Determine file based on entry timestamp
        date = datetime.fromisoformat(entry.timestamp).date()
        log_file = self.logs_dir / f"{date.isoformat()}.jsonl"

        # Append to file
        with open(log_file, 'a') as f:
            f.write(entry.to_json() + '\n')

    def save_many(self, entries: List[LogEntry]):
        """
        Save multiple log entries efficiently.

        Args:
            entries: List of LogEntry objects
        """
        # Group by date
        entries_by_date = {}
        for entry in entries:
            date = datetime.fromisoformat(entry.timestamp).date()
            if date not in entries_by_date:
                entries_by_date[date] = []
            entries_by_date[date].append(entry)

        # Write to files
        for date, date_entries in entries_by_date.items():
            log_file = self.logs_dir / f"{date.isoformat()}.jsonl"
            with open(log_file, 'a') as f:
                for entry in date_entries:
                    f.write(entry.to_json() + '\n')

    def load_by_date(self, date: datetime.date) -> List[LogEntry]:
        """
        Load all log entries for a specific date.

        Args:
            date: Date to load logs for

        Returns:
            List of LogEntry objects for that date
        """
        log_file = self.logs_dir / f"{date.isoformat()}.jsonl"

        if not log_file.exists():
            return []

        entries = []
        with open(log_file, 'r') as f:
            for line in f:
                if line.strip():
                    entries.append(LogEntry.from_json(line))

        return entries

    def load_by_date_range(
        self,
        start_date: datetime.date,
        end_date: datetime.date
    ) -> List[LogEntry]:
        """
        Load all log entries within a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of all LogEntry objects in range, sorted by timestamp
        """
        all_entries = []

        current_date = start_date
        while current_date <= end_date:
            entries = self.load_by_date(current_date)
            all_entries.extend(entries)
            current_date = current_date.replace(day=current_date.day + 1)

        # Sort by timestamp
        all_entries.sort(key=lambda e: e.timestamp)

        return all_entries

    def load_all(self) -> List[LogEntry]:
        """
        Load all log entries from all files.

        Returns:
            List of all LogEntry objects, sorted by timestamp
        """
        all_entries = []

        for log_file in self.logs_dir.glob("*.jsonl"):
            with open(log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        all_entries.append(LogEntry.from_json(line))

        # Sort by timestamp
        all_entries.sort(key=lambda e: e.timestamp)

        return all_entries

    def load_by_session(self, session_id: str) -> List[LogEntry]:
        """
        Load all log entries for a specific session.

        Args:
            session_id: Session ID to filter by

        Returns:
            List of LogEntry objects for that session
        """
        all_entries = self.load_all()
        return [e for e in all_entries if e.session_id == session_id]

    def get_session_ids(self) -> List[str]:
        """
        Get all unique session IDs.

        Returns:
            List of unique session IDs
        """
        all_entries = self.load_all()
        return list(set(e.session_id for e in all_entries))

    def get_stats(self) -> dict:
        """
        Get storage statistics.

        Returns:
            Dictionary with stats: total_entries, total_sessions, date_range
        """
        all_entries = self.load_all()

        if not all_entries:
            return {
                "total_entries": 0,
                "total_sessions": 0,
                "date_range": None
            }

        timestamps = [datetime.fromisoformat(e.timestamp) for e in all_entries]

        return {
            "total_entries": len(all_entries),
            "total_sessions": len(set(e.session_id for e in all_entries)),
            "date_range": {
                "start": min(timestamps).isoformat(),
                "end": max(timestamps).isoformat()
            }
        }
