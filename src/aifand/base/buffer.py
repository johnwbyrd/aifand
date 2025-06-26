"""Buffer class for timestamped state storage."""

from typing import Any

from pydantic import ConfigDict

from .entity import Entity
from .state import State


class Buffer(Entity):
    """Timestamped state storage for StatefulProcess implementations.

    Buffer maintains chronologically ordered States with nanosecond
    timestamps, supporting time-based queries, automatic aging, and
    efficient access patterns for thermal control algorithms.

    Buffer abstracts timing complexity from thermal algorithms:
    - PID controllers query Buffer for derivative calculations
    - Safety controllers monitor Buffer for temperature spike detection
    - Learning controllers access Buffer for training data
    """

    model_config = ConfigDict(frozen=False)

    def __init__(self, **data: Any) -> None:
        """Initialize Buffer with internal storage."""
        super().__init__(**data)
        # Private attribute for internal storage
        self._entries: list[tuple[int, dict[str, State]]] = []

    def store(self, timestamp: int, states: dict[str, State]) -> None:
        """Store states with timestamp.

        States are stored in chronological order for efficient access.

        Args:
            timestamp: Nanosecond timestamp
            states: Dictionary of named states to store

        """
        # Insert in chronological order (simple insertion sort for now)
        # For production, consider more efficient data structures
        entry = (timestamp, states.copy())

        # Find insertion point to maintain chronological order
        insert_index = len(self._entries)
        for i, (existing_timestamp, _) in enumerate(self._entries):
            if timestamp < existing_timestamp:
                insert_index = i
                break

        self._entries.insert(insert_index, entry)

    def get_recent(
        self, duration_ns: int
    ) -> list[tuple[int, dict[str, State]]]:
        """Get entries from the last duration_ns nanoseconds.

        Args:
            duration_ns: Duration in nanoseconds to look back

        Returns:
            List of (timestamp, states) tuples in chronological order

        """
        if not self._entries:
            return []

        # Find cutoff time
        latest_timestamp = self._entries[-1][0]
        cutoff_time = latest_timestamp - duration_ns

        # Find first entry within duration
        result = []
        for timestamp, states in self._entries:
            if timestamp >= cutoff_time:
                result.append((timestamp, states))

        return result

    def get_range(
        self, start_ns: int, end_ns: int
    ) -> list[tuple[int, dict[str, State]]]:
        """Get entries within specified time range.

        Args:
            start_ns: Start time in nanoseconds (inclusive)
            end_ns: End time in nanoseconds (inclusive)

        Returns:
            List of (timestamp, states) tuples in chronological order

        """
        result = []
        for timestamp, states in self._entries:
            if start_ns <= timestamp <= end_ns:
                result.append((timestamp, states))

        return result

    def prune_before(self, timestamp: int) -> int:
        """Remove entries before specified timestamp.

        Args:
            timestamp: Remove entries before this time

        Returns:
            Number of entries removed

        """
        original_count = len(self._entries)

        # Find first entry to keep
        keep_index = 0
        for i, (entry_timestamp, _) in enumerate(self._entries):
            if entry_timestamp >= timestamp:
                keep_index = i
                break
        else:
            # All entries are before timestamp
            keep_index = len(self._entries)

        # Remove entries before keep_index
        self._entries = self._entries[keep_index:]

        return original_count - len(self._entries)

    def count(self) -> int:
        """Get number of stored entries."""
        return len(self._entries)

    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return len(self._entries) == 0

    def clear(self) -> None:
        """Remove all entries from buffer."""
        self._entries.clear()

    def get_latest(self) -> tuple[int, dict[str, State]] | None:
        """Get the most recent entry.

        Returns:
            Latest (timestamp, states) tuple or None if empty

        """
        if not self._entries:
            return None
        return self._entries[-1]

    def get_oldest(self) -> tuple[int, dict[str, State]] | None:
        """Get the oldest entry.

        Returns:
            Oldest (timestamp, states) tuple or None if empty

        """
        if not self._entries:
            return None
        return self._entries[0]
