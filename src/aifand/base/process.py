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
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from pydantic import ConfigDict, Field

from aifand.base.entity import Entity
from aifand.base.state import States

if TYPE_CHECKING:
    from aifand.base.state import State


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
            f"{self.__class__.__module__}."
            f"{self.__class__.__name__}."
            f"{self.name}"
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

    Environments interface with the physical or simulated world using
    a position-dependent execution pattern:

    - Pipeline start (no input): Read sensors, create initial states
    - Pipeline middle/end (has input): Apply control, pass through

    This pattern avoids redundant sensor reading while ensuring control
    decisions reach hardware. The same Environment instance can serve
    as both sensor source and actuator sink.

    Permission rules:
    - Can create, read, and modify Sensors
    - Can read Actuators from input states
    - Can write Actuator values to hardware
    - Cannot modify Actuator values in states (only Controllers do that)
    """

    def _execute(self, states: States) -> States:
        """Execute position-dependent environment operations.

        Args:
            states: Input states from pipeline (empty if at start)

        Returns:
            Fresh states if at start, or passed-through states if not

        """
        if not states:
            # Pipeline start - create fresh states from world
            actual = self._read_sensors()
            result = States({"actual": actual})
            # Initialize desired as copy of actual for initial control
            # Copy only actuators to desired state (not sensors)
            from typing import cast

            from aifand.base.device import Actuator, Device
            from aifand.base.state import State

            desired_devices = {
                name: cast("Device", device)  # Actuator inherits Device
                for name, device in actual.devices.items()
                if isinstance(device, Actuator)
            }
            result["desired"] = State(devices=desired_devices)
            return result
        # Pipeline middle/end - apply control and pass through
        if "desired" in states:
            self._write_actuators(states["desired"])
        return states

    @abstractmethod
    def _read_sensors(self) -> "State":
        """Read current sensor values from the world.

        Returns:
            State containing current sensor and actuator readings

        """

    @abstractmethod
    def _write_actuators(self, desired: "State") -> None:
        """Write actuator values to the world.

        Args:
            desired: State containing target actuator values to write

        """


class Controller(Process, ABC):
    """Abstract base class for control logic.

    Controllers represent an attempt to modify a controllable, such as
    a real or virtual Actuator. A Controller implements decision-making
    logic that determines actuator settings, based on current, previous,
    and predicted Sensor readings.

    A Controller can read Sensors, and it can modify Actuators.  It
    can't create or copy Sensors or Actuators, as those are created
    by the Environment.

    As a general guideline, one Controller should be responsible for
    only one bit of control logic. It's possible to chain together
    multiple Controllers to implement complex control logic, in
    the form of a Pipeline.

    Controller implementations typically override _think() for core
    logic, and may override _import_state() and _export_state() for
    format conversion.
    """
