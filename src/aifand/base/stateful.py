"""StatefulProcess class for state management between executions."""

from typing import Any

from pydantic import Field

from .buffer import Buffer
from .process import Process
from .state import State


class StatefulProcess(Process):
    """Process extension supporting state management between executions.

    StatefulProcess inherits the three-method pattern and adds runtime
    state management capabilities for processes that need memory,
    learning, or historical data analysis.

    StatefulProcess separates configuration (pydantic fields) from
    runtime state (instance attributes):
    - Configuration: PID gains, device names, algorithm parameters
    - Runtime state: Buffer contents, numpy arrays, tensorflow models

    Key characteristics:
    - Buffer for timestamped state storage
    - Runtime state recreated during initialize()
    - Clean serialization of configuration only
    - Foundation for PID controllers, safety controllers, learning
      controllers
    """

    # Configuration fields (serialized)
    buffer_size_limit: int = Field(
        default=1000,
        description="Maximum number of entries to keep in buffer",
        ge=1,
    )

    auto_prune_enabled: bool = Field(
        default=True,
        description="Whether to automatically prune old buffer entries",
    )

    max_age_ns: int = Field(
        default=300_000_000_000,  # 5 minutes in nanoseconds
        description="Maximum age of buffer entries before auto-pruning",
        ge=0,
    )

    def __init__(self, **data: Any) -> None:
        """Initialize StatefulProcess with runtime state setup."""
        super().__init__(**data)
        # Runtime state (not serialized) - recreated in initialize()
        self.buffer: Buffer | None = None

    def initialize(self) -> None:
        """Initialize state for stateful process execution.

        Creates runtime state from configuration. Called before
        execution to ensure clean state.
        """
        super().initialize()

        # Create runtime state from configuration
        self.buffer = Buffer()

    def _import_state(self, states: dict[str, State]) -> None:
        """Store states in buffer with automatic pruning.

        Stateful processes can override this for custom memory
        management.

        Args:
            states: Dictionary of named input states

        """
        if self.buffer is None:
            # Ensure buffer is initialized
            self.initialize()

        # Store current states with timestamp
        current_time = self.get_time()
        if self.buffer is not None:
            self.buffer.store(current_time, states)

        # Auto-prune if enabled
        if self.auto_prune_enabled:
            self._auto_prune()

    def _auto_prune(self) -> None:
        """Automatically prune buffer based on size and age limits."""
        if self.buffer is None:
            return

        # Prune by age
        if self.max_age_ns > 0:
            current_time = self.get_time()
            cutoff_time = current_time - self.max_age_ns
            self.buffer.prune_before(cutoff_time)

        # Prune by size (keep most recent entries)
        while self.buffer.count() > self.buffer_size_limit:
            # Remove oldest entry
            if not self.buffer.is_empty():
                oldest = self.buffer.get_oldest()
                if oldest:
                    # Remove entries up to and including oldest
                    self.buffer.prune_before(oldest[0] + 1)
            else:
                break

    def get_buffer_summary(self) -> dict[str, Any]:
        """Get summary of buffer state for debugging.

        Returns:
            Dictionary with buffer statistics

        """
        if self.buffer is None:
            return {"buffer_initialized": False}

        summary = {
            "buffer_initialized": True,
            "entry_count": self.buffer.count(),
            "is_empty": self.buffer.is_empty(),
        }

        oldest = self.buffer.get_oldest()
        latest = self.buffer.get_latest()

        if oldest:
            summary["oldest_timestamp"] = oldest[0]

        if latest:
            summary["latest_timestamp"] = latest[0]

        if oldest and latest:
            summary["time_span_ns"] = latest[0] - oldest[0]

        return summary
