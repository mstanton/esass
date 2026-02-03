"""
Calibration Probe

Tracks predicted confidence vs actual outcomes - essential for self-improvement.
Compares assertions, estimates, and predictions against reality.
"""

from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass
import re

from .base import FilteringProbe, ProbeContext, LogEntry


@dataclass
class Prediction:
    """Tracks a prediction and its outcome"""
    prediction_id: str
    timestamp: datetime
    prediction_type: str  # 'success', 'complexity', 'time', 'effectiveness'
    predicted_value: float  # 0-1 confidence or estimated value
    predicted_text: str
    actual_value: Optional[float] = None
    actual_outcome: Optional[str] = None
    verified: bool = False
    verification_time: Optional[datetime] = None
    calibration_error: Optional[float] = None


class CalibrationProbe(FilteringProbe):
    """
    Tracks confidence calibration.

    Captures:
    - "This should work" → did it?
    - Estimated complexity vs actual
    - Time estimates vs reality
    - Predicted outcomes vs actual

    Events observed:
    - thinking_block: Confidence statements and estimates
    - tool_call_complete/error: Outcome verification
    """

    # Confidence/prediction patterns
    PREDICTION_PATTERNS = {
        'high_confidence': {
            'pattern': re.compile(r"\b(should work|will work|definitely|certainly|surely|confident)", re.I),
            'confidence': 0.9
        },
        'moderate_confidence': {
            'pattern': re.compile(r"\b(probably|likely|should|might work|expect)", re.I),
            'confidence': 0.7
        },
        'low_confidence': {
            'pattern': re.compile(r"\b(might|may|possibly|unsure|uncertain|not sure)", re.I),
            'confidence': 0.4
        },
        'very_low_confidence': {
            'pattern': re.compile(r"\b(unlikely|doubtful|probably not|may not work)", re.I),
            'confidence': 0.2
        }
    }

    # Complexity estimate patterns
    COMPLEXITY_PATTERNS = {
        'simple': {
            'pattern': re.compile(r"\b(simple|easy|straightforward|trivial|quick)", re.I),
            'estimated_complexity': 0.2
        },
        'moderate': {
            'pattern': re.compile(r"\b(moderate|medium|reasonable)", re.I),
            'estimated_complexity': 0.5
        },
        'complex': {
            'pattern': re.compile(r"\b(complex|complicated|difficult|challenging)", re.I),
            'estimated_complexity': 0.8
        }
    }

    # Time estimate patterns (extract numbers)
    TIME_PATTERN = re.compile(r"\b(\d+)\s*(second|minute|hour|step|action)s?\b", re.I)

    def __init__(self, enabled: bool = True, verification_window_seconds: int = 300):
        super().__init__(enabled)
        self.verification_window_seconds = verification_window_seconds
        self._pending_predictions: Dict[str, Prediction] = {}
        self._verified_predictions: List[Prediction] = []
        self._last_prediction_id: Optional[str] = None

    def can_observe(self, event_type: str) -> bool:
        """Observe prediction and verification events"""
        return event_type in [
            'thinking_block',
            'tool_call_complete',
            'tool_call_error'
        ]

    def observe_filtered(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """Track predictions and verify them"""
        event_type = context.event_type

        if event_type == 'thinking_block':
            return self._handle_prediction(context)
        elif event_type in ['tool_call_complete', 'tool_call_error']:
            return self._handle_verification(context)

        return None

    def _handle_prediction(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """Extract predictions from thinking"""
        content = context.event_data.get('content', '')
        entries = []

        # Check for confidence statements
        confidence_level, confidence_value = self._extract_confidence(content)
        if confidence_level:
            prediction_id = f"pred-{context.session_id}-{context.timestamp.timestamp()}"
            prediction = Prediction(
                prediction_id=prediction_id,
                timestamp=context.timestamp,
                prediction_type='success',
                predicted_value=confidence_value,
                predicted_text=content[:200]
            )

            self._pending_predictions[prediction_id] = prediction
            self._last_prediction_id = prediction_id

            entry = LogEntry(
                event_id=f"{prediction_id}-made",
                timestamp=context.timestamp,
                event_type="calibration",
                event_data={
                    'prediction_id': prediction_id,
                    'type': 'success_prediction',
                    'confidence_level': confidence_level,
                    'confidence_value': confidence_value,
                    'statement': content[:200],
                    'phase': 'prediction'
                },
                session_id=context.session_id,
                tags=['calibration', 'prediction', confidence_level]
            )
            entries.append(entry)

        # Check for complexity estimates
        complexity_level, complexity_value = self._extract_complexity(content)
        if complexity_level:
            prediction_id = f"complexity-{context.session_id}-{context.timestamp.timestamp()}"
            prediction = Prediction(
                prediction_id=prediction_id,
                timestamp=context.timestamp,
                prediction_type='complexity',
                predicted_value=complexity_value,
                predicted_text=content[:200]
            )

            self._pending_predictions[prediction_id] = prediction

            entry = LogEntry(
                event_id=f"{prediction_id}-made",
                timestamp=context.timestamp,
                event_type="calibration",
                event_data={
                    'prediction_id': prediction_id,
                    'type': 'complexity_estimate',
                    'complexity_level': complexity_level,
                    'complexity_value': complexity_value,
                    'statement': content[:200],
                    'phase': 'prediction'
                },
                session_id=context.session_id,
                tags=['calibration', 'complexity', complexity_level]
            )
            entries.append(entry)

        return entries if entries else None

    def _handle_verification(self, context: ProbeContext) -> Optional[List[LogEntry]]:
        """Verify predictions against outcomes"""
        if not self._pending_predictions:
            return None

        entries = []
        event_type = context.event_type
        data = context.event_data

        # Determine actual outcome
        actual_success = 1.0 if event_type == 'tool_call_complete' and data.get('success', False) else 0.0

        # Verify recent predictions
        for pred_id, prediction in list(self._pending_predictions.items()):
            # Check if within verification window
            time_since_prediction = (context.timestamp - prediction.timestamp).total_seconds()
            if time_since_prediction > self.verification_window_seconds:
                # Timeout - remove from pending
                self._pending_predictions.pop(pred_id)
                continue

            # Verify success predictions
            if prediction.prediction_type == 'success':
                prediction.actual_value = actual_success
                prediction.actual_outcome = 'success' if actual_success == 1.0 else 'failure'
                prediction.verified = True
                prediction.verification_time = context.timestamp
                prediction.calibration_error = abs(prediction.predicted_value - actual_success)

                entry = LogEntry(
                    event_id=f"{pred_id}-verified",
                    timestamp=context.timestamp,
                    event_type="calibration",
                    event_data={
                        'prediction_id': pred_id,
                        'type': 'verification',
                        'predicted_confidence': prediction.predicted_value,
                        'actual_outcome': prediction.actual_outcome,
                        'calibration_error': prediction.calibration_error,
                        'well_calibrated': prediction.calibration_error < 0.3,
                        'overconfident': prediction.predicted_value > 0.7 and actual_success == 0.0,
                        'underconfident': prediction.predicted_value < 0.5 and actual_success == 1.0,
                        'phase': 'verification'
                    },
                    session_id=context.session_id,
                    tags=['calibration', 'verification', prediction.actual_outcome or 'unknown'],
                    caused_by=f"{pred_id}-made"
                )
                entries.append(entry)

                # Move to verified
                self._verified_predictions.append(prediction)
                self._pending_predictions.pop(pred_id)

        return entries if entries else None

    def _extract_confidence(self, content: str) -> tuple[Optional[str], Optional[float]]:
        """Extract confidence level from text"""
        for level, info in self.PREDICTION_PATTERNS.items():
            if info['pattern'].search(content):
                return level, info['confidence']
        return None, None

    def _extract_complexity(self, content: str) -> tuple[Optional[str], Optional[float]]:
        """Extract complexity estimate from text"""
        for level, info in self.COMPLEXITY_PATTERNS.items():
            if info['pattern'].search(content):
                return level, info['estimated_complexity']
        return None, None

    def get_calibration_stats(self) -> Dict:
        """Get calibration statistics"""
        if not self._verified_predictions:
            return {
                'total_predictions': 0,
                'verified': 0,
                'mean_calibration_error': 0.0,
                'well_calibrated_pct': 0.0,
                'overconfident_pct': 0.0,
                'underconfident_pct': 0.0,
                'by_confidence_level': {}
            }

        total = len(self._verified_predictions)

        # Calculate mean calibration error
        errors = [p.calibration_error for p in self._verified_predictions if p.calibration_error is not None]
        mean_error = sum(errors) / len(errors) if errors else 0.0

        # Count calibration quality
        well_calibrated = sum(1 for p in self._verified_predictions if p.calibration_error and p.calibration_error < 0.3)
        overconfident = sum(1 for p in self._verified_predictions
                          if p.predicted_value > 0.7 and p.actual_value == 0.0)
        underconfident = sum(1 for p in self._verified_predictions
                           if p.predicted_value < 0.5 and p.actual_value == 1.0)

        # Breakdown by confidence level
        by_level = {}
        for prediction in self._verified_predictions:
            # Determine confidence bucket
            if prediction.predicted_value >= 0.8:
                level = 'high'
            elif prediction.predicted_value >= 0.6:
                level = 'moderate'
            elif prediction.predicted_value >= 0.4:
                level = 'low'
            else:
                level = 'very_low'

            if level not in by_level:
                by_level[level] = {
                    'count': 0,
                    'correct': 0,
                    'accuracy': 0.0
                }

            by_level[level]['count'] += 1
            if prediction.actual_value == 1.0:
                by_level[level]['correct'] += 1

        # Calculate accuracy for each level
        for level in by_level:
            by_level[level]['accuracy'] = (
                by_level[level]['correct'] / by_level[level]['count']
                if by_level[level]['count'] > 0 else 0.0
            )

        return {
            'total_predictions': total,
            'verified': total,
            'mean_calibration_error': mean_error,
            'well_calibrated_pct': well_calibrated / total if total > 0 else 0.0,
            'overconfident_pct': overconfident / total if total > 0 else 0.0,
            'underconfident_pct': underconfident / total if total > 0 else 0.0,
            'by_confidence_level': by_level
        }
