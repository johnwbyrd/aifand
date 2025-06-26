"""System class for independent timing coordination of multiple thermal.

System class for independent timing coordination of multiple thermal
control flows.
"""

import heapq

from pydantic import Field

from aifand.base.collection import Collection
from aifand.base.process import Process
from aifand.base.state import States


class System(Collection):
    """Independent timing coordination for parallel thermal control.

    Independent timing coordination for parallel thermal control
    coordination.

    System manages multiple Pipelines or other Systems with independent
    timing, where each child executes when its individual timing
    requirements are met. This enables coordination across thermal zones
    with different update rates.

    System queries children for timing preferences and executes ready
    children independently (parallel coordination). Each child manages
    its
    own state.

    Key characteristics:
    - Independent timing: Children execute when ready based on their own
      timing
    - Parallel coordination: Ready children execute independently
    - State isolation: Each child manages its own state
    - Hierarchical composition: Systems can contain other Systems
    """

    # Child process storage as priority queue (next_time, process)
    process_heap: list[tuple[int, Process]] = Field(
        default_factory=list,
        description="Priority queue of (next_execution_time, process) for "
        "parallel coordination",
    )

    # Collection protocol implementation
    def count(self) -> int:
        """Get the number of processes in the system."""
        return len(self.process_heap)

    def append(self, process: Process) -> None:
        """Add a process to the system priority queue."""
        next_time = process.get_next_execution_time()
        heapq.heappush(self.process_heap, (next_time, process))

    def remove(self, name: str) -> bool:
        """Remove a process by name.

        Returns True if removed, False if not found.
        """
        for i, (_, process) in enumerate(self.process_heap):
            if process.name == name:
                # Remove item and re-heapify
                self.process_heap.pop(i)
                heapq.heapify(self.process_heap)
                return True
        return False

    def has(self, name: str) -> bool:
        """Check if a process exists in the system.

        Args:
            name: Name of process to check

        Returns:
            True if process exists

        """
        return any(process.name == name for _, process in self.process_heap)

    def get(self, name: str) -> Process | None:
        """Get a process by name. Returns None if not found."""
        for _, process in self.process_heap:
            if process.name == name:
                return process
        return None

    def get_next_execution_time(self) -> int:
        """Get next execution time based on earliest child's timing.

        System executes when any child is ready, so it delegates timing
        to the earliest child's next execution time.

        Returns:
            Earliest child's next execution time, or system's own time
            if
            no children

        """
        if not self.process_heap:
            # No children - use our own timing
            return super().get_next_execution_time()

        # Return the earliest child's CURRENT timing (not stale heap
        # data)
        earliest_process = self.process_heap[0][1]
        return earliest_process.get_next_execution_time()

    def initialize(self) -> None:
        """Initialize state for system and all children.

        Propagates initialization to all child processes in the
        priority queue to ensure the entire process tree has clean
        state before execution.
        """
        # Initialize our own state
        super().initialize()

        # Initialize all children in priority queue
        for _, process in self.process_heap:
            process.initialize()

    def _get_ready_children(self) -> list[Process]:
        """Get children that are ready to execute based on timing.

        Uses priority queue to efficiently find ready processes.

        Returns:
            List of child processes ready for execution

        """
        if not self.process_heap:
            return []

        ready_processes: list[Process] = []
        current_time = self.get_time()

        # Pop ready processes from the front of the heap
        while self.process_heap:
            next_time, process = self.process_heap[0]

            # Update process timing in case it changed
            actual_next_time = process.get_next_execution_time()

            if actual_next_time <= current_time:
                # Process is ready - remove from heap and add to ready
                # list
                heapq.heappop(self.process_heap)
                ready_processes.append(process)
            elif actual_next_time != next_time:
                # Process timing changed but not ready - update heap
                # entry
                heapq.heappop(self.process_heap)
                heapq.heappush(self.process_heap, (actual_next_time, process))
            else:
                # Process not ready and timing unchanged - stop checking
                break

        return ready_processes

    def _execute(self, states: States) -> States:
        """Execute ready child processes independently.

        System finds children that are ready to execute based on their
        timing and executes them independently. Each child manages its
        own state.

        Args:
            states: Dictionary of named states (typically empty for
                System)

        Returns:
            Dictionary of states (passthrough for System)

        """
        ready_children = self._get_ready_children()

        # Execute ready children independently and update heap with new
        # timing
        for child in ready_children:
            try:
                # Each child manages its own states independently
                child.execute(States())

                # After execution, re-add child to heap with updated
                # execution time (child was already removed from heap by
                # _get_ready_children())
                updated_next_time = child.get_next_execution_time()
                heapq.heappush(self.process_heap, (updated_next_time, child))
            except PermissionError:
                # Permission errors bubble up as programming errors
                raise
            except Exception:
                self._logger.exception(
                    "Child process %s failed in system %s",
                    child.name,
                    self.name,
                )
                # Re-add child to heap even on failure to continue
                # scheduling
                updated_next_time = child.get_next_execution_time()
                heapq.heappush(self.process_heap, (updated_next_time, child))
                continue

        return states
