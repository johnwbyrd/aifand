"""Process classes for thermal management system execution.

CRITICAL: Process base class MUST NOT store persistent state!
State persistence is handled by concrete subclasses (Pipeline, System)
that have explicit state management fields. The Process base class
provides execution framework only.
DO NOT ADD STATE STORAGE TO THIS FILE!  NOT IN ATTRIBUTES, NOT IN
METHODS!
THIS MEANS YOU, CLAUDE!
"""

import logging
import time
from abc import ABC
from typing import Any

from pydantic import ConfigDict, Field

from aifand.base.entity import Entity
from aifand.base.state import States


class Process(Entity, ABC):
    """Base class for computational units in thermal management.

    A Process represents a computational unit that transforms states
    within the system. Processes can contain child processes that
    execute in serial order, forming execution pipelines. Each process
    receives a dictionary of named states and produces a transformed
    dictionary of states.

    Process supports two execution modes:
    1. Stateless execution via execute() for transformations
    2. Timing-driven execution via start() for autonomous operation

    Key characteristics:
    - Stateless execution: No data persists between execute() calls
    - Pipeline: Child processes execute serially with state passthrough
    - Error resilient: Exceptions are caught, logged, and execution
      continues
    - Immutable input states: Input states are never modified (deep copy
      used)
    - Mutable structure: Process structure can be modified for
      construction
    - Template method timing: Subclasses override timing strategies

    Subclasses must implement _process() and timing methods to define
    their specific logic.
    """

    model_config = ConfigDict(extra="allow", frozen=False)

    # Timing configuration
    interval_ns: int = Field(
        default=100_000_000,  # 100ms in nanoseconds
        description="Default execution interval in nanoseconds for "
        "timing-driven mode",
    )

    # Runtime timing state (mutable during execution)
    start_time: int = Field(
        default=0,
        description="Start time of current timing loop execution "
        "(nanoseconds)",
    )
    execution_count: int = Field(
        default=0,
        description="Number of completed execution cycles in timing mode",
    )
    stop_requested: bool = Field(
        default=False,
        description="Whether graceful stop has been requested",
    )

    def __init__(self, **data: Any) -> None:
        """Initialize process with logging and execution tracking."""
        super().__init__(**data)
        # Create a logger specific to this process instance
        self._logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}.{self.name}"
        )

    def execute(self, states: States) -> States:
        """Execute this process, transforming the input states.

        Template method that calls _execute() and automatically updates
        execution count.

        Args:
            states: Dictionary of named states (e.g., "actual",
                "desired")

        Returns:
            Dictionary of transformed states

        Note:
            Input states are never modified. All transformations work on
            copies.

        """
        try:
            result = self._execute(states)
            self.update_execution_count()
            # Keep return in try block to group success path together
            return result  # noqa: TRY300
        except Exception:  # noqa: TRY203
            # Must catch and re-raise to prevent execution count update
            # The re-raise preserves original exception and stack trace
            raise

    def _execute(self, states: States) -> States:
        """Execute this process using three-method pattern.

        Default implementation calls the three-method pattern:
        _import_state() → _think() → _export_state()

        This can be overridden by subclasses that need custom execution
        flow, while maintaining backward compatibility.

        Args:
            states: Dictionary of named states (e.g., "actual",
                "desired")

        Returns:
            Dictionary of transformed states

        Note:
            Input states are never modified. All transformations work on
            copies.

        """
        # Three-method pattern execution
        self._import_state(states)
        self._think()
        return self._export_state()

    def _import_state(self, states: States) -> None:
        """Import and process input states into internal representation.

        Default implementation does nothing (pass-through).
        Stateful processes override this to update internal memory.
        AI processes override this for State → tensor conversion.

        Args:
            states: Dictionary of named input states

        """

    def _think(self) -> None:
        """Core computation logic using internal state.

        Default implementation does nothing (pass-through).
        All processes typically override this for their core logic.
        Reads from and writes to instance variables for state
        communication.
        """

    def _export_state(self) -> States:
        """Export internal representation back to standard State format.

        Default implementation returns empty state dictionary.
        Processes override this to convert internal state to external
        format.

        Returns:
            Dictionary of final output states
        """
        return States()

    def get_time(self) -> int:
        """Get current time in nanoseconds.

        Returns nanosecond timestamp. Can be overridden by subclasses
        to use alternative time sources like GPS clocks, NTP
        synchronization, or other high-precision timing sources.

        When running under a Runner, returns the runner's time source
        which may be simulated time for testing.

        Returns:
            Current time in nanoseconds since epoch

        """
        # Import here to avoid circular dependency
        from aifand.base.runner import TimeSource

        # Check for runner-provided time source
        runner = TimeSource.get_current()
        if runner:
            return runner.get_time()

        # Fall back to system time
        return time.monotonic_ns()

    def update_execution_count(self) -> None:
        """Update execution count after successful process execution.

        Called automatically by execute() after successful completion.
        Can be overridden by subclasses to customize execution count
        behavior.

        Default implementation increments execution_count by 1.
        """
        self.execution_count += 1

    def get_next_execution_time(self) -> int:
        """Calculate when the next execution should occur.

        Uses modulo timing for calculation.

        Returns:
            Next execution time in nanoseconds since epoch

        """
        return self.start_time + (self.execution_count * self.interval_ns)

    def initialize(self) -> None:
        """Initialize all state needed for process execution.

        Sets up timing control fields for this process.
        Can be called by parent processes to initialize child
        state before execution begins.
        """
        self.start_time = self.get_time()
        self.execution_count = 0
        self.stop_requested = False

    def __lt__(self, other: "Process") -> bool:
        """Compare processes for heap ordering by UUID string.

        This enables heapq to handle processes with identical execution
        times
        by falling back to UUID comparison for consistent ordering.
        """
        return False


class Environment(Process, ABC):
    """Abstract base class for environment interfaces.

    Environments interface with the physical or simulated world, reading
    sensor values and applying actuator settings. They can read and
    modify sensors in their output state, but should only read actuators
    from their input state.

    Environment implementations typically override _think() for core
    logic, and may override _import_state() and _export_state() for
    format conversion.
    """


class Controller(Process, ABC):
    """Abstract base class for control logic.

    Controllers implement decision-making logic that determines actuator
    settings based on sensor readings. They can read and modify
    actuators in their output state, but should only read sensors from
    their input state.

    Controller implementations typically override _think() for core
    logic, and may override _import_state() and _export_state() for
    format conversion.
    """
