"""Process classes for thermal management system execution.

CRITICAL: Process base class MUST NOT store persistent state!
State persistence is handled by concrete subclasses (Pipeline, System) that have explicit
state management fields. The Process base class provides execution framework only.
DO NOT ADD STATE STORAGE TO THIS FILE!  NOT IN ATTRIBUTES, NOT IN METHODS!
THIS MEANS YOU, CLAUDE!
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict

from pydantic import ConfigDict, Field

from .entity import Entity
from .state import State


class Process(Entity, ABC):
    """Base class for computational units that transform thermal management data.

    A Process represents a computational unit that transforms states within the system.
    Processes can contain child processes that execute in serial order, forming
    execution pipelines. Each process receives a dictionary of named states and
    produces a transformed dictionary of states.

    Process supports two execution modes:
    1. Stateless execution via execute() for transformations
    2. Timing-driven execution via start() for autonomous operation

    Key characteristics:
    - Stateless execution: No data persists between execute() calls
    - Pipeline: Child processes execute serially with state passthrough
    - Error resilient: Exceptions are caught, logged, and execution continues
    - Immutable input states: Input states are never modified (deep copy used)
    - Mutable structure: Process structure can be modified for construction
    - Template method timing: Subclasses override timing strategies

    Subclasses must implement _process() and timing methods to define their specific logic.
    """

    model_config = ConfigDict(extra="allow", frozen=False)

    # Timing configuration
    interval_ns: int = Field(
        default=100_000_000,  # 100ms in nanoseconds
        description="Default execution interval in nanoseconds for timing-driven mode",
    )

    # Runtime timing state (mutable during execution)
    start_time: int = Field(default=0, description="Start time of current timing loop execution (nanoseconds)")
    execution_count: int = Field(default=0, description="Number of completed execution cycles in timing mode")
    stop_requested: bool = Field(default=False, description="Whether graceful stop has been requested")

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        # Create a logger specific to this process instance
        self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}.{self.name}")

    @abstractmethod
    def execute(self, states: Dict[str, State]) -> Dict[str, State]:
        """Execute this process, transforming the input states.

        Args:
            states: Dictionary of named states (e.g., "actual", "desired")

        Returns:
            Dictionary of transformed states

        Note:
            Input states are never modified. All transformations work on copies.

        """

    def get_time(self) -> int:
        """Get current time in nanoseconds.

        Returns nanosecond timestamp. Can be overridden by subclasses to use
        alternative time sources like GPS clocks, NTP synchronization, or
        other high-precision timing sources.

        When running under a Runner, returns the runner's time source which
        may be simulated time for testing.

        Returns:
            Current time in nanoseconds since epoch

        """
        # Import here to avoid circular dependency
        from .runner import TimeSource

        # Check for runner-provided time source
        runner = TimeSource.get_current()
        if runner:
            return runner.get_time()

        # Fall back to system time
        return time.monotonic_ns()

    def update_execution_count(self) -> None:
        """Update execution count after successful process execution.

        Called automatically by execute() after successful completion.
        Can be overridden by subclasses to customize execution count behavior.

        Default implementation increments execution_count by 1.
        """
        self.execution_count += 1

    def get_next_execution_time(self) -> int:
        """Calculate when the next execution should occur using modulo timing.

        Returns:
            Next execution time in nanoseconds since epoch

        """
        return self.start_time + (self.execution_count * self.interval_ns)

    def initialize_timing(self) -> None:
        """Initialize timing state for execution.

        Sets up timing control fields for this process.
        Can be called by parent processes to initialize child timing state
        before execution begins.
        """
        self.start_time = self.get_time()
        self.execution_count = 0
        self.stop_requested = False

    def __lt__(self, other: "Process") -> bool:
        """Compare processes for heap ordering by UUID string.

        This enables heapq to handle processes with identical execution times
        by falling back to UUID comparison for consistent ordering.
        """
        return False


class Environment(Process, ABC):
    """Abstract base class for environment interfaces.

    Environments interface with the physical or simulated world, reading sensor
    values and applying actuator settings. They can read and modify sensors in
    their output state, but should only read actuators from their input state.
    """

    @abstractmethod
    def execute(self, states: Dict[str, State]) -> Dict[str, State]:
        """Environment-specific state transformation implementation."""


class Controller(Process, ABC):
    """Abstract base class for control logic.

    Controllers implement decision-making logic that determines actuator settings
    based on sensor readings. They can read and modify actuators in their output
    state, but should only read sensors from their input state.
    """

    @abstractmethod
    def execute(self, states: Dict[str, State]) -> Dict[str, State]:
        """Controller-specific state transformation implementation."""
