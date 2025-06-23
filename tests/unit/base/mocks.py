"""Mock classes for testing thermal management processes.

These are temporary scaffolding classes that provide basic implementations
of Environment and Controller for testing purposes. They will be replaced
by real implementations as the system is developed.
"""

from typing import Dict, List

from src.aifand.base.process import Controller, Environment, Process
from src.aifand.base.state import State


class MockEnvironment(Environment):
    """Basic Environment mock for testing."""

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Default implementation that passes states through unchanged."""
        return states

    def _calculate_next_tick_time(self) -> int:
        """Simple fixed interval timing for tests."""
        return self.start_time + (self.execution_count * self.interval_ns)

    def _select_processes_to_execute(self) -> List[Process]:
        """Return all children for unified timing."""
        return self.children


class MockController(Controller):
    """Basic Controller mock for testing."""

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Default implementation that passes states through unchanged."""
        return states

    def _calculate_next_tick_time(self) -> int:
        """Simple fixed interval timing for tests."""
        return self.start_time + (self.execution_count * self.interval_ns)

    def _select_processes_to_execute(self) -> List[Process]:
        """Return all children for unified timing."""
        return self.children
