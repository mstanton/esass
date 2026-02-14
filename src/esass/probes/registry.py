"""
Probe registry and event routing system.

Central coordination for all observation probes.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from esass.probes.base import Probe, ProbeContext
from esass.models import LogEntry

logger = logging.getLogger(__name__)


class ProbeRegistry:
    """
    Central registry for all ESASS observation probes.

    Manages probe lifecycle and event routing:
    - Register/unregister probes
    - Route events to interested probes
    - Collect log entries from probes
    - Handle probe errors gracefully
    - Track performance metrics
    """

    def __init__(self, event_pipeline: Optional['EventPipeline'] = None):
        """
        Initialize probe registry.

        Args:
            event_pipeline: Optional pipeline for processing captured events
        """
        self.probes: List[Probe] = []
        self.event_pipeline = event_pipeline
        self._active = True
        self._total_events_received = 0
        self._total_entries_generated = 0
        self._probe_errors = 0
        self._session_stack: List[str] = []  # Track call hierarchy

        logger.info("ProbeRegistry initialized")

    def register(self, probe: Probe) -> None:
        """
        Register a probe for event observation.

        Args:
            probe: Probe instance to register
        """
        if probe not in self.probes:
            self.probes.append(probe)
            logger.info(f"Registered probe: {probe.name}")
        else:
            logger.warning(f"Probe already registered: {probe.name}")

    def unregister(self, probe: Probe) -> None:
        """
        Unregister a probe.

        Args:
            probe: Probe to remove
        """
        if probe in self.probes:
            self.probes.remove(probe)
            logger.info(f"Unregistered probe: {probe.name}")

    def register_all(self, probes: List[Probe]) -> None:
        """
        Register multiple probes at once.

        Args:
            probes: List of probes to register
        """
        for probe in probes:
            self.register(probe)

    def notify(self, event_type: str, event_data: Dict[str, Any],
               context: Optional[Dict[str, Any]] = None) -> int:
        """
        Notify all probes of an event.

        Routes event to interested probes and collects log entries.

        Args:
            event_type: Type of event (e.g., 'tool_call_start')
            event_data: Event-specific data
            context: Optional additional context (session_id, etc.)

        Returns:
            Number of log entries generated
        """
        if not self._active:
            return 0

        self._total_events_received += 1

        # Build probe context
        probe_context = self._build_context(event_type, event_data, context or {})

        # Route to interested probes
        all_entries: List[LogEntry] = []

        for probe in self.probes:
            if not probe.enabled:
                continue

            if not probe.can_observe(event_type):
                continue

            try:
                entries = probe.observe(probe_context)
                if entries:
                    all_entries.extend(entries)
                    logger.debug(f"{probe.name} generated {len(entries)} entries for {event_type}")

            except Exception as e:
                self._probe_errors += 1
                logger.error(f"Probe {probe.name} failed on {event_type}: {e}", exc_info=True)
                try:
                    probe.on_error(e, probe_context)
                except Exception as error_handler_error:
                    logger.error(f"Probe error handler failed: {error_handler_error}")

        # Send entries to pipeline
        if all_entries and self.event_pipeline:
            try:
                self.event_pipeline.submit(all_entries)
                self._total_entries_generated += len(all_entries)
                logger.debug(f"Submitted {len(all_entries)} entries to pipeline")
            except Exception as e:
                logger.error(f"Failed to submit entries to pipeline: {e}", exc_info=True)

        return len(all_entries)

    def push_context(self, event_id: str) -> None:
        """
        Push event ID onto context stack for causality tracking.

        Args:
            event_id: Event ID to track as parent
        """
        self._session_stack.append(event_id)

    def pop_context(self) -> Optional[str]:
        """
        Pop event ID from context stack.

        Returns:
            Popped event ID, or None if stack empty
        """
        return self._session_stack.pop() if self._session_stack else None

    def _build_context(self, event_type: str, event_data: Dict[str, Any],
                       context: Dict[str, Any]) -> ProbeContext:
        """
        Build ProbeContext from event information.

        Args:
            event_type: Event type
            event_data: Event data
            context: Additional context

        Returns:
            Constructed ProbeContext
        """
        return ProbeContext(
            event_type=event_type,
            event_data=event_data,
            session_id=context.get('session_id') or context.get('conversation_id'),
            conversation_id=context.get('conversation_id'),
            timestamp=context.get('timestamp') or datetime.utcnow(),
            call_stack=self._session_stack.copy(),
            metadata=context.get('metadata', {})
        )

    def start(self) -> None:
        """Activate the registry"""
        self._active = True
        logger.info("ProbeRegistry started")

    def stop(self) -> None:
        """Deactivate the registry"""
        self._active = False
        logger.info("ProbeRegistry stopped")

    def flush(self) -> None:
        """Flush pipeline and wait for completion"""
        if self.event_pipeline:
            self.event_pipeline.flush()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dict with metrics
        """
        stats = {
            'active': self._active,
            'registered_probes': len(self.probes),
            'total_events_received': self._total_events_received,
            'total_entries_generated': self._total_entries_generated,
            'probe_errors': self._probe_errors,
            'probes': {}
        }

        # Per-probe stats
        for probe in self.probes:
            stats['probes'][probe.name] = {
                'enabled': probe.enabled,
                **probe.stats
            }

        return stats

    def reset_stats(self) -> None:
        """Reset all statistics"""
        self._total_events_received = 0
        self._total_entries_generated = 0
        self._probe_errors = 0

        for probe in self.probes:
            probe.observations_count = 0
            probe.errors_count = 0

        logger.info("Registry statistics reset")


class GlobalRegistry:
    """
    Singleton global registry for convenient access.

    Usage:
        from esass.probes.registry import global_registry

        global_registry.register(ToolCallProbe())
        global_registry.notify('tool_call_start', {...})
    """

    _instance: Optional[ProbeRegistry] = None

    @classmethod
    def get_instance(cls) -> ProbeRegistry:
        """Get or create global registry instance"""
        if cls._instance is None:
            from esass.probes.pipeline import EventPipeline
            pipeline = EventPipeline()
            cls._instance = ProbeRegistry(event_pipeline=pipeline)
            logger.info("Created global ProbeRegistry instance")
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset global instance (primarily for testing)"""
        if cls._instance:
            cls._instance.stop()
            if cls._instance.event_pipeline:
                cls._instance.event_pipeline.shutdown()
        cls._instance = None
        logger.info("Reset global ProbeRegistry")


# Convenience global instance
global_registry = GlobalRegistry.get_instance()


def notify_event(event_type: str, event_data: Dict[str, Any],
                 context: Optional[Dict[str, Any]] = None) -> int:
    """
    Convenience function for notifying global registry.

    Args:
        event_type: Type of event
        event_data: Event data
        context: Optional context

    Returns:
        Number of log entries generated
    """
    return global_registry.notify(event_type, event_data, context)


def register_probe(probe: Probe) -> None:
    """
    Convenience function for registering with global registry.

    Args:
        probe: Probe to register
    """
    global_registry.register(probe)
