"""Mock classes for testing thermal management processes.

These are temporary scaffolding classes that provide basic implementations
of Environment and Controller for testing purposes. They will be replaced
by real implementations as the system is developed.
"""

from typing import Dict, List

from pydantic import Field

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


class CountingMixin:
    """Mixin that adds execution counting to Process classes.

    Used across multiple test files to track how many times a process
    has executed its _process method.
    """

    counter: int = Field(default=0, description="Counter for tracking executions")

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Increment counter and call parent _process method."""
        self.counter += 1
        # Call parent class _process if it exists
        if hasattr(super(), "_process"):
            return super()._process(states)
        return states


class FailingMixin:
    """Mixin that adds configurable failure behavior to Process classes.

    Used across multiple test files to test error handling by making
    processes fail after a specified number of executions.
    """

    fail_after: int = Field(default=3, description="Number of executions before failing")
    fail_count: int = Field(default=0, description="Counter for tracking calls before failure")

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Fail after specified number of executions."""
        self.fail_count += 1

        if self.fail_count > self.fail_after:
            raise RuntimeError(f"Simulated failure on execution {self.fail_count}")

        # Call parent class _process if it exists
        if hasattr(super(), "_process"):
            return super()._process(states)
        return states
