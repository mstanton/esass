"""
ESASS Event Capture Probes

Real-time event capture system for observing Claude Code execution.

This module provides the probe infrastructure for capturing:
- Tool invocations and results
- Reasoning chains and hypotheses
- Decision points and rationale
- Errors and outcomes

Usage:
    from esass.probes import ProbeRegistry, ToolCallProbe, ReasoningProbe

    # Initialize registry
    registry = ProbeRegistry(logger)

    # Register probes
    registry.register(ToolCallProbe())
    registry.register(ReasoningProbe())

    # Notify probes of events
    registry.notify('tool_call_start', {
        'tool_name': 'Read',
        'parameters': {'file_path': 'foo.py'},
        'context': {'conversation_id': 'session-123'}
    })
"""

from esass.probes.base import Probe, ProbeContext
from esass.probes.decision_probe import DecisionProbe
from esass.probes.pipeline import EventPipeline
from esass.probes.reasoning_probe import ReasoningProbe
from esass.probes.registry import ProbeRegistry
from esass.probes.tool_probe import ToolCallProbe

__all__ = [
    'Probe',
    'ProbeContext',
    'ProbeRegistry',
    'ToolCallProbe',
    'ReasoningProbe',
    'DecisionProbe',
    'EventPipeline',
]

__version__ = '0.1.0'
