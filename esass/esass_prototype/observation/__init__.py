"""
Observation subsystem for ESASS.

This module handles event observation, simulation, and logging.
"""

from esass_prototype.observation.logger import ObservationLogger
from esass_prototype.observation.simulator import EventSimulator

__all__ = ['EventSimulator', 'ObservationLogger']
