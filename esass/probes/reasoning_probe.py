"""
Reasoning chain observation probe.

Captures Claude's thinking process, hypotheses, and confidence levels.
"""

import re
from typing import List, Optional, Tuple

from esass.probes.base import FilteringProbe, ProbeContext, TagExtractor
from esass_prototype.models import LogEntry, create_reasoning_event


class ReasoningProbe(FilteringProbe):
    """
    Observes reasoning chains and hypothesis formation.

    Extracts:
    - Hypotheses and conclusions
    - Confidence indicators
    - Evidence cited
    - Reasoning patterns
    """

    # Patterns that indicate reasoning
    REASONING_INDICATORS = [
        r'\bI think\b',
        r'\blikely\b',
        r'\bprobably\b',
        r'\bappears? to\b',
        r'\bsuggests? that\b',
        r'\bindicates?\b',
        r'\bseems? to\b',
        r'\bmight be\b',
        r'\bcould be\b',
        r'\bshould be\b',
        r'\bmy hypothesis\b',
        r'\bI suspect\b',
        r'\bI believe\b',
        r'\bI infer\b',
        r'\bI conclude\b',
    ]

    # High confidence indicators
    HIGH_CONFIDENCE = [
        r'\bcertainly\b',
        r'\bdefinitely\b',
        r'\bclearly\b',
        r'\bobviously\b',
        r'\bundoubtedly\b',
        r'\bwill\b',
        r'\bmust be\b',
    ]

    # Low confidence indicators
    LOW_CONFIDENCE = [
        r'\bmaybe\b',
        r'\bperhaps\b',
        r'\bpossibly\b',
        r'\bmight\b',
        r'\bcould\b',
        r'\bunsure\b',
        r'\bnot certain\b',
    ]

    def __init__(self, enabled: bool = True,
                 min_confidence: float = 0.0,
                 extract_evidence: bool = True):
        """
        Initialize reasoning probe.

        Args:
            enabled: Whether probe is active
            min_confidence: Minimum confidence to log (0.0-1.0)
            extract_evidence: Whether to extract evidence citations
        """
        super().__init__(enabled)
        self.min_confidence = min_confidence
        self.extract_evidence = extract_evidence

    def can_observe(self, event_type: str) -> bool:
        """Handle message_generated and thinking_block events"""
        return event_type in [
            'message_generated',
            'thinking_block',
            'hypothesis_formed'
        ]

    def observe_filtered(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """Extract reasoning from messages and thinking blocks"""
        event_type = context.event_type

        if event_type == 'thinking_block':
            return self._on_thinking_block(context)
        elif event_type == 'message_generated':
            return self._on_message_generated(context)
        elif event_type == 'hypothesis_formed':
            return self._on_hypothesis_formed(context)

        return None

    def _on_thinking_block(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """
        Process thinking block content.

        Thinking blocks contain explicit reasoning that should be captured.
        """
        thinking_content = context.event_data.get('content', '')
        if not thinking_content:
            return None

        # Extract multiple reasoning statements from thinking block
        entries = []

        # Split by sentence
        sentences = self._split_into_sentences(thinking_content)

        for sentence in sentences:
            if self._contains_reasoning(sentence):
                reasoning_data = self._extract_reasoning(sentence)

                if reasoning_data['confidence'] >= self.min_confidence:
                    entry = create_reasoning_event(
                        statement=reasoning_data['statement'],
                        confidence=reasoning_data['confidence'],
                        evidence=reasoning_data.get('evidence'),
                        session_id=context.session_id or 'unknown',
                        caused_by=context.current_parent,
                        tags=reasoning_data.get('tags', [])
                    )
                    entries.append(entry)

        return entries if entries else None

    def _on_message_generated(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """
        Process generated message for reasoning patterns.

        Messages may contain implicit reasoning that's valuable to capture.
        """
        message = context.event_data.get('message', '')
        if not message:
            return None

        # Only process if message contains reasoning indicators
        if not self._contains_reasoning(message):
            return None

        # Extract first major reasoning statement
        reasoning_data = self._extract_reasoning(message)

        if reasoning_data['confidence'] < self.min_confidence:
            return None

        entry = create_reasoning_event(
            statement=reasoning_data['statement'],
            confidence=reasoning_data['confidence'],
            evidence=reasoning_data.get('evidence'),
            session_id=context.session_id or 'unknown',
            caused_by=context.current_parent,
            tags=reasoning_data.get('tags', [])
        )

        return [entry]

    def _on_hypothesis_formed(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """
        Handle explicit hypothesis formation events.

        Some integrations may directly signal hypothesis events.
        """
        hypothesis = context.event_data.get('hypothesis', '')
        confidence = context.event_data.get('confidence', 0.5)
        evidence = context.event_data.get('evidence', [])

        if not hypothesis:
            return None

        entry = create_reasoning_event(
            statement=hypothesis,
            confidence=confidence,
            evidence=evidence if evidence else None,
            session_id=context.session_id or 'unknown',
            caused_by=context.current_parent,
            tags=['hypothesis', 'explicit']
        )

        return [entry]

    def _contains_reasoning(self, text: str) -> bool:
        """
        Check if text contains reasoning indicators.

        Args:
            text: Text to analyze

        Returns:
            True if text appears to contain reasoning
        """
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in self.REASONING_INDICATORS)

    def _extract_reasoning(self, text: str) -> dict:
        """
        Extract reasoning statement and metadata from text.

        Args:
            text: Text containing reasoning

        Returns:
            Dict with statement, confidence, evidence, tags
        """
        # Estimate confidence from language
        confidence = self._estimate_confidence(text)

        # Extract evidence if enabled
        evidence = None
        if self.extract_evidence:
            evidence = self._extract_evidence(text)

        # Extract semantic tags
        tags = TagExtractor.extract_from_text(text)
        tags.append('reasoning')

        # Clean up statement
        statement = self._clean_statement(text)

        return {
            'statement': statement,
            'confidence': confidence,
            'evidence': evidence,
            'tags': tags
        }

    def _estimate_confidence(self, text: str) -> float:
        """
        Estimate confidence level from linguistic cues.

        Args:
            text: Text to analyze

        Returns:
            Confidence score 0.0-1.0
        """
        text_lower = text.lower()

        # Check for high confidence indicators
        high_count = sum(1 for pattern in self.HIGH_CONFIDENCE
                        if re.search(pattern, text_lower))

        # Check for low confidence indicators
        low_count = sum(1 for pattern in self.LOW_CONFIDENCE
                       if re.search(pattern, text_lower))

        # Base confidence
        base = 0.5

        # Adjust based on indicators
        if high_count > low_count:
            return min(0.95, base + (high_count * 0.15))
        elif low_count > high_count:
            return max(0.2, base - (low_count * 0.15))

        return base

    def _extract_evidence(self, text: str) -> Optional[List[str]]:
        """
        Extract evidence citations from text.

        Looks for:
        - "because X"
        - "since X"
        - "given that X"
        - "due to X"

        Args:
            text: Text to analyze

        Returns:
            List of evidence strings, or None
        """
        evidence_patterns = [
            r'because\s+(.+?)(?:[.!?]|$)',
            r'since\s+(.+?)(?:[.!?]|$)',
            r'given that\s+(.+?)(?:[.!?]|$)',
            r'due to\s+(.+?)(?:[.!?]|$)',
            r'as\s+(.+?)(?:[.!?]|$)',
        ]

        evidence = []
        text_lower = text.lower()

        for pattern in evidence_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                evidence_text = match.group(1).strip()
                if len(evidence_text) > 10:  # Skip very short matches
                    evidence.append(evidence_text[:200])  # Truncate long evidence

        return evidence if evidence else None

    def _clean_statement(self, text: str) -> str:
        """
        Clean reasoning statement for logging.

        Args:
            text: Raw text

        Returns:
            Cleaned statement
        """
        # Take first complete sentence or first 200 chars
        sentences = self._split_into_sentences(text)
        if sentences:
            statement = sentences[0]
        else:
            statement = text[:200]

        # Trim whitespace
        statement = statement.strip()

        # Remove markdown formatting
        statement = re.sub(r'\*\*(.+?)\*\*', r'\1', statement)  # Bold
        statement = re.sub(r'\*(.+?)\*', r'\1', statement)  # Italic
        statement = re.sub(r'`(.+?)`', r'\1', statement)  # Code

        return statement

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Simple sentence splitting (could be enhanced with NLTK)
        sentences = re.split(r'[.!?]+\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]


class CausalReasoningProbe(ReasoningProbe):
    """
    Enhanced reasoning probe that tracks causal relationships.

    Detects cause-effect reasoning patterns.
    """

    CAUSAL_PATTERNS = [
        r'if\s+(.+?)\s+then\s+(.+?)(?:[.!?]|$)',
        r'when\s+(.+?),\s+(.+?)(?:[.!?]|$)',
        r'(.+?)\s+causes?\s+(.+?)(?:[.!?]|$)',
        r'(.+?)\s+leads? to\s+(.+?)(?:[.!?]|$)',
        r'(.+?)\s+results? in\s+(.+?)(?:[.!?]|$)',
    ]

    def observe_filtered(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """Extend observation to detect causal patterns"""
        entries = super().observe_filtered(context)

        # Check for causal reasoning
        if context.event_type in ['thinking_block', 'message_generated']:
            text = context.event_data.get('content') or context.event_data.get('message', '')
            if text:
                causal_entry = self._detect_causal_reasoning(text, context)
                if causal_entry:
                    if entries:
                        entries.append(causal_entry)
                    else:
                        entries = [causal_entry]

        return entries

    def _detect_causal_reasoning(self, text: str, context: ProbeContext) -> Optional[LogEntry]:
        """
        Detect if-then and causal reasoning.

        Args:
            text: Text to analyze
            context: Event context

        Returns:
            LogEntry for causal reasoning, or None
        """
        for pattern in self.CAUSAL_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                cause = match.group(1).strip()
                effect = match.group(2).strip()

                return LogEntry.create(
                    event_type='reasoning',
                    event_data={
                        'statement': f'Causal reasoning: {cause} → {effect}',
                        'confidence': 0.8,
                        'evidence': [f'If-then pattern detected'],
                        'causal': True,
                        'cause': cause,
                        'effect': effect
                    },
                    session_id=context.session_id or 'unknown',
                    caused_by=context.current_parent,
                    tags=['reasoning', 'causal', 'if_then']
                )

        return None
