"""System class for independent timing coordination of multiple thermal control flows."""

from typing import Dict, List

from .process import Process
from .state import State


class System(Process):
    """Independent timing coordination for multiple thermal control flows.

    System manages multiple Pipelines or other Systems with independent timing,
    where each child executes when its individual timing requirements are met.
    This enables coordination across thermal zones with different update rates
    and thermal characteristics.

    System queries children for timing preferences rather than imposing intervals,
    implementing an "ask-don't-tell" coordination model that respects individual
    child timing needs while maintaining execution order based on readiness.

    Key characteristics:
    - Independent timing: Children execute when ready, not in predetermined order
    - Uniform child handling: Treats Pipeline and System children uniformly through Process interface
    - State isolation: Each child manages its own state by default
    - Coordination hooks: Enable parent-child communication without automatic state sharing
    - Hierarchical composition: Systems can contain other Systems for scalable coordination
    """

    def _calculate_next_tick_time(self) -> int:
        """Calculate when the next execution should occur using independent timing.

        System queries all children for their timing preferences and returns
        the earliest requested time. This implements the "ask-don't-tell"
        coordination model where children express timing needs.

        Returns:
            Nanosecond timestamp when next execution should occur

        """
        if not self.children:
            # No children - use our own interval
            return self.start_time + (self.execution_count * self.interval_ns)

        # Query all children for their timing preferences
        earliest_time = None
        current_time = self.get_time()

        for child in self.children:
            # Initialize child timing if needed
            if not hasattr(child, "start_time") or child.start_time == 0:
                child._initialize_timing()

            # Get child's preferred execution time
            child_next_time = child._calculate_next_tick_time()

            if earliest_time is None or child_next_time < earliest_time:
                earliest_time = child_next_time

        return earliest_time if earliest_time is not None else current_time

    def _select_processes_to_execute(self) -> List[Process]:
        """Select child processes ready for execution based on timing.

        Returns children whose next execution time is less than or equal
        to current time, enabling independent timing coordination.

        Returns:
            List of child processes ready for execution

        """
        if not self.children:
            return []

        ready_processes = []
        current_time = self.get_time()

        for child in self.children:
            # Ensure child timing is initialized
            if not hasattr(child, "start_time") or child.start_time == 0:
                child._initialize_timing()

            # Check if child is ready to execute
            child_next_time = child._calculate_next_tick_time()
            if child_next_time <= current_time:
                ready_processes.append(child)

        return ready_processes

    def _execute_selected_processes(self, processes: List[Process]) -> None:
        """Execute ready children independently and update persistent states.

        Overrides default implementation to handle System's persistent
        state management during timing-driven execution. Each child
        manages its own state with isolation by default.

        Args:
            processes: List of processes ready for execution

        """
        if not processes:
            # No children ready - execute this system's logic directly
            try:
                self.get_logger().debug(f"Executing system {self.name} with no ready children")
                self._process({})
            except PermissionError:
                # Permission errors bubble up as programming errors
                raise
            except Exception as e:
                self.get_logger().error(f"System {self.name} failed during timing execution: {e}", exc_info=True)
                # Continue with timing loop (error resilience)
            return

        # Execute ready children independently
        for process in processes:
            try:
                self.get_logger().debug(f"Executing ready child process: {process.name}")
                # Children manage their own states independently
                process.execute({})

            except PermissionError:
                # Permission errors bubble up as programming errors
                raise
            except Exception as e:
                self.get_logger().error(
                    f"Child process {process.name} failed during System timing execution: {e}", exc_info=True
                )
                # Continue with other processes (error resilience for thermal systems)
                continue

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Handle System-specific state transformation when no children exist.

        This is called when System has no children (edge case). Normally
        System will have Pipeline or System children, so the inherited
        execute() method executes the children instead of calling this.

        Args:
            states: Dictionary of states to transform

        Returns:
            Dictionary of states (passthrough when no children)

        """
        self.get_logger().warning(f"System {self.name} has no children - no Pipelines or Systems configured")
        return states
