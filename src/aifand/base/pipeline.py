"""Pipeline class for single thermal control flows with timing and state persistence."""

import time
from typing import Dict

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
        default_factory=dict, 
        description="Named states that persist between timing-driven executions"
    )
    
    # Timing configuration  
    interval_ns: int = Field(
        default=100_000_000,  # 100ms in nanoseconds
        description="Execution interval in nanoseconds for timing-driven mode"
    )
    
    # Runtime control (important for remote monitoring and debugging)
    start_time: int = Field(default=0, description="Start time of current timing loop execution (nanoseconds)")
    execution_count: int = Field(default=0, description="Number of completed execution cycles")
    stop_requested: bool = Field(default=False, description="Whether stop has been requested")
    
    def get_time(self) -> int:
        """Get current time in nanoseconds.
        
        Returns nanosecond timestamp. Can be overridden by subclasses to use
        alternative time sources like GPS clocks, NTP synchronization, or
        other high-precision timing sources.
        
        Returns:
            Current time in nanoseconds since epoch
        """
        return time.time_ns()
    
    def start(self) -> None:
        """Start timing-driven execution using persistent states.
        
        Runs autonomous timing loop that repeatedly calls execute() on self.states
        with consistent interval timing. Uses modulo-based scheduling to ensure
        consistent intervals regardless of execution duration.
        
        Continues until stop() is called. Handles execution errors gracefully
        by logging and continuing operation (critical for thermal systems).
        """
        self.start_time = self.get_time()
        self.execution_count = 0
        self.stop_requested = False
        
        self.get_logger().info(f"Starting timing-driven execution for pipeline {self.name}")
        
        while not self.stop_requested:
            # Calculate target execution time using modulo-based scheduling
            target_time = self.start_time + (self.execution_count * self.interval_ns)
            current_time = self.get_time()
            
            # Execute pipeline if we're at or past target time
            if current_time >= target_time:
                try:
                    self.get_logger().debug(f"Executing pipeline cycle {self.execution_count}")
                    # Execute pipeline and update persistent states
                    self.states = self.execute(self.states)
                    self.execution_count += 1
                except Exception as e:
                    # Never abort thermal control loops - log error and continue
                    self.get_logger().error(
                        f"Pipeline execution failed on cycle {self.execution_count}: {e}", 
                        exc_info=True
                    )
                    self.execution_count += 1  # Still increment to maintain timing
            
            # Sleep with stop checking for responsive shutdown
            if not self.stop_requested:
                next_target = self.start_time + (self.execution_count * self.interval_ns)
                sleep_time_ns = next_target - self.get_time()
                
                if sleep_time_ns > 0:
                    sleep_time_s = sleep_time_ns / 1_000_000_000  # Convert to seconds for time.sleep()
                    # Sleep in chunks to check stop_requested frequently
                    while sleep_time_s > 0 and not self.stop_requested:
                        chunk_duration = min(sleep_time_s, 0.1)  # 100ms max chunks
                        time.sleep(chunk_duration)
                        sleep_time_s = (next_target - self.get_time()) / 1_000_000_000
        
        self.get_logger().info(f"Stopped timing-driven execution for pipeline {self.name}")
    
    def stop(self) -> None:
        """Request graceful shutdown of timing-driven execution.
        
        Sets stop flag that will be checked during sleep cycles and before
        next execution. Shutdown may take up to 100ms (sleep chunk size)
        to complete.
        """
        self.get_logger().info(f"Stop requested for pipeline {self.name}")
        self.stop_requested = True
    
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
        self.get_logger().warning(
            f"Pipeline {self.name} has no children - no Environment or Controllers configured"
        )
        return states