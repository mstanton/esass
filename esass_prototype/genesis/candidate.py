"""
Skill candidacy evaluation - determines if patterns are ready for skill generation.

Implements criteria from §6.2 of specification.
"""

from typing import List, Tuple

from esass_prototype.models import PatternDefinition


class SkillCandidacyEvaluator:
    """
    Evaluate if patterns meet skill candidacy criteria.

    Criteria from §6.2:
    - min_support: >= 10 instances
    - min_confidence: >= 0.8
    - min_stability_days: >= 7 days
    """

    def __init__(
        self,
        min_support: int = 10,
        min_confidence: float = 0.8,
        min_stability_days: int = 7
    ):
        """
        Initialize evaluator.

        Args:
            min_support: Minimum pattern instances
            min_confidence: Minimum confidence score
            min_stability_days: Minimum stability period
        """
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_stability_days = min_stability_days

    def evaluate(self, pattern: PatternDefinition) -> Tuple[bool, List[str]]:
        """
        Evaluate if pattern is a skill candidate.

        Args:
            pattern: PatternDefinition to evaluate

        Returns:
            Tuple of (is_candidate, reasons)
            - is_candidate: True if meets all criteria
            - reasons: List of reasons (why it passed or what's blocking)
        """
        reasons = []
        is_candidate = True

        # Check support
        if pattern.support >= self.min_support:
            reasons.append(f"✓ Support: {pattern.support} instances (≥{self.min_support})")
        else:
            reasons.append(f"✗ Support: {pattern.support} instances (<{self.min_support})")
            is_candidate = False

        # Check confidence
        if pattern.confidence >= self.min_confidence:
            reasons.append(f"✓ Confidence: {pattern.confidence:.1%} (≥{self.min_confidence:.0%})")
        else:
            reasons.append(f"✗ Confidence: {pattern.confidence:.1%} (<{self.min_confidence:.0%})")
            is_candidate = False

        # Check stability
        if pattern.stability_days >= self.min_stability_days:
            reasons.append(f"✓ Stability: {pattern.stability_days} days (≥{self.min_stability_days})")
        else:
            reasons.append(f"✗ Stability: {pattern.stability_days} days (<{self.min_stability_days})")
            is_candidate = False

        return is_candidate, reasons

    def filter_candidates(
        self,
        patterns: List[PatternDefinition]
    ) -> List[PatternDefinition]:
        """
        Filter patterns to only those meeting candidacy criteria.

        Args:
            patterns: List of patterns to filter

        Returns:
            List of candidate patterns
        """
        candidates = []

        for pattern in patterns:
            is_candidate, _ = self.evaluate(pattern)
            if is_candidate:
                candidates.append(pattern)

        return candidates

    def get_report(self, patterns: List[PatternDefinition]) -> dict:
        """
        Generate candidacy evaluation report.

        Args:
            patterns: List of patterns to evaluate

        Returns:
            Dictionary with evaluation statistics
        """
        total = len(patterns)
        candidates = 0
        blocking_factors = {
            "support": 0,
            "confidence": 0,
            "stability": 0
        }

        for pattern in patterns:
            is_candidate, reasons = self.evaluate(pattern)

            if is_candidate:
                candidates += 1
            else:
                # Count blocking factors
                for reason in reasons:
                    if "Support" in reason and "✗" in reason:
                        blocking_factors["support"] += 1
                    if "Confidence" in reason and "✗" in reason:
                        blocking_factors["confidence"] += 1
                    if "Stability" in reason and "✗" in reason:
                        blocking_factors["stability"] += 1

        return {
            "total_patterns": total,
            "skill_candidates": candidates,
            "candidate_rate": candidates / total if total > 0 else 0,
            "blocking_factors": blocking_factors
        }
