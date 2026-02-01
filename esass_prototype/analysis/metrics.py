"""
Pattern quality metrics calculation.

Provides functions for computing various pattern quality metrics.
"""

from typing import List
from esass_prototype.models import PatternDefinition, PatternQualityMetrics


def calculate_pattern_quality(pattern: PatternDefinition) -> PatternQualityMetrics:
    """
    Calculate comprehensive quality metrics for a pattern.

    Args:
        pattern: PatternDefinition to analyze

    Returns:
        PatternQualityMetrics object
    """
    metrics = PatternQualityMetrics(
        support=pattern.support,
        confidence=pattern.confidence,
        stability_days=pattern.stability_days
    )

    # Calculate lift (how surprising is this pattern vs. random)
    # Simplified: lift = confidence (baseline assumed to be uniform)
    metrics.lift = pattern.confidence

    # Calculate coherence (how internally consistent)
    # Simplified: higher support with high confidence = more coherent
    metrics.coherence = min(1.0, (pattern.support / 20.0) * pattern.confidence)

    # Calculate distinctiveness (separation from other patterns)
    # Simplified: longer sequences are more distinctive
    metrics.distinctiveness = min(1.0, len(pattern.sequence) / 5.0)

    return metrics


def evaluate_skill_candidacy(pattern: PatternDefinition) -> bool:
    """
    Evaluate if a pattern meets skill candidacy criteria.

    Criteria from §6.2 of specification:
    - Support ≥ 10 instances
    - Confidence ≥ 0.8
    - Stability ≥ 7 days

    Args:
        pattern: PatternDefinition to evaluate

    Returns:
        True if pattern is a skill candidate
    """
    return (
        pattern.support >= 10 and
        pattern.confidence >= 0.8 and
        pattern.stability_days >= 7
    )


def rank_patterns(patterns: List[PatternDefinition]) -> List[PatternDefinition]:
    """
    Rank patterns by quality metrics.

    Ranking score = (support * 0.4) + (confidence * 100 * 0.3) + (stability_days * 0.3)

    Args:
        patterns: List of patterns to rank

    Returns:
        Sorted list (highest quality first)
    """
    def score(p: PatternDefinition) -> float:
        return (
            (p.support * 0.4) +
            (p.confidence * 100 * 0.3) +
            (p.stability_days * 0.3)
        )

    return sorted(patterns, key=score, reverse=True)
