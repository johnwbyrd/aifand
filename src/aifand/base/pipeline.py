"""Pipeline class for single thermal control flows with timing and state persistence."""

from typing import Dict, List

from pydantic import Field

from .process import Controller, Environment, Process
from .state import State


class Pipeline(Process):
    """Sequential execution unit for thermal control with timing and state persistence.

    Pipeline manages a single logical control flow (e.g., CPU thermal management)
    through Environment → Controllers stages. It maintains named states that persist
    between executions and provides timing control for autonomous operation.

    Pipeline can operate in two ways:
    - Timing-driven: start() runs autonomous timing loop using persistent states
    - Process execution: execute() called by parent System, processes input states

    The same execute() method handles both cases - timing-driven mode calls it
    repeatedly on persistent states, process execution ignores persistent states.
    """

    # Persistent state for timing-driven execution
    states: Dict[str, State] = Field(
        default_factory=dict, description="Named states that persist between timing-driven executions"
    )

    # Timing configuration
    interval_ns: int = Field(
        default=100_000_000,  # 100ms in nanoseconds
        description="Execution interval in nanoseconds for timing-driven mode",
    )

    # Runtime control (important for remote monitoring and debugging)
    start_time: int = Field(default=0, description="Start time of current timing loop execution (nanoseconds)")
    execution_count: int = Field(default=0, description="Number of completed execution cycles")
    stop_requested: bool = Field(default=False, description="Whether stop has been requested")

    def _calculate_next_tick_time(self) -> int:
        """Calculate when the next execution should occur using unified timing.

        Pipeline implements unified timing where all children execute together
        at the same interval. Uses modulo-based scheduling for consistent
        intervals regardless of execution duration.

        Returns:
            Nanosecond timestamp when next execution should occur

        """
        return self.start_time + (self.execution_count * self.interval_ns)

    def _select_processes_to_execute(self) -> List[Process]:
        """Select child processes for unified execution.

        Pipeline implements unified timing where all children execute together
        at shared intervals, preserving serial execution order.

        Returns:
            List of all child processes for unified execution

        """
        return self.children

    def _execute_selected_processes(self, processes: List[Process]) -> None:
        """Execute selected child processes and update persistent states.

        Overrides the default implementation to handle Pipeline's persistent
        state management during timing-driven execution.

        Args:
            processes: List of processes ready for execution

        """
        if not processes:
            # No children - execute this pipeline's logic directly
            try:
                self.get_logger().debug(f"Executing pipeline {self.name} with no children")
                self.states = self._process(self.states)
            except PermissionError:
                # Permission errors bubble up as programming errors
                raise
            except Exception as e:
                self.get_logger().error(f"Pipeline {self.name} failed during timing execution: {e}", exc_info=True)
                # Continue with timing loop (error resilience)
            return

        # Execute children as serial pipeline and update persistent states
        try:
            self.get_logger().debug(f"Executing pipeline {self.name} with {len(processes)} children")
            self.states = self.execute(self.states)
        except PermissionError:
            # Permission errors bubble up as programming errors
            raise
        except Exception as e:
            self.get_logger().error(f"Pipeline {self.name} failed during timing execution: {e}", exc_info=True)
            # Continue with timing loop (error resilience)

    def set_environment(self, environment: Environment) -> None:
        """Set the Environment process as the first child in the pipeline.

        Replaces any existing Environment and places it before all Controllers.
        Following thermal control convention, Environment should execute first
        to read sensor values.

        Args:
            environment: Environment process to set as first pipeline stage

        """
        # Remove any existing Environment processes
        self.children = [child for child in self.children if not isinstance(child, Environment)]

        # Insert Environment at the beginning
        self.children.insert(0, environment)

        self.get_logger().debug(f"Set environment {environment.name} for pipeline {self.name}")

    def add_controller(self, controller: Controller) -> None:
        """Add a Controller process after the Environment in the pipeline.

        Controllers are added in the order they are registered and execute
        after the Environment. This follows thermal control convention where
        Environment reads sensors first, then Controllers process the data.

        Args:
            controller: Controller process to add to the pipeline

        """
        self.children.append(controller)
        self.get_logger().debug(f"Added controller {controller.name} to pipeline {self.name}")

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Handle Pipeline-specific state transformation when no children exist.

        This is called when Pipeline has no children (unusual case). Normally
        Pipeline will have Environment + Controllers as children, so the inherited
        execute() method executes the children pipeline instead of calling this.

        Args:
            states: Dictionary of states to transform

        Returns:
            Dictionary of states (passthrough when no children)

        """
        self.get_logger().warning(f"Pipeline {self.name} has no children - no Environment or Controllers configured")
        return states
