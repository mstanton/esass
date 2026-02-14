"""
Insight Probe

Captures "aha moments" - discoveries, connections, and debugging breakthroughs.
Tracks pattern recognition and understanding evolution.
"""

from datetime import datetime
from typing import Optional, List
import re

from .base import FilteringProbe, ProbeContext, LogEntry


class InsightProbe(FilteringProbe):
    """
    Tracks insight and discovery moments.

    Captures:
    - "I see, the issue is actually..."
    - "This explains why..."
    - Pattern recognition moments
    - Debugging breakthroughs
    - Conceptual connections

    Events observed:
    - thinking_block: Insight language and realizations
    """

    # Insight indicator patterns
    INSIGHT_PATTERNS = {
        'realization': {
            'pattern': re.compile(
                r"\b(I see|aha|oh|now I understand|makes sense|that's (it|why)|realized|realize)\b",
                re.I
            ),
            'confidence': 0.9,
            'type': 'realization'
        },
        'causal_discovery': {
            'pattern': re.compile(
                r"\b((this|that) (is|explains) why|because of|caused by|the reason is|root cause)\b",
                re.I
            ),
            'confidence': 0.8,
            'type': 'causal'
        },
        'pattern_recognition': {
            'pattern': re.compile(
                r"\b(pattern|similar to|same (as|pattern)|like (how|when)|analogous|parallel)\b",
                re.I
            ),
            'confidence': 0.7,
            'type': 'pattern'
        },
        'connection': {
            'pattern': re.compile(
                r"\b(connects? to|related to|ties into|links? to|connection between)\b",
                re.I
            ),
            'confidence': 0.7,
            'type': 'connection'
        },
        'breakthrough': {
            'pattern': re.compile(
                r"\b(breakthrough|figured (it )?out|discovered|found (it|the issue|the problem))\b",
                re.I
            ),
            'confidence': 0.9,
            'type': 'breakthrough'
        },
        'correction': {
            'pattern': re.compile(
                r"\b(actually|wait|correction|I was wrong|mistake|incorrectly thought)\b",
                re.I
            ),
            'confidence': 0.8,
            'type': 'correction'
        }
    }

    # Context enrichment patterns
    DOMAIN_PATTERNS = {
        'debugging': re.compile(r"\b(debug|bug|error|issue|problem|fix)\b", re.I),
        'architecture': re.compile(r"\b(architecture|design|structure|pattern|framework)\b", re.I),
        'performance': re.compile(r"\b(performance|optimize|efficiency|speed|slow)\b", re.I),
        'security': re.compile(r"\b(security|vulnerability|exploit|auth|permission)\b", re.I),
        'data_flow': re.compile(r"\b(data flow|pipeline|transform|process)\b", re.I)
    }

    def __init__(self, enabled: bool = True, min_insight_confidence: float = 0.7):
        super().__init__(enabled)
        self.min_insight_confidence = min_insight_confidence
        self._insight_count = 0

    def can_observe(self, event_type: str) -> bool:
        """Observe thinking blocks for insight language"""
        return event_type == 'thinking_block'

    def observe_filtered(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """Detect and log insights"""
        content = context.event_data.get('content', '')

        # Check for insight patterns
        insight_type, confidence = self._detect_insight(content)
        if not insight_type or confidence < self.min_insight_confidence:
            return None

        # Detect domain context
        domain = self._detect_domain(content)

        # Extract the insight itself (try to get key sentence)
        insight_text = self._extract_insight_text(content, insight_type)

        # Detect what was learned
        learning = self._extract_learning(content)

        self._insight_count += 1

        entry = LogEntry(
            event_id=f"insight-{context.session_id}-{self._insight_count}",
            timestamp=context.timestamp,
            event_type="insight",
            event_data={
                'insight_type': insight_type,
                'confidence': confidence,
                'domain': domain,
                'insight': insight_text,
                'learning': learning,
                'full_context': content[:500]  # Include surrounding context
            },
            session_id=context.session_id,
            tags=['insight', insight_type, domain or 'general']
        )

        return [entry]

    def _detect_insight(self, content: str) -> tuple[Optional[str], float]:
        """Detect insight type and confidence"""
        for insight_category, info in self.INSIGHT_PATTERNS.items():
            if info['pattern'].search(content):
                return info['type'], info['confidence']
        return None, 0.0

    def _detect_domain(self, content: str) -> Optional[str]:
        """Detect domain/context of insight"""
        for domain, pattern in self.DOMAIN_PATTERNS.items():
            if pattern.search(content):
                return domain
        return None

    def _extract_insight_text(self, content: str, insight_type: str) -> str:
        """Extract the key insight sentence"""
        # Split into sentences
        sentences = re.split(r'[.!?]\s+', content)

        # Find sentence with insight indicator
        for sentence in sentences:
            for info in self.INSIGHT_PATTERNS.values():
                if info['type'] == insight_type and info['pattern'].search(sentence):
                    # Return this sentence (truncated if too long)
                    return sentence[:200].strip()

        # Fallback: return first sentence
        return sentences[0][:200].strip() if sentences else content[:200].strip()

    def _extract_learning(self, content: str) -> str:
        """Extract what was learned from the insight"""
        # Look for "because", "so", "therefore" clauses
        learning_pattern = re.compile(
            r"(because|so|therefore|which means|this means|indicating|suggesting)\s+(.+?)(?:\.|$)",
            re.I | re.DOTALL
        )

        match = learning_pattern.search(content)
        if match:
            return match.group(2)[:200].strip()

        # Fallback: return a snippet
        return content[:200].strip()

    def get_insight_stats(self) -> dict:
        """Get insight statistics"""
        return {
            'total_insights': self._insight_count
        }
