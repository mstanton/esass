"""MCP Status Snapshot Writer.

Periodically writes a JSON snapshot of MCP server state to a file
that the dashboard can read. Updated every ~5 seconds by a background
task in the MCP server.
"""

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_data_dir() -> Path:
    """Get the ESASS data directory."""
    return Path(
        os.environ.get("ESASS_DATA_DIR", str(Path.home() / ".esass" / "data"))
    )


class MCPStatusWriter:
    """Writes MCP server status to JSON for dashboard consumption.

    Uses atomic write (write to temp file, then rename) to avoid
    the dashboard reading a partially-written file.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or _get_data_dir()
        self.mcp_dir = self.data_dir / "mcp"
        self.mcp_dir.mkdir(parents=True, exist_ok=True)
        self.status_file = self.mcp_dir / "status.json"

    def write_status(
        self,
        availability: Dict[str, bool],
        circuit_breakers: Dict[str, Dict[str, Any]],
        cache_stats: Dict[str, Dict[str, Any]],
        rate_limit: Dict[str, Any],
        session_summary: Dict[str, Any],
        tier_breakdown: Dict[str, int],
        adaptive_overrides: List[Dict[str, Any]],
    ) -> None:
        """Write complete status snapshot.

        Args:
            availability: Tier name -> available bool
            circuit_breakers: Client name -> {state, failure_count, ...}
            cache_stats: Client name -> {size, max_size, hit_rate, ...}
            rate_limit: {available_tokens, capacity, rate_per_second}
            session_summary: {total_executions, total_cost, total_savings, ...}
            tier_breakdown: Tier name -> execution count
            adaptive_overrides: List of active tier overrides
        """
        status = {
            "updated_at": datetime.now().isoformat(),
            "availability": availability,
            "circuit_breakers": circuit_breakers,
            "cache": cache_stats,
            "rate_limit": rate_limit,
            "costs": {
                "session_executions": session_summary.get("total_executions", 0),
                "session_cost": session_summary.get("total_cost", 0.0),
                "session_savings": session_summary.get("total_savings", 0.0),
                "savings_percentage": session_summary.get("savings_percentage", 0.0),
            },
            "tier_breakdown": tier_breakdown,
            "adaptive_overrides": adaptive_overrides,
        }

        try:
            # Atomic write: write to temp file then rename
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self.mcp_dir), suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(status, f, indent=2, default=str)
                # On Windows, need to remove target first
                if self.status_file.exists():
                    self.status_file.unlink()
                os.rename(tmp_path, str(self.status_file))
            except Exception:
                # Clean up temp file on error
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            logger.debug(f"Failed to write MCP status: {e}")

    def remove_status(self) -> None:
        """Remove status file (on server shutdown)."""
        try:
            if self.status_file.exists():
                self.status_file.unlink()
        except Exception:
            pass
