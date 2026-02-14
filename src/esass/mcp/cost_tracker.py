"""Cost tracking and analytics for 3-tier LLM execution.

Provides:
- Per-execution cost logging with tier decisions
- Cumulative cost savings analytics
- Success rate tracking by tier
- Daily/weekly/monthly cost reports
"""

import json
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from esass.mcp.mcp_config import Tier

logger = logging.getLogger(__name__)


# Cost per 1K tokens (approximate, as of 2024)
COST_PER_1K_TOKENS = {
    Tier.LOCAL: 0.0001,      # ~$0 (only electricity)
    Tier.HUGGINGFACE: 0.001,  # ~10x cheaper than Claude
    Tier.CLAUDE: 0.015,       # Opus pricing
}


@dataclass
class ExecutionLog:
    """Single execution record."""
    timestamp: float
    skill_name: str
    tier_requested: str
    tier_used: str
    fallback_used: bool
    success: bool
    tokens_used: int
    latency_ms: float
    cost_actual: float
    cost_if_claude: float
    savings: float
    error: Optional[str] = None
    routing_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionLog":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class TierStats:
    """Statistics for a single tier."""
    executions: int = 0
    successes: int = 0
    failures: int = 0
    fallback_to: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    total_tokens: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    cost_savings: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.executions == 0:
            return 0.0
        return self.successes / self.executions

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if self.executions == 0:
            return 0.0
        return self.total_latency_ms / self.executions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "executions": self.executions,
            "successes": self.successes,
            "failures": self.failures,
            "fallback_to": dict(self.fallback_to),
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 6),
            "total_latency_ms": round(self.total_latency_ms, 2),
            "cost_savings": round(self.cost_savings, 6),
            "success_rate": round(self.success_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
        }


@dataclass
class DailyReport:
    """Daily cost report."""
    date: str
    total_executions: int = 0
    tier_breakdown: Dict[str, int] = field(default_factory=dict)
    total_cost: float = 0.0
    cost_if_all_claude: float = 0.0
    total_savings: float = 0.0
    savings_percentage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "date": self.date,
            "total_executions": self.total_executions,
            "tier_breakdown": self.tier_breakdown,
            "total_cost": round(self.total_cost, 4),
            "cost_if_all_claude": round(self.cost_if_all_claude, 4),
            "total_savings": round(self.total_savings, 4),
            "savings_percentage": round(self.savings_percentage, 2),
        }


class CostTracker:
    """Tracks execution costs and provides analytics.

    Features:
    - Per-execution logging with tier decisions
    - Cumulative statistics by tier
    - Daily cost reports
    - Savings calculation (local vs Claude)
    - Persistence to JSON file
    - Memory-bounded execution log (configurable max size)
    """

    def __init__(
        self,
        data_dir: str = "./data/cost_tracking",
        auto_save_interval: int = 10,  # Save every N executions
        max_memory_logs: int = 1000,   # Max logs to keep in memory
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.auto_save_interval = auto_save_interval
        self.max_memory_logs = max_memory_logs
        self._executions_since_save = 0

        # Current session stats
        self.session_start = time.time()
        self.execution_logs: List[ExecutionLog] = []
        self.tier_stats: Dict[Tier, TierStats] = {
            Tier.LOCAL: TierStats(),
            Tier.HUGGINGFACE: TierStats(),
            Tier.CLAUDE: TierStats(),
        }

        # Load historical data
        self._load_historical_stats()

    def _get_log_file(self, date: Optional[datetime] = None) -> Path:
        """Get log file path for a given date."""
        if date is None:
            date = datetime.now()
        return self.data_dir / f"executions_{date.strftime('%Y-%m-%d')}.jsonl"

    def _get_stats_file(self) -> Path:
        """Get cumulative stats file path."""
        return self.data_dir / "cumulative_stats.json"

    def _load_historical_stats(self) -> None:
        """Load historical cumulative stats."""
        stats_file = self._get_stats_file()
        if stats_file.exists():
            try:
                with open(stats_file, "r") as f:
                    data = json.load(f)

                for tier_name, stats_data in data.get("tier_stats", {}).items():
                    tier = Tier(tier_name)
                    if tier in self.tier_stats:
                        self.tier_stats[tier].executions = stats_data.get("executions", 0)
                        self.tier_stats[tier].successes = stats_data.get("successes", 0)
                        self.tier_stats[tier].failures = stats_data.get("failures", 0)
                        self.tier_stats[tier].total_tokens = stats_data.get("total_tokens", 0)
                        self.tier_stats[tier].total_cost = stats_data.get("total_cost", 0.0)
                        self.tier_stats[tier].total_latency_ms = stats_data.get("total_latency_ms", 0.0)
                        self.tier_stats[tier].cost_savings = stats_data.get("cost_savings", 0.0)
                        self.tier_stats[tier].fallback_to = defaultdict(
                            int, stats_data.get("fallback_to", {})
                        )

                logger.info(f"Loaded historical stats from {stats_file}")

            except Exception as e:
                logger.warning(f"Failed to load historical stats: {e}")

    def _save_stats(self) -> None:
        """Save cumulative stats to disk."""
        stats_file = self._get_stats_file()
        try:
            data = {
                "updated_at": datetime.now().isoformat(),
                "tier_stats": {
                    tier.value: stats.to_dict()
                    for tier, stats in self.tier_stats.items()
                },
            }
            with open(stats_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save stats: {e}")

    def _append_execution_log(self, log: ExecutionLog) -> None:
        """Append execution log to daily file."""
        log_file = self._get_log_file()
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(log.to_dict()) + "\n")

        except Exception as e:
            logger.error(f"Failed to append execution log: {e}")

    def log_execution(
        self,
        skill_name: str,
        tier_requested: Tier,
        tier_used: Tier,
        fallback_used: bool,
        success: bool,
        tokens_used: int,
        latency_ms: float,
        error: Optional[str] = None,
        routing_reason: Optional[str] = None,
    ) -> ExecutionLog:
        """Log a skill execution with cost calculation.

        Args:
            skill_name: Name of the executed skill
            tier_requested: Original routing decision
            tier_used: Actual tier used (may differ due to fallback)
            fallback_used: Whether fallback was triggered
            success: Whether execution succeeded
            tokens_used: Number of tokens consumed
            latency_ms: Execution latency in milliseconds
            error: Error message if failed
            routing_reason: Reason for routing decision

        Returns:
            ExecutionLog record
        """
        # Calculate costs
        cost_actual = (tokens_used / 1000) * COST_PER_1K_TOKENS[tier_used]
        cost_if_claude = (tokens_used / 1000) * COST_PER_1K_TOKENS[Tier.CLAUDE]
        savings = cost_if_claude - cost_actual

        # Create log record
        log = ExecutionLog(
            timestamp=time.time(),
            skill_name=skill_name,
            tier_requested=tier_requested.value,
            tier_used=tier_used.value,
            fallback_used=fallback_used,
            success=success,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            cost_actual=cost_actual,
            cost_if_claude=cost_if_claude,
            savings=savings,
            error=error,
            routing_reason=routing_reason,
        )

        # Store in memory (with bounded size)
        self.execution_logs.append(log)

        # Trim if exceeding max memory logs
        if len(self.execution_logs) > self.max_memory_logs:
            # Keep most recent logs
            self.execution_logs = self.execution_logs[-self.max_memory_logs:]

        # Update tier stats
        stats = self.tier_stats[tier_used]
        stats.executions += 1
        stats.total_tokens += tokens_used
        stats.total_cost += cost_actual
        stats.total_latency_ms += latency_ms
        stats.cost_savings += savings

        if success:
            stats.successes += 1
        else:
            stats.failures += 1

        # Track fallbacks
        if fallback_used and tier_requested != tier_used:
            self.tier_stats[tier_requested].fallback_to[tier_used.value] += 1

        # Persist
        self._append_execution_log(log)
        self._executions_since_save += 1

        if self._executions_since_save >= self.auto_save_interval:
            self._save_stats()
            self._executions_since_save = 0

        return log

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session."""
        session_duration = time.time() - self.session_start
        total_executions = len(self.execution_logs)

        # Calculate session totals
        session_cost = sum(log.cost_actual for log in self.execution_logs)
        session_savings = sum(log.savings for log in self.execution_logs)
        session_tokens = sum(log.tokens_used for log in self.execution_logs)

        # Tier breakdown for session
        session_tier_counts = defaultdict(int)
        for log in self.execution_logs:
            session_tier_counts[log.tier_used] += 1

        return {
            "session_duration_seconds": round(session_duration, 2),
            "total_executions": total_executions,
            "tier_breakdown": dict(session_tier_counts),
            "total_cost": round(session_cost, 6),
            "total_savings": round(session_savings, 6),
            "total_tokens": session_tokens,
            "savings_percentage": round(
                (session_savings / (session_cost + session_savings)) * 100
                if (session_cost + session_savings) > 0 else 0,
                2
            ),
        }

    def get_tier_summary(self) -> Dict[str, Any]:
        """Get comprehensive tier statistics."""
        total_executions = sum(s.executions for s in self.tier_stats.values())
        total_cost = sum(s.total_cost for s in self.tier_stats.values())
        total_savings = sum(s.cost_savings for s in self.tier_stats.values())

        return {
            "total_executions": total_executions,
            "total_cost": round(total_cost, 4),
            "total_savings": round(total_savings, 4),
            "savings_percentage": round(
                (total_savings / (total_cost + total_savings)) * 100
                if (total_cost + total_savings) > 0 else 0,
                2
            ),
            "tiers": {
                tier.value: stats.to_dict()
                for tier, stats in self.tier_stats.items()
            },
        }

    def get_daily_report(self, date: Optional[datetime] = None) -> DailyReport:
        """Generate a daily cost report."""
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")
        log_file = self._get_log_file(date)

        report = DailyReport(date=date_str)

        if not log_file.exists():
            return report

        try:
            tier_breakdown = defaultdict(int)
            with open(log_file, "r") as f:
                for line in f:
                    if line.strip():
                        log_data = json.loads(line)
                        report.total_executions += 1
                        tier_breakdown[log_data["tier_used"]] += 1
                        report.total_cost += log_data["cost_actual"]
                        report.cost_if_all_claude += log_data["cost_if_claude"]
                        report.total_savings += log_data["savings"]

            report.tier_breakdown = dict(tier_breakdown)
            if report.cost_if_all_claude > 0:
                report.savings_percentage = (
                    report.total_savings / report.cost_if_all_claude
                ) * 100

        except Exception as e:
            logger.error(f"Failed to generate daily report: {e}")

        return report

    def get_weekly_report(self) -> List[DailyReport]:
        """Generate reports for the past 7 days."""
        reports = []
        for i in range(7):
            date = datetime.now() - timedelta(days=i)
            reports.append(self.get_daily_report(date))
        return reports

    def get_cost_projection(self, daily_executions: int = 100) -> Dict[str, Any]:
        """Project monthly costs based on current tier distribution."""
        tier_summary = self.get_tier_summary()
        total_executions = tier_summary["total_executions"]

        if total_executions == 0:
            return {
                "message": "No execution data yet",
                "projected_monthly_cost": 0,
                "projected_monthly_savings": 0,
            }

        # Calculate average tokens per execution
        avg_tokens = sum(
            s.total_tokens for s in self.tier_stats.values()
        ) / total_executions if total_executions > 0 else 500

        # Calculate tier distribution
        tier_distribution = {
            tier.value: stats.executions / total_executions if total_executions > 0 else 0
            for tier, stats in self.tier_stats.items()
        }

        # Project monthly costs
        monthly_executions = daily_executions * 30

        projected_cost = 0.0
        projected_cost_if_claude = 0.0

        for tier, pct in tier_distribution.items():
            tier_executions = monthly_executions * pct
            tier_tokens = tier_executions * avg_tokens
            projected_cost += (tier_tokens / 1000) * COST_PER_1K_TOKENS[Tier(tier)]
            projected_cost_if_claude += (tier_tokens / 1000) * COST_PER_1K_TOKENS[Tier.CLAUDE]

        return {
            "assumptions": {
                "daily_executions": daily_executions,
                "avg_tokens_per_execution": round(avg_tokens),
                "tier_distribution": {k: round(v * 100, 1) for k, v in tier_distribution.items()},
            },
            "projected_monthly_cost": round(projected_cost, 2),
            "projected_cost_if_all_claude": round(projected_cost_if_claude, 2),
            "projected_monthly_savings": round(projected_cost_if_claude - projected_cost, 2),
            "projected_savings_percentage": round(
                ((projected_cost_if_claude - projected_cost) / projected_cost_if_claude) * 100
                if projected_cost_if_claude > 0 else 0,
                1
            ),
        }

    def flush(self) -> None:
        """Force save all stats to disk."""
        self._save_stats()
        self._executions_since_save = 0


# Singleton instance
_tracker: Optional[CostTracker] = None


def get_cost_tracker(data_dir: Optional[str] = None) -> CostTracker:
    """Get the global cost tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = CostTracker(
            data_dir=data_dir or os.environ.get(
                "COST_TRACKING_DIR",
                "./data/cost_tracking"
            )
        )
    return _tracker
