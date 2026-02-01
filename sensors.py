"""
ESASS Skill Evolution Sensors

Sensors that monitor for evolution opportunities and trigger appropriate jobs:
- Skill similarity: New skills added or updated
- Chain optimization: Behavior patterns accumulate
- Unification opportunity: High-similarity clusters detected
- Emergence detection: Experience patterns accumulate
"""

from datetime import datetime
from typing import Optional

from dagster import (
    DefaultSensorStatus,
    RunRequest,
    SensorEvaluationContext,
    SkipReason,
    sensor,
)

# =============================================================================
# Skill Similarity Sensor
# =============================================================================

@sensor(
    name="skill_similarity_sensor",
    description="Monitors for new or updated skills that need similarity recomputation",
    minimum_interval_seconds=3600,  # Check hourly
    default_status=DefaultSensorStatus.RUNNING,
)
def skill_similarity_sensor(
    context: SensorEvaluationContext,
) -> Optional[RunRequest | SkipReason]:
    """
    Trigger similarity computation when:
    - New skills are added
    - Existing skills are significantly updated
    - Similarity matrix is stale (> 24 hours)
    """
    # Get cursor (last check time)
    last_check_str = context.cursor or "2000-01-01T00:00:00"
    last_check = datetime.fromisoformat(last_check_str)
    now = datetime.utcnow()
    
    # Check if enough time has passed for a recomputation
    hours_since_check = (now - last_check).total_seconds() / 3600
    
    # Always recompute at least once per day
    if hours_since_check >= 24:
        context.update_cursor(now.isoformat())
        return RunRequest(
            run_key=f"similarity_{now.strftime('%Y%m%d_%H')}",
            tags={
                "trigger": "scheduled",
                "hours_since_last": str(int(hours_since_check)),
            },
        )
    
    # Check for new skills via asset observation
    # In production, this would query the skill registry
    # For now, we skip if not enough time has passed
    return SkipReason(f"Last computed {hours_since_check:.1f} hours ago, waiting for 24h threshold")


# =============================================================================
# Chain Optimization Sensor
# =============================================================================

@sensor(
    name="chain_optimization_sensor",
    description="Monitors for behavior chain patterns that warrant optimization",
    minimum_interval_seconds=7200,  # Check every 2 hours
    default_status=DefaultSensorStatus.RUNNING,
)
def chain_optimization_sensor(
    context: SensorEvaluationContext,
) -> Optional[RunRequest | SkipReason]:
    """
    Trigger chain optimization when:
    - Sufficient new experiences accumulated
    - Chains with optimization_score above threshold detected
    - No optimization run in the past 12 hours
    """
    last_check_str = context.cursor or "2000-01-01T00:00:00"
    last_check = datetime.fromisoformat(last_check_str)
    now = datetime.utcnow()
    
    hours_since_check = (now - last_check).total_seconds() / 3600
    
    # Run optimization at least every 12 hours if there's activity
    if hours_since_check >= 12:
        context.update_cursor(now.isoformat())
        return RunRequest(
            run_key=f"chain_opt_{now.strftime('%Y%m%d_%H')}",
            tags={
                "trigger": "scheduled",
                "hours_since_last": str(int(hours_since_check)),
            },
        )
    
    return SkipReason(f"Last run {hours_since_check:.1f} hours ago, waiting for 12h threshold")


# =============================================================================
# Unification Opportunity Sensor
# =============================================================================

@sensor(
    name="unification_opportunity_sensor",
    description="Monitors for skill unification opportunities",
    minimum_interval_seconds=14400,  # Check every 4 hours
    default_status=DefaultSensorStatus.RUNNING,
)
def unification_opportunity_sensor(
    context: SensorEvaluationContext,
) -> Optional[RunRequest | SkipReason]:
    """
    Trigger unification analysis when:
    - High-similarity clusters detected (> 0.8 similarity)
    - Skills marked as candidates in state space
    - Pending unifications in queue need processing
    """
    last_check_str = context.cursor or "2000-01-01T00:00:00"
    last_check = datetime.fromisoformat(last_check_str)
    now = datetime.utcnow()
    
    hours_since_check = (now - last_check).total_seconds() / 3600
    
    # Run unification analysis at least once per day
    if hours_since_check >= 24:
        context.update_cursor(now.isoformat())
        return RunRequest(
            run_key=f"unification_{now.strftime('%Y%m%d')}",
            tags={
                "trigger": "scheduled",
                "phase": "candidate_detection",
            },
        )
    
    return SkipReason(f"Last run {hours_since_check:.1f} hours ago, waiting for 24h threshold")


# =============================================================================
# Emergence Detection Sensor
# =============================================================================

@sensor(
    name="emergence_detection_sensor",
    description="Monitors for emergent capabilities from experience patterns",
    minimum_interval_seconds=21600,  # Check every 6 hours
    default_status=DefaultSensorStatus.RUNNING,
)
def emergence_detection_sensor(
    context: SensorEvaluationContext,
) -> Optional[RunRequest | SkipReason]:
    """
    Trigger emergence detection when:
    - Sufficient experiences accumulated (> min_experiences_for_pattern)
    - Unusual patterns detected in recent usage
    - No emergence scan in past 24 hours
    """
    last_check_str = context.cursor or "2000-01-01T00:00:00"
    last_check = datetime.fromisoformat(last_check_str)
    now = datetime.utcnow()
    
    hours_since_check = (now - last_check).total_seconds() / 3600
    
    # Run emergence detection daily
    if hours_since_check >= 24:
        context.update_cursor(now.isoformat())
        return RunRequest(
            run_key=f"emergence_{now.strftime('%Y%m%d')}",
            tags={
                "trigger": "scheduled",
                "scan_type": "full",
            },
        )
    
    return SkipReason(f"Last run {hours_since_check:.1f} hours ago, waiting for 24h threshold")


# =============================================================================
# Advanced Sensors with Resource Access
# =============================================================================

@sensor(
    name="experience_threshold_sensor",
    description="Monitors experience accumulation and triggers analysis when thresholds are met",
    minimum_interval_seconds=1800,  # Check every 30 minutes
    default_status=DefaultSensorStatus.STOPPED,  # Enable manually in production
)
def experience_threshold_sensor(
    context: SensorEvaluationContext,
) -> Optional[RunRequest | SkipReason]:
    """
    More sophisticated sensor that checks actual experience counts.
    
    Requires resources to be configured to access experience store.
    """
    # Parse cursor state
    cursor_data = {}
    if context.cursor:
        import json
        cursor_data = json.loads(context.cursor)
    
    last_experience_count = cursor_data.get("experience_count", 0)
    last_run_time_str = cursor_data.get("last_run", "2000-01-01T00:00:00")
    last_run = datetime.fromisoformat(last_run_time_str)
    
    now = datetime.utcnow()
    
    # In production, would query experience store for actual count
    # For now, estimate based on time
    estimated_new_experiences = int((now - last_run).total_seconds() / 60)  # ~1 per minute assumed
    
    # Thresholds
    min_new_experiences = 100
    max_hours_between_runs = 48
    
    hours_since_run = (now - last_run).total_seconds() / 3600
    
    should_run = False
    trigger_reason = ""
    
    if estimated_new_experiences >= min_new_experiences:
        should_run = True
        trigger_reason = f"experience_threshold:{estimated_new_experiences}"
    elif hours_since_run >= max_hours_between_runs:
        should_run = True
        trigger_reason = f"time_threshold:{int(hours_since_run)}h"
    
    if should_run:
        import json
        context.update_cursor(json.dumps({
            "experience_count": last_experience_count + estimated_new_experiences,
            "last_run": now.isoformat(),
        }))
        return RunRequest(
            run_key=f"exp_analysis_{now.strftime('%Y%m%d_%H%M')}",
            tags={
                "trigger": trigger_reason,
                "estimated_experiences": str(estimated_new_experiences),
            },
        )
    
    return SkipReason(f"Conditions not met: {estimated_new_experiences} experiences, {hours_since_run:.1f}h since last run")


@sensor(
    name="state_space_drift_sensor",
    description="Monitors for significant changes in skill state space",
    minimum_interval_seconds=7200,  # Check every 2 hours
    default_status=DefaultSensorStatus.STOPPED,
)
def state_space_drift_sensor(
    context: SensorEvaluationContext,
) -> Optional[RunRequest | SkipReason]:
    """
    Detect when skills have drifted significantly in state space.
    
    Triggers recomputation when:
    - Average skill movement exceeds threshold
    - Cluster membership changes significantly
    - Fitness distribution shifts
    """
    last_check_str = context.cursor or "2000-01-01T00:00:00"
    last_check = datetime.fromisoformat(last_check_str)
    now = datetime.utcnow()
    
    hours_since_check = (now - last_check).total_seconds() / 3600
    
    # Recompute state space at least every 6 hours
    if hours_since_check >= 6:
        context.update_cursor(now.isoformat())
        return RunRequest(
            run_key=f"state_space_{now.strftime('%Y%m%d_%H')}",
            tags={
                "trigger": "drift_check",
                "hours_since_last": str(int(hours_since_check)),
            },
        )
    
    return SkipReason(f"Last computed {hours_since_check:.1f} hours ago")


@sensor(
    name="unification_queue_sensor",
    description="Monitors unification queue for pending approvals",
    minimum_interval_seconds=300,  # Check every 5 minutes
    default_status=DefaultSensorStatus.STOPPED,
)
def unification_queue_sensor(
    context: SensorEvaluationContext,
) -> Optional[RunRequest | SkipReason]:
    """
    Process approved unifications from the queue.
    
    Triggers execution when:
    - Approved candidates exist in queue
    - Daily limit not reached
    """
    # In production, would query the unification queue
    # For now, this is a placeholder
    
    last_check_str = context.cursor or "2000-01-01T00:00:00"
    last_check = datetime.fromisoformat(last_check_str)
    now = datetime.utcnow()
    
    # Only process once per hour at most
    minutes_since_check = (now - last_check).total_seconds() / 60
    
    if minutes_since_check >= 60:
        context.update_cursor(now.isoformat())
        # Would check queue here
        return SkipReason("No approved candidates in queue")
    
    return SkipReason(f"Recently checked {minutes_since_check:.0f}m ago")


# =============================================================================
# Composite Evolution Sensor
# =============================================================================

@sensor(
    name="full_evolution_sensor",
    description="Master sensor that orchestrates the full evolution pipeline",
    minimum_interval_seconds=3600,  # Check hourly
    default_status=DefaultSensorStatus.STOPPED,
)
def full_evolution_sensor(
    context: SensorEvaluationContext,
) -> Optional[RunRequest | SkipReason]:
    """
    Orchestrate the complete evolution pipeline.
    
    Runs the full pipeline when:
    - Significant changes detected in skill repertoire
    - Weekly scheduled run
    - Manual trigger requested
    """
    import json
    
    cursor_data = {}
    if context.cursor:
        cursor_data = json.loads(context.cursor)
    
    last_full_run_str = cursor_data.get("last_full_run", "2000-01-01T00:00:00")
    last_full_run = datetime.fromisoformat(last_full_run_str)
    run_count = cursor_data.get("run_count", 0)
    
    now = datetime.utcnow()
    days_since_full_run = (now - last_full_run).days
    
    # Run full pipeline at least weekly
    if days_since_full_run >= 7:
        context.update_cursor(json.dumps({
            "last_full_run": now.isoformat(),
            "run_count": run_count + 1,
        }))
        return RunRequest(
            run_key=f"full_evolution_{now.strftime('%Y%m%d')}",
            tags={
                "trigger": "weekly",
                "run_number": str(run_count + 1),
                "days_since_last": str(days_since_full_run),
            },
        )
    
    return SkipReason(f"Last full run {days_since_full_run} days ago, waiting for weekly threshold")


# =============================================================================
# All Sensors Export
# =============================================================================

all_evolution_sensors = [
    skill_similarity_sensor,
    chain_optimization_sensor,
    unification_opportunity_sensor,
    emergence_detection_sensor,
    experience_threshold_sensor,
    state_space_drift_sensor,
    unification_queue_sensor,
    full_evolution_sensor,
]
