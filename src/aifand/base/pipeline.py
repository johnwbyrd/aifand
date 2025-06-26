"""Pipeline class for single thermal control flows."""

from pydantic import Field

from .collection import Collection
from .process import Process
from .state import State


class Pipeline(Collection):
    """Sequential execution unit for serial thermal control.

    Pipeline manages a single logical control flow by executing child
    processes sequentially in order. It passes states through children
    serially: input → child1.execute() → child2.execute() → ... → output

    Pipeline maintains its own execution rate and coordinates timing,
    but does not store persistent state - it's a pure coordinator.
    """

    # Child process storage for serial execution
    children: list[Process] = Field(
        default_factory=list,
        description="Ordered list of child processes for serial execution",
    )

    # Collection protocol implementation
    def count(self) -> int:
        """Get the number of processes in the pipeline."""
        return len(self.children)

    def append(self, process: Process) -> None:
        """Add a process to the end of the pipeline."""
        self.children.append(process)

    def remove(self, name: str) -> bool:
        """Remove a process by name.

        Returns True if removed, False if not found.
        """
        for i, child in enumerate(self.children):
            if child.name == name:
                self.children.pop(i)
                return True
        return False

    def has(self, name: str) -> bool:
        """Check if a process exists in the pipeline.

        Args:
            name: Name of process to check

        Returns:
            True if process exists

        """
        return any(child.name == name for child in self.children)

    def get(self, name: str) -> Process | None:
        """Get a process by name. Returns None if not found."""
        for child in self.children:
            if child.name == name:
                return child
        return None

    def initialize(self) -> None:
        """Initialize state for pipeline and all children.

        Propagates initialization to all child processes to
        ensure the entire process tree has clean state before
        execution.
        """
        # Initialize our own state
        super().initialize()

        # Initialize all children
        for child in self.children:
            child.initialize()

    def _execute(self, states: dict[str, State]) -> dict[str, State]:
        """Execute child processes serially.

        Passes states through children sequentially:
        input → child1.execute() → child2.execute() → ... → output

        Args:
            states: Dictionary of named states to transform

        Returns:
            Dictionary of transformed states after serial execution

        """
        current_states = states

        # Execute children serially, passing states through the pipeline
        for child in self.children:
            try:
                current_states = child.execute(current_states)
            except PermissionError:
                # Permission errors bubble up as programming errors
                raise
            except Exception:
                self._logger.exception(
                    "Child process %s failed in pipeline %s",
                    child.name,
                    self.name,
                )
                # Continue with next child (error resilience)
                continue

        return current_states
