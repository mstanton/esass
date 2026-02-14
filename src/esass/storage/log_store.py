"""
Log storage using JSONL format.

Stores observation logs in daily JSONL files for efficient append operations.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from ..config import ESASSConfig, get_data_dir
from ..models import LogEntry
from .interfaces import LogStoreInterface


class LogStore(LogStoreInterface):
    """Manages JSONL log files organized by date"""

    def __init__(self, config: Optional[ESASSConfig] = None):
        # Handle both Path and ESASSConfig
        if isinstance(config, Path):
            self.data_dir = config
        else:
            self.data_dir = get_data_dir(config)
        self.logs_dir = self.data_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_path(self, date: datetime) -> Path:
        """Get log file path for a specific date"""
        filename = f"log_{date.strftime('%Y%m%d')}.jsonl"
        return self.logs_dir / filename

    def _parse_timestamp(self, timestamp) -> datetime:
        """Parse timestamp from string or datetime object"""
        if isinstance(timestamp, datetime):
            return timestamp
        elif isinstance(timestamp, str):
            return datetime.fromisoformat(timestamp)
        else:
            raise ValueError(f"Invalid timestamp type: {type(timestamp)}")

    def save(self, entry: LogEntry) -> None:
        """Alias for append (backward compatibility)"""
        self.append(entry)

    def append(self, entry: LogEntry) -> None:
        """Append a log entry to the appropriate daily file"""
        timestamp = self._parse_timestamp(entry.timestamp)
        log_path = self._get_log_path(timestamp)

        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry.to_dict()) + '\n')

    def append_batch(self, entries: List[LogEntry]) -> None:
        """Append multiple log entries efficiently"""
        # Group by date
        entries_by_date = {}
        for entry in entries:
            timestamp = self._parse_timestamp(entry.timestamp)
            date_key = timestamp.date()
            if date_key not in entries_by_date:
                entries_by_date[date_key] = []
            entries_by_date[date_key].append(entry)

        # Write to each file
        for date, date_entries in entries_by_date.items():
            log_path = self._get_log_path(datetime.combine(date, datetime.min.time()))
            with open(log_path, 'a', encoding='utf-8') as f:
                for entry in date_entries:
                    f.write(json.dumps(entry.to_dict()) + '\n')

    def save_many(self, entries: List[LogEntry]) -> None:
        """Alias for append_batch for backward compatibility"""
        self.append_batch(entries)

    def read_date(self, date: datetime) -> List[LogEntry]:
        """Read all log entries for a specific date"""
        log_path = self._get_log_path(date)
        if not log_path.exists():
            return []

        entries = []
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    entries.append(LogEntry.from_dict(data))
        return entries

    def read_date_range(self, start_date: datetime, end_date: datetime) -> List[LogEntry]:
        """Read all log entries within a date range (inclusive)"""
        all_entries = []
        current_date = start_date.date()
        end = end_date.date()

        while current_date <= end:
            date_entries = self.read_date(datetime.combine(current_date, datetime.min.time()))
            all_entries.extend(date_entries)
            current_date += timedelta(days=1)

        return all_entries

    def read_last_n_days(self, n_days: int) -> List[LogEntry]:
        """Read log entries from the last N days"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=n_days - 1)
        return self.read_date_range(start_date, end_date)

    def read_all(self) -> List[LogEntry]:
        """Read all log entries from all files"""
        all_entries = []
        for log_file in sorted(self.logs_dir.glob("log_*.jsonl")):
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        all_entries.append(LogEntry.from_dict(data))
        return all_entries

    def load_all(self) -> List[LogEntry]:
        """Alias for read_all for backward compatibility"""
        return self.read_all()

    def get_session_logs(self, session_id: str) -> List[LogEntry]:
        """Get all log entries for a specific session"""
        all_entries = self.read_all()
        return [entry for entry in all_entries if entry.session_id == session_id]

    def count_entries(self) -> int:
        """Count total number of log entries"""
        count = 0
        for log_file in self.logs_dir.glob("log_*.jsonl"):
            with open(log_file, 'r', encoding='utf-8') as f:
                count += sum(1 for line in f if line.strip())
        return count

    def get_date_range(self) -> tuple[Optional[datetime], Optional[datetime]]:
        """Get the date range of available logs"""
        log_files = sorted(self.logs_dir.glob("log_*.jsonl"))
        if not log_files:
            return None, None

        first_file = log_files[0]
        last_file = log_files[-1]

        # Extract dates from filenames
        def parse_date_from_filename(path: Path) -> datetime:
            date_str = path.stem.replace('log_', '')
            return datetime.strptime(date_str, '%Y%m%d')

        start_date = parse_date_from_filename(first_file)
        end_date = parse_date_from_filename(last_file)

        return start_date, end_date

    def clear_all(self) -> None:
        """Delete all log files (use with caution!)"""
        for log_file in self.logs_dir.glob("log_*.jsonl"):
            log_file.unlink()

    def get_stats(self) -> dict:
        """Get statistics about stored logs"""
        all_entries = self.read_all()
        unique_sessions = set(entry.session_id for entry in all_entries)

        start_date, end_date = self.get_date_range()

        return {
            "total_events": len(all_entries),
            "total_sessions": len(unique_sessions),
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "log_files": len(list(self.logs_dir.glob("log_*.jsonl")))
        }
