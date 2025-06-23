"""Runner classes for autonomous execution of thermal management."""

import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Any

from pydantic import Field

from .entity import Entity
from .process import Process


class TimeSource:
    """Thread-local time source discovery for process execution.

    This class manages thread-local storage of runner instances to
    provide time sources for processes executing in different threads.
    The encapsulation allows for future changes to the time source
    discovery mechanism without modifying Process code.
    """

    _thread_locals = threading.local()

    @classmethod
    def set_current(cls, runner: "Runner") -> None:
        """Set time source (runner) for current thread.

        Args:
            runner: The runner instance to use as time source

        """
        cls._thread_locals.runner = runner

    @classmethod
    def get_current(cls) -> "Runner | None":
        """Get time source (runner) for current thread.

        Returns:
            The runner instance for this thread, or None if not set

        """
        return getattr(cls._thread_locals, "runner", None)

    @classmethod
    def clear_current(cls) -> None:
        """Clear time source for current thread."""
        if hasattr(cls._thread_locals, "runner"):
            del cls._thread_locals.runner


class Runner(Entity, ABC):
    """Base class for autonomous execution of processes.

    Runner manages the execution lifecycle of a main process, calling
    its execute() method according to the process's timing preferences.
    Runner respects get_next_execution_time() and sleeps between
    executions.

    Key characteristics:
    - Runs in separate thread for non-blocking operation
    - Respects process timing preferences
    - Provides time source for executed processes
    - Handles graceful shutdown
    - Initializes process timing state on start
    """

    main_process: Process = Field(
        description="The root process to execute autonomously"
    )

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}."
            f"{self.name}"
        )
        self._thread: threading.Thread | None = None
        self._stop_requested = False

    @abstractmethod
    def get_time(self) -> int:
        """Get current time in nanoseconds.

        Returns:
            Current time in nanoseconds

        """

    @abstractmethod
    def _execution_loop(self) -> None:
        """Main execution loop run in separate thread."""

    def start(self) -> None:
        """Start autonomous execution in background thread.

        Initializes the main process's timing state and starts a thread
        that executes the process according to its timing preferences.

        Raises:
            RuntimeError: If runner is already started

        """
        if self._thread and self._thread.is_alive():
            raise RuntimeError(f"Runner {self.name} already started")

        self._logger.info(f"Starting runner {self.name}")

        # Initialize timing state for entire process tree
        self.main_process.initialize_timing()

        # Start execution thread
        self._stop_requested = False
        self._thread = threading.Thread(
            target=self._execution_loop,
            name=f"Runner-{self.name}",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop autonomous execution gracefully.

        Signals the execution thread to stop and waits for it to finish.
        """
        if not self._thread:
            return

        self._logger.info(f"Stopping runner {self.name}")
        self._stop_requested = True

        # Wait for thread to finish
        self._thread.join(timeout=5.0)
        if self._thread.is_alive():
            self._logger.warning(
                f"Runner {self.name} thread did not stop within timeout"
            )

        self._thread = None

    def is_running(self) -> bool:
        """Check if runner is currently executing.

        Returns:
            True if execution thread is active

        """
        return self._thread is not None and self._thread.is_alive()

    def _execute_process_once(self) -> None:
        """Execute the main process once.

        This method is shared between different runner implementations.
        The template method pattern in Process.execute() automatically
        handles execution count updates.
        """
        self._logger.debug(f"Executing {self.main_process.name}")
        self.main_process.execute({})


class StandardRunner(Runner):
    """Standard runner that respects real-time execution.

    StandardRunner executes the main process according to its timing
    preferences, sleeping between executions to maintain proper
    intervals. This is the normal production runner for thermal
    management.
    """

    def get_time(self) -> int:
        """Get current monotonic time in nanoseconds.

        Returns:
            Current time from time.monotonic_ns()

        """
        return time.monotonic_ns()

    def _execution_loop(self) -> None:
        """Main execution loop that respects process timing."""
        # Set ourselves as time source for this thread
        TimeSource.set_current(self)

        try:
            while not self._stop_requested:
                try:
                    # Get next execution time from process
                    next_time = self.main_process.get_next_execution_time()
                    current_time = self.get_time()

                    if next_time <= current_time:
                        # Ready to execute
                        self._execute_process_once()
                    else:
                        # Sleep until next execution
                        sleep_duration = (
                            next_time - current_time
                        ) / 1_000_000_000.0  # ns to seconds
                        if sleep_duration > 0:
                            time.sleep(sleep_duration)

                except Exception as e:
                    # Log error but continue execution
                    self._logger.error(
                        f"Error in execution loop: {e}", exc_info=True
                    )
                    # Brief sleep to prevent tight error loop
                    time.sleep(0.1)

        finally:
            # Clean up thread-local storage
            TimeSource.clear_current()
            self._logger.info(f"Runner {self.name} execution loop ended")


class FastRunner(Runner):
    """Test runner that accelerates time for rapid testing.

    FastRunner manipulates time to execute processes as quickly as
    possible without waiting for real time to pass. This enables rapid
    testing of long-term thermal behavior and timing scenarios.

    Key characteristics:
    - Maintains internal simulation time
    - Advances time instantly to next execution
    - No sleeping between executions
    - Deterministic test execution
    """

    # Test execution control
    max_duration_ns: int = Field(
        default=3600_000_000_000,  # 1 hour in nanoseconds
        description="Maximum simulation duration to prevent infinite loops",
    )

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._simulation_time = 0
        self._start_time = 0

    def get_time(self) -> int:
        """Get current simulation time in nanoseconds.

        Returns:
            Current simulation time

        """
        return self._simulation_time

    def _advance_time_to(self, target_time: int) -> None:
        """Advance simulation time to target.

        Args:
            target_time: Time to advance to in nanoseconds

        """
        if target_time > self._simulation_time:
            self._simulation_time = target_time

    def _should_continue_execution(self) -> bool:
        """Check if execution should continue.

        Checks stop flag and safety limits to determine if execution
        should continue.

        Returns:
            True if execution should continue

        """
        if self._stop_requested:
            return False

        # Safety check for runaway time
        if self._simulation_time - self._start_time > self.max_duration_ns:
            self._logger.warning("FastRunner exceeded max duration, stopping")
            return False

        return True

    def _execute_one_cycle(self) -> None:
        """Execute one cycle if process is ready."""
        next_time = self.main_process.get_next_execution_time()

        if next_time <= self._simulation_time:
            # Ready to execute
            self._execute_process_once()
        else:
            # Jump time forward to next execution
            self._advance_time_to(next_time)

    def run_for_duration(self, duration_seconds: float) -> None:
        """Run simulation for specified duration without delays.

        Args:
            duration_seconds: Simulation duration in seconds

        """
        # Set ourselves as time source first
        self._simulation_time = 0
        self._start_time = 0
        TimeSource.set_current(self)

        # Initialize timing (will use simulation time source)
        self.main_process.initialize_timing()

        try:
            end_time = self._simulation_time + int(
                duration_seconds * 1_000_000_000
            )

            while (
                self._simulation_time < end_time
                and self._should_continue_execution()
            ):
                self._execute_one_cycle()

        finally:
            TimeSource.clear_current()

    def _execution_loop(self) -> None:
        """FastRunner uses run_for_duration instead of threading.

        This runner doesn't support threaded execution - use
        run_for_duration().
        """
        # This runner doesn't use threaded execution
        raise NotImplementedError(
            "FastRunner uses run_for_duration() instead of start()"
        )

    def start(self) -> None:
        """FastRunner doesn't support threaded execution."""
        raise NotImplementedError(
            "FastRunner uses run_for_duration() instead of start()"
        )
