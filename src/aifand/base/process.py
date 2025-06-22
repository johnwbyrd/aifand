"""Process classes for thermal management system execution."""

import copy
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from pydantic import Field

from .entity import Entity
from .state import State


class Process(Entity, ABC):
    """Base class for computational units that transform thermal management data.

    A Process represents a computational unit that transforms states within the system.
    Processes can contain child processes that execute in serial order, forming
    execution pipelines. Each process receives a dictionary of named states and
    produces a transformed dictionary of states.

    Key characteristics:
    - Stateless: No data persists between execute() calls
    - Pipeline: Child processes execute serially with state passthrough
    - Error resilient: Exceptions are caught, logged, and execution continues
    - Immutable: Input states are never modified (deep copy used)

    Subclasses must implement _execute_impl() to define their specific logic.
    """

    children: List["Process"] = Field(
        default_factory=list, description="Ordered list of child processes for pipeline execution"
    )

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
                return self._execute_impl(result_states)
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
                except Exception as e:
                    self._logger.error(
                        f"Child process {child.name} (index {i}) failed in {self.name} pipeline: {e}", exc_info=True
                    )
                    # Continue with current states (passthrough behavior)
                    continue

            return result_states

    @abstractmethod
    def _execute_impl(self, states: Dict[str, State]) -> Dict[str, State]:
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

    def add_child(self, child: "Process") -> "Process":
        """Return a new Process with the given child added to the pipeline.

        Since Process is immutable, this returns a new instance rather than
        modifying the current one.

        Args:
            child: Process to add to the end of the pipeline

        Returns:
            New Process instance with the child added

        """
        new_children = list(self.children) + [child]
        return self.__class__(
            uuid=self.uuid,
            name=self.name,
            children=new_children,
            **{k: v for k, v in self.model_dump().items() if k not in ["uuid", "name", "children"]},
        )

    def get_logger(self) -> logging.Logger:
        """Get the logger instance for this process."""
        return self._logger


class Environment(Process, ABC):
    """Abstract base class for environment interfaces.

    Environments interface with the physical or simulated world, reading sensor
    values and applying actuator settings. They can read and modify sensors in
    their output state, but should only read actuators from their input state.
    """

    @abstractmethod
    def _execute_impl(self, states: Dict[str, State]) -> Dict[str, State]:
        """Environment-specific implementation."""
        pass


class Controller(Process, ABC):
    """Abstract base class for control logic.

    Controllers implement decision-making logic that determines actuator settings
    based on sensor readings. They can read and modify actuators in their output
    state, but should only read sensors from their input state.
    """

    @abstractmethod
    def _execute_impl(self, states: Dict[str, State]) -> Dict[str, State]:
        """Controller-specific implementation."""
        pass
