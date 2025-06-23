"""Process classes for thermal management system execution.

CRITICAL: Process base class MUST NOT store persistent state!
State persistence is handled by concrete subclasses (Pipeline, System) that have explicit
state management fields. The Process base class provides execution framework only.
DO NOT ADD STATE STORAGE TO THIS FILE!  NOT IN ATTRIBUTES, NOT IN METHODS!
THIS MEANS YOU, CLAUDE!
"""

import copy
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List

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

    children: List["Process"] = Field(
        default_factory=list, description="Ordered list of child processes for pipeline execution"
    )

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

    def execute(self, states: Dict[str, State]) -> Dict[str, State]:
        """Execute this process and its children, transforming the input states.

        If this process has children, they are executed serially in order,
        with each child's output becoming the next child's input.

        If this process has no children, it copies the input states and
        calls _execute_impl() to perform its specific transformation.

        Args:
            states: Dictionary of named states (e.g., "actual", "desired")

        Returns:
            Dictionary of transformed states

        Note:
            Input states are never modified. All transformations work on copies.
            Exceptions in child processes are caught, logged, and execution continues
            with passthrough behavior (current states are preserved).

        """
        # Deep copy states to ensure we never modify the input
        result_states = copy.deepcopy(states)

        if not self.children:
            # No children - execute this process's logic
            try:
                self._logger.debug(f"Executing process {self.name}")
                return self._process(result_states)
            except PermissionError:
                # Permission errors should bubble up - they're programming errors, not operational failures
                raise
            except Exception as e:
                self._logger.error(f"Process {self.name} failed during execution: {e}", exc_info=True)
                return result_states  # Passthrough on error
        else:
            # Execute children serially in pipeline
            self._logger.debug(f"Executing pipeline for process {self.name} with {len(self.children)} children")

            for i, child in enumerate(self.children):
                try:
                    self._logger.debug(f"Executing child {i}: {child.name}")
                    result_states = child.execute(result_states)
                except PermissionError:
                    # Permission errors should bubble up - they're programming errors, not operational failures
                    raise
                except Exception as e:
                    self._logger.error(
                        f"Child process {child.name} (index {i}) failed in {self.name} pipeline: {e}", exc_info=True
                    )
                    # Continue with current states (passthrough behavior)
                    continue

            return result_states

    @abstractmethod
    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Implement process-specific state transformation logic.

        This method is called when the process has no children and needs to
        perform its own transformation. Subclasses must implement this method
        to define their specific behavior.

        Args:
            states: Dictionary of states to transform (already deep-copied)

        Returns:
            Dictionary of transformed states

        Note:
            This method should not modify the input states directly, but rather
            create new State objects for any changes.

        """
        pass

    def append_child(self, child: "Process") -> None:
        """Append a child process to the end of the execution pipeline.

        Args:
            child: Process to append to the end of the pipeline

        """
        self.children.append(child)

    def insert_before(self, target_name: str, process: "Process") -> None:
        """Insert a process before the named target process.

        Args:
            target_name: Name of the target process to insert before
            process: Process to insert

        Raises:
            ValueError: If target_name is not found in the pipeline

        """
        for i, child in enumerate(self.children):
            if child.name == target_name:
                self.children.insert(i, process)
                return
        raise ValueError(f"Process '{target_name}' not found in pipeline")

    def insert_after(self, target_name: str, process: "Process") -> None:
        """Insert a process after the named target process.

        Args:
            target_name: Name of the target process to insert after
            process: Process to insert

        Raises:
            ValueError: If target_name is not found in the pipeline

        """
        for i, child in enumerate(self.children):
            if child.name == target_name:
                self.children.insert(i + 1, process)
                return
        raise ValueError(f"Process '{target_name}' not found in pipeline")

    def remove_child(self, name: str) -> bool:
        """Remove a child process by name.

        Args:
            name: Name of the process to remove

        Returns:
            True if the process was found and removed, False otherwise

        """
        for i, child in enumerate(self.children):
            if child.name == name:
                del self.children[i]
                return True
        return False

    def get_logger(self) -> logging.Logger:
        """Get the logger instance for this process."""
        return self._logger

    def get_time(self) -> int:
        """Get current time in nanoseconds.

        Returns nanosecond timestamp. Can be overridden by subclasses to use
        alternative time sources like GPS clocks, NTP synchronization, or
        other high-precision timing sources.

        Returns:
            Current time in nanoseconds since epoch

        """
        return time.time_ns()

    @abstractmethod
    def _calculate_next_tick_time(self) -> int:
        """Calculate when the next execution should occur.

        This method implements the timing strategy for this process.
        Different process types can implement different timing approaches:
        - Pipeline: unified timing (all children execute at same interval)
        - System: independent timing (find earliest child ready time)

        Returns:
            Nanosecond timestamp when next execution should occur

        """
        pass

    @abstractmethod
    def _select_processes_to_execute(self) -> List["Process"]:
        """Select which child processes are ready for execution.

        This method determines which children should execute based on
        timing requirements and process-specific selection criteria.

        Returns:
            List of child processes ready for execution

        """
        pass

    def _execute_selected_processes(self, processes: List["Process"]) -> None:
        """Execute the selected child processes.

        Base implementation provides no state management - subclasses must
        override to implement their specific execution strategies and state handling.

        Args:
            processes: List of processes ready for execution

        """
        # Base Process class does NOT manage state - subclasses must override
        # this method to implement their own state management strategies
        for process in processes:
            try:
                self._logger.debug(f"Executing selected process: {process.name}")
                process.execute({})  # Base class provides empty state only
            except PermissionError:
                # Permission errors bubble up as programming errors
                raise
            except Exception as e:
                self._logger.error(
                    f"Selected process {process.name} failed during timing execution: {e}", exc_info=True
                )
                # Continue with other processes (error resilience)
                continue

    def _before_process(self) -> None:
        """Hook called before process execution in timing loop.

        Subclasses can override to implement preparation logic.
        Default implementation does nothing.
        """
        pass

    def _after_process(self) -> None:
        """Hook called after process execution in timing loop.

        Subclasses can override to implement cleanup or coordination logic.
        Default implementation does nothing.
        """
        pass

    def _before_child_process(self, processes: List["Process"]) -> None:
        """Hook called before child process execution.

        Args:
            processes: List of processes about to be executed

        Subclasses can override to implement coordination logic.
        Default implementation does nothing.

        """
        pass

    def _after_child_process(self, processes: List["Process"]) -> None:
        """Hook called after child process execution.

        Args:
            processes: List of processes that were executed

        Subclasses can override to implement coordination logic.
        Default implementation does nothing.

        """
        pass

    def _initialize_timing(self) -> None:
        """Initialize timing state for execution.

        Sets up timing control fields for this process.
        Can be called by parent processes to initialize child timing state
        before execution begins.
        """
        self.start_time = self.get_time()
        self.execution_count = 0
        self.stop_requested = False

    def start(self) -> None:  # noqa: C901
        """Start timing-driven execution using template method pattern.

        Implements the timing loop structure following the architecture
        document's sequence diagram. Timing strategies are customizable
        through method overrides in subclasses.

        Continues until stop() is called. Handles execution errors gracefully
        by logging and continuing operation (critical for thermal systems).
        """
        self._initialize_timing()
        self.get_logger().info(f"Starting timing-driven execution for process {self.name}")

        while not self.stop_requested:
            try:
                # Template method pattern: calculate when to execute next
                next_tick_time = self._calculate_next_tick_time()
                current_time = self.get_time()

                # Execute if we're at or past the target time
                if current_time >= next_tick_time:
                    # Coordination hooks
                    self._before_process()

                    # Select which processes to execute
                    selected_processes = self._select_processes_to_execute()

                    if selected_processes:
                        # Execute child processes
                        self._before_child_process(selected_processes)
                        self._execute_selected_processes(selected_processes)
                        self._after_child_process(selected_processes)
                    else:
                        # No children - execute this process directly
                        # Subclasses handle their own state management
                        try:
                            self._logger.debug(f"Executing process {self.name} in timing mode")
                            self._process({})
                        except PermissionError:
                            # Permission errors bubble up as programming errors
                            raise
                        except Exception as e:
                            self._logger.error(
                                f"Process {self.name} failed during timing execution: {e}", exc_info=True
                            )
                            # Continue with timing loop (error resilience)

                    self._after_process()
                    self.execution_count += 1

                    self.get_logger().debug(f"Completed timing execution cycle {self.execution_count}")

                # Sleep with stop checking for responsive shutdown
                if not self.stop_requested:
                    next_tick_time = self._calculate_next_tick_time()
                    sleep_time_ns = next_tick_time - self.get_time()

                    if sleep_time_ns > 0:
                        sleep_time_s = sleep_time_ns / 1_000_000_000  # Convert to seconds
                        # Sleep in chunks to check stop_requested frequently
                        while sleep_time_s > 0 and not self.stop_requested:
                            chunk_duration = min(sleep_time_s, 0.1)  # 100ms max chunks
                            time.sleep(chunk_duration)
                            sleep_time_s = (self._calculate_next_tick_time() - self.get_time()) / 1_000_000_000

            except Exception as e:
                # Never abort timing loops - log error and continue
                self.get_logger().error(f"Timing execution failed on cycle {self.execution_count}: {e}", exc_info=True)
                self.execution_count += 1  # Still increment to maintain timing

        self.get_logger().info(f"Stopped timing-driven execution for process {self.name}")

    def stop(self) -> None:
        """Request graceful shutdown of timing-driven execution.

        Sets stop flag that will be checked during sleep cycles and before
        next execution. Shutdown may take up to 100ms (sleep chunk size)
        to complete.
        """
        self.get_logger().info(f"Stop requested for process {self.name}")
        self.stop_requested = True


class Environment(Process, ABC):
    """Abstract base class for environment interfaces.

    Environments interface with the physical or simulated world, reading sensor
    values and applying actuator settings. They can read and modify sensors in
    their output state, but should only read actuators from their input state.
    """

    @abstractmethod
    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Environment-specific implementation."""
        pass


class Controller(Process, ABC):
    """Abstract base class for control logic.

    Controllers implement decision-making logic that determines actuator settings
    based on sensor readings. They can read and modify actuators in their output
    state, but should only read sensors from their input state.
    """

    @abstractmethod
    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Controller-specific implementation."""
        pass
