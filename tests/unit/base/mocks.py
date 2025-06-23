"""Mock classes for testing thermal management processes.

These are temporary scaffolding classes that provide basic implementations
of Environment and Controller for testing purposes. They will be replaced
by real implementations as the system is developed.
"""

from typing import Dict, List

from pydantic import Field

from src.aifand.base.pipeline import Pipeline
from src.aifand.base.process import Controller, Environment, Process
from src.aifand.base.state import State
from src.aifand.base.system import System


class MockEnvironment(Environment):
    """Basic Environment mock for testing."""

    def _execute(self, states: Dict[str, State]) -> Dict[str, State]:
        """Default implementation that passes states through unchanged."""
        return states


class MockController(Controller):
    """Basic Controller mock for testing."""

    def _execute(self, states: Dict[str, State]) -> Dict[str, State]:
        """Default implementation that passes states through unchanged."""
        return states


class CountingMixin:
    """Mixin that adds execution counting to Process classes.

    Used across multiple test files to track how many times a process
    has executed its execute method.
    """

    counter: int = Field(default=0, description="Counter for tracking executions")

    def _execute(self, states: Dict[str, State]) -> Dict[str, State]:
        """Increment counter and call parent _execute method."""
        self.counter += 1
        # Call parent class _execute if it exists
        if hasattr(super(), "_execute"):
            return super()._execute(states)
        return states


class FailingMixin:
    """Mixin that adds configurable failure behavior to Process classes.

    Used across multiple test files to test error handling by making
    processes fail after a specified number of executions.
    """

    fail_after: int = Field(default=3, description="Number of executions before failing")
    fail_count: int = Field(default=0, description="Counter for tracking calls before failure")

    def _execute(self, states: Dict[str, State]) -> Dict[str, State]:
        """Fail after specified number of executions."""
        self.fail_count += 1

        if self.fail_count > self.fail_after:
            raise RuntimeError(f"Simulated failure on execution {self.fail_count}")

        # Call parent class _execute if it exists
        if hasattr(super(), "_execute"):
            return super()._execute(states)
        return states


class MockTimedPipeline(Pipeline):
    """Pipeline mock for System testing with configurable intervals and execution tracking."""

    execution_timestamps: List[int] = Field(default_factory=list, description="Nanosecond timestamps of executions")
    execution_sequence: List[int] = Field(default_factory=list, description="Sequence numbers for executions")
    received_states_log: List[Dict[str, State]] = Field(
        default_factory=list, description="Log of states received during execution"
    )

    def _execute(self, states: Dict[str, State]) -> Dict[str, State]:
        """Track execution when called by System and pass states through."""
        self.execution_timestamps.append(self.get_time())
        self.execution_sequence.append(self.execution_count)
        self.received_states_log.append(states.copy())

        # Call the parent _execute method to handle any mixins (like FailingMixin)
        # Execution count will be automatically updated by base class
        return super()._execute(states)


class MockTimedSystem(System):
    """System mock for hierarchical testing with execution tracking."""

    execution_history: List[Dict] = Field(default_factory=list, description="History of executions with metadata")

    def _execute(self, states: Dict[str, State]) -> Dict[str, State]:
        """Track execution when called by parent System."""
        timestamp = self.get_time()
        self.execution_history.append(
            {
                "timestamp": timestamp,
                "event": "_execute",
                "execution_count": self.execution_count,
                "states": states.copy(),
            }
        )
        return super()._execute(states)


class MockProcess(Process):
    """Simple Process mock for mixed child testing."""

    call_history: List[Dict] = Field(default_factory=list, description="Complete call history with timestamps")
    execution_timestamps: List[int] = Field(default_factory=list, description="Nanosecond timestamps of executions")

    def _execute(self, states: Dict[str, State]) -> Dict[str, State]:
        """Track execution with detailed logging."""
        timestamp = self.get_time()
        self.execution_timestamps.append(timestamp)
        self.call_history.append(
            {
                "timestamp": timestamp,
                "method": "_execute",
                "execution_count": self.execution_count,
                "states_received": list(states.keys()),
            }
        )
        return states
