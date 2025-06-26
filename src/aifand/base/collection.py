"""A collection of processes, executed serially or in parallel."""

from abc import ABC, abstractmethod

from aifand.base.process import Process


class Collection(Process, ABC):
    """A collection of processes, executed serially or in parallel.

    This class represents a collection of processes that can be executed
    either one after another (serially) or all at once (in parallel).
    It inherits from the Entity class to provide unique identification
    and naming capabilities.

    Note that a Collection does not specify an internal container type!
    This is Python and we use duck typing. Any object that can store a
    bunch of processes, can be asked what time the next process(es)
    wants to be executed, and can execute it or them, is valid as a
    Collection.

    Collections are purely coordination abstractions - they contain no
    data structures themselves, just the protocol for managing
    processes.
    """

    @abstractmethod
    def count(self) -> int:
        """Get the number of processes in the collection."""

    @abstractmethod
    def append(self, process: Process) -> None:
        """Add a process to the collection."""

    @abstractmethod
    def remove(self, name: str) -> bool:
        """Remove a process by name.

        Returns True if removed, False if not found.
        """

    @abstractmethod
    def has(self, name: str) -> bool:
        """Check if a process with the given name exists.

        Returns True if found in the collection.
        """

    @abstractmethod
    def get(self, name: str) -> Process | None:
        """Get a process by name. Returns None if not found."""
