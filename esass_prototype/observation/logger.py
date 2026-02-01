"""
Logger for writing observations to storage.

Provides simple interface for capturing and persisting events.
"""

import json
from pathlib import Path
from typing import List

from esass_prototype.models import LogEntry, ObserverState
from esass_prototype.storage.log_store import LogStore


class ObservationLogger:
    """
    Logger for observation events.

    Handles writing events to storage and maintaining observer state.
    """

    def __init__(self, data_dir: Path, state_file: Path = None):
        """
        Initialize logger.

        Args:
            data_dir: Data directory for storage
            state_file: Optional path to state file
        """
        self.log_store = LogStore(data_dir)
        self.state_file = state_file or (Path(data_dir) / "state" / "observer_state.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Load or create state
        self.state = self._load_state()

    def _load_state(self) -> ObserverState:
        """Load observer state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        return ObserverState.from_json(content)
            except (json.JSONDecodeError, ValueError):
                # If state file is corrupted, start fresh
                pass
        return ObserverState()

    def _save_state(self):
        """Save observer state to file"""
        with open(self.state_file, 'w') as f:
            f.write(self.state.to_json())

    def log(self, entry: LogEntry):
        """
        Log a single observation entry.

        Args:
            entry: LogEntry to log
        """
        self.log_store.save(entry)
        self.state.total_events += 1
        self._save_state()

    def log_many(self, entries: List[LogEntry]):
        """
        Log multiple observation entries efficiently.

        Args:
            entries: List of LogEntry objects
        """
        self.log_store.save_many(entries)
        self.state.total_events += len(entries)

        # Count unique sessions
        sessions = set(e.session_id for e in entries)
        self.state.total_sessions += len(sessions)

        self._save_state()

    def start_observation(self):
        """Start observation mode"""
        from datetime import datetime

        self.state.is_enabled = True
        self.state.started_at = datetime.utcnow().isoformat()
        self.state.stopped_at = None
        self._save_state()

    def stop_observation(self):
        """Stop observation mode"""
        from datetime import datetime

        self.state.is_enabled = False
        self.state.stopped_at = datetime.utcnow().isoformat()
        self._save_state()

    def get_state(self) -> ObserverState:
        """Get current observer state"""
        return self.state

    def get_stats(self) -> dict:
        """
        Get observation statistics.

        Returns:
            Dictionary with observation stats
        """
        log_stats = self.log_store.get_stats()

        return {
            "observer_enabled": self.state.is_enabled,
            "total_events": self.state.total_events,
            "total_sessions": self.state.total_sessions,
            "log_stats": log_stats
        }
