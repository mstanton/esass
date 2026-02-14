"""
Observation subsystem for ESASS.

This module handles event observation, simulation, and logging.
"""

from esass.observation.logger import ObservationLogger
from esass.observation.simulator import EventSimulator

__all__ = ['EventSimulator', 'ObservationLogger']
