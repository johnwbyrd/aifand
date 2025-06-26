# aifand Architecture

This document outlines the software architecture for `aifand`, an adaptive thermal management system designed for both local and remote operation across multiple network protocols.

## Core Philosophy

The `aifand` architecture automatically discovers and learns the thermal properties of hardware without manual configuration. It separates pure data (`State`) from logic that transforms it (`Process`), enabling complex behaviors through composable building blocks. The system supports multiple network protocols for remote monitoring and control while maintaining a single source of truth through pydantic models.

## Key Abstractions and Data Models

### Entity

The `Entity` class serves as the foundational base for all objects within the system. Each entity has a unique identifier (`uuid`) and human-readable name, with support for arbitrary additional properties through pydantic's `extra="allow"` configuration.

Implementation details include inheritance from `pydantic.BaseModel` with `frozen=True` for immutability, automatic UUID generation via `uuid4()` if not provided, support for arbitrary key-value pairs alongside core fields, full JSON serialization and deserialization support, and string representation showing all fields for debugging.

All core classes (`Device`, `Process`, `Collection`, `Runner`) inherit from `Entity` to ensure consistent identification, serialization, and extensibility across the architecture.

### Data Models

The `Device` class represents a single interface point with hardware. It extends Entity with a flexible properties dictionary storing arbitrary key-value pairs like value, min, max, label, hwmon_path, scale, and unit. Standard property naming conventions ensure consistency across thermal management operations.

Two specialized device types exist: `Sensor` for reporting values from the environment (temperature, fan RPM), and `Actuator` for performing actions (fan PWM control, thermal limits).

A `State` represents a snapshot of device properties at a specific moment, implemented as an immutable collection of Devices indexed by name. States are unopinionated about their meaning; their role (like "actual" or "desired") is defined by how a `Process` uses them. States provide helper methods for device access, addition, and removal while maintaining immutability through copy-on-write semantics.

### Process

The `Process` class represents computational units that transform thermal management data. Process provides a template method `execute()` that calls `_execute()` and automatically updates execution count. The default `_execute()` implementation uses a three-method pattern: `_import_state()`, `_think()`, and `_export_state()`, enabling both stateless and stateful process implementations through selective method overriding.

Process execution follows the pattern: input states → `_import_state()` → `_think()` → `_export_state()` → output states. Stateless processes override only `_think()` for computation. Stateful processes override `_import_state()` to update internal memory and `_think()` to use historical data. Advanced processes override all three methods for custom data format conversion (State ↔ numpy/tensorflow).

Process includes timing infrastructure with `interval_ns` field for execution intervals, `start_time` for timing loop initialization, `execution_count` for tracking completed cycles, and `get_next_execution_time()` method for calculating when next execution should occur using modulo timing. The timing system uses nanosecond precision with `get_time()` method that automatically uses runner-provided time sources when available, falling back to `time.monotonic_ns()`.

Process execution characteristics include immutable data flow where input states are never modified, error resilience where exceptions are caught and logged without aborting thermal control, per-process logging with hierarchical logger names, and progressive complexity through the three-method pattern.

Device modification permissions enforce thermal management domain rules through runtime validation. Environment processes can read and modify Sensors but can only read Actuators from their input state (hardware interface responsibility), while Controller processes can only modify Actuators but can only read Sensors from their input state (decision-making responsibility). This separation prevents Controllers from corrupting sensor readings and prevents Environments from bypassing controller decisions. Permission checking uses call stack inspection to identify the modifying process and validates against a class-based permission matrix.

An `Environment` can read and modify sensors but should only read actuators from its input state. A `Controller` can read and modify actuators but should only read sensors from its input state.

### StatefulProcess

The `StatefulProcess` class extends Process to support state management between executions. StatefulProcess inherits the three-method pattern and adds runtime state management capabilities for processes that need memory, learning, or historical data analysis.

StatefulProcess separates configuration (pydantic fields) from runtime state (instance attributes). Configuration includes settings like PID gains, device names, and algorithm parameters that get serialized for persistence and network transfer. Runtime state includes Buffer contents, numpy arrays, tensorflow models, and computed values that are recreated during `initialize()`.

StatefulProcess provides a foundation for thermal management algorithms requiring historical context. PID controllers use StatefulProcess with Buffer for error history and integral terms. Safety controllers use StatefulProcess for monitoring temperature trends and detecting thermal runaway. Learning controllers use StatefulProcess for training data accumulation and model state management.

The key insight is that StatefulProcess maintains algorithm-specific memory while preserving the clean State-based interface for inter-process communication. Internal memory serves computational needs while States provide standardized data exchange across the thermal management pipeline.

### Buffer

The `Buffer` class provides timestamped state storage for StatefulProcess implementations. Buffer maintains chronologically ordered States with nanosecond timestamps, supporting time-based queries, automatic aging, and efficient access patterns for thermal control algorithms.

Buffer operations include `store(timestamp, states)` for adding new data, `get_recent(duration_ns)` for sliding window access, `get_range(start_ns, end_ns)` for arbitrary time ranges, and `prune_before(timestamp)` for memory management. Buffer implementations can use circular buffers, linked lists, or database storage depending on performance and persistence requirements.

Buffer abstracts timing complexity from thermal algorithms. PID controllers query Buffer for derivative calculations without managing timestamps. Safety controllers monitor Buffer for temperature spike detection without implementing time-series logic. Learning controllers access Buffer for training data without managing data lifecycle.

Buffer provides the temporal foundation that enables sophisticated thermal management while keeping controller implementations focused on their domain logic rather than data structure management.

### Collection

The `Collection` class defines the coordination protocol for managing multiple processes. Collection inherits from Process and adds abstract methods for process management: `count()` returns the number of processes, `append()` adds a process, `remove()` removes a process by name, `has()` checks if a process exists, and `get()` retrieves a process by name.

Collection uses duck typing and specifies no internal container type. Any object that can store processes, determine execution timing, and coordinate execution is a valid Collection implementation. Collections are coordination abstractions containing no data structures themselves, just the protocol for managing processes.

Collection inherits timing capabilities from Process, allowing Collections to participate in hierarchical timing coordination while implementing their own storage and execution strategies. Collections propagate `initialize()` to all child processes to ensure clean state throughout the process hierarchy.

### Pipeline

The `Pipeline` class implements serial execution coordination for thermal control flows. Pipeline inherits from Collection and manages an ordered list of child processes in its `children` field, executing them sequentially where each child's output becomes the next child's input.

Pipeline execution passes states through children serially: input → child1.execute() → child2.execute() → ... → output. The `execute()` method iterates through children, calling each child's execute method with the current states and passing the result to the next child. Error handling catches exceptions, logs them, and continues with the next child to maintain thermal control operation.

Collection protocol implementation uses the children list directly: `count()` returns `len(children)`, `append()` adds to the list, `remove()` searches by name and removes matching processes, and `has()`/`get()` search the list by process name.

Pipeline maintains its own execution timing inherited from Process but does not store persistent state between executions. It coordinates timing for serial execution while children manage their own internal state.

### System

The `System` class implements parallel execution coordination for multiple independent thermal control flows. System inherits from Collection and manages child processes in a priority queue implemented as `process_heap: List[Tuple[int, Process]]` using Python's `heapq` module for efficient timing-based coordination.

System execution finds processes ready to execute based on their individual timing preferences. The `_get_ready_children()` method queries the priority queue to find processes whose `get_next_execution_time()` is less than or equal to current time. Ready processes execute independently with empty states (state isolation), and after execution they are re-added to the priority queue with updated next execution times.

System delegates its own timing to children through `get_next_execution_time()`, which returns the earliest child's next execution time rather than using System's own timing interval. This enables event-driven coordination where System executes precisely when children need to execute, avoiding polling.

Collection protocol implementation operates on the priority queue: `append()` calculates the process's next execution time and pushes it onto the heap, `remove()` searches the heap and re-heapifies after removal, and `has()`/`get()` search through heap tuples by process name.

System enables coordination across thermal zones with different update rates and characteristics. Children execute when ready based on their individual timing requirements rather than synchronized intervals, allowing CPU thermal management at 100ms intervals while storage thermal management operates at 1000ms intervals within the same System.

### Runner

The `Runner` class provides autonomous execution management for thermal management processes. Runner manages the execution lifecycle, calling a main process's `execute()` method according to the process's timing preferences while running in a separate thread for non-blocking operation.

The `TimeSource` class encapsulates time source discovery using thread-local storage, enabling different runners to provide different time sources to processes executing in their threads. This abstraction supports both real-time execution and accelerated simulation testing.

`StandardRunner` implements production execution that respects real-time timing, sleeping between executions to maintain proper intervals. It provides monotonic time to executed processes and handles graceful shutdown with proper thread cleanup.

`FastRunner` implements accelerated execution for testing, maintaining internal simulation time that advances instantly to the next execution time without real delays. FastRunner sets itself as the time source before initializing timing to ensure processes use simulation time (starting at 0) rather than wall clock time. The `run_for_duration()` method enables deterministic testing of long-term thermal behavior in milliseconds rather than hours.

Runner integration enables autonomous thermal management operation through `StandardRunner` and rapid testing of complex timing scenarios through `FastRunner`. Both runners initialize timing state for the entire process hierarchy and provide error resilience to maintain thermal control operation.

## Concrete Implementations

The following implementations demonstrate the three-method pattern across different complexity levels:

### Stateless Controllers

**FixedSpeedController** demonstrates the simplest pattern, overriding only `_think()` to apply fixed actuator values:

```python
class FixedSpeedController(Controller):
    actuator_settings: dict[str, float] = Field(default_factory=dict)
    
    def _think(self, states: dict[str, State]) -> dict[str, State]:
        # Apply fixed values directly to actuators
        return updated_states
```

### Stateful Controllers  

**PIDController** demonstrates StatefulProcess with Buffer for historical error tracking:

```python
class PIDController(StatefulProcess, Controller):
    kp: float = Field(default=1.0)  # Configuration
    
    def _import_state(self, states: dict[str, State]) -> None:
        # Store current error in Buffer
        self.buffer.store(self.get_time(), states)
    
    def _think(self, states: dict[str, State]) -> dict[str, State]:
        # PID calculation using Buffer history
        return pid_result_states
```

**SafetyController** demonstrates rapid monitoring using StatefulProcess:

```python
class SafetyController(StatefulProcess, Controller):
    def _import_state(self, states: dict[str, State]) -> None:
        # Monitor temperature trends
        self.buffer.store(self.get_time(), states)
    
    def _think(self, states: dict[str, State]) -> dict[str, State]:
        # Detect thermal runaway from Buffer trends
        return emergency_actions if thermal_runaway else states
```

### Advanced AI Controllers

**LearningController** demonstrates custom format conversion for machine learning:

```python
class EchoStateNetworkController(Controller):
    def _import_state(self, states: dict[str, State]) -> None:
        # Convert States to TensorFlow tensors
        tensor_data = self._states_to_tensor(states)
        self.tensor_memory.append(tensor_data)
    
    def _think(self, states: dict[str, State]) -> tf.Tensor:
        # Echo State Network computation
        return self.esn_model.predict(self.tensor_memory.recent())
    
    def _export_state(self, result: tf.Tensor, original: dict[str, State]) -> dict[str, State]:
        # Convert tensor predictions back to actuator States
        return self._tensor_to_states(result, original)
```

### Environments

**Hardware** environment interfaces with physical hardware through format conversion:

```python
class Hardware(Environment):
    def _import_state(self, states: dict[str, State]) -> None:
        # Read hwmon filesystem into internal format
        
    def _think(self, states: dict[str, State]) -> dict[str, State]:
        # Apply actuator commands to hardware
        
    def _export_state(self, result, original: dict[str, State]) -> dict[str, State]:
        # Convert hardware readings back to sensor States
```

**Simulation** environment creates virtual thermal models for testing:

```python
class LinearThermalSimulation(StatefulProcess, Environment):
    def _import_state(self, states: dict[str, State]) -> None:
        # Update thermal simulation state
        self.buffer.store(self.get_time(), states)
    
    def _think(self, states: dict[str, State]) -> dict[str, State]:
        # Run thermal physics simulation
        return simulated_sensor_states
```

## Class Hierarchy

```mermaid
classDiagram
    class Entity {
        +uuid: UUID
        +name: str
        +properties: dict
    }
    class Device {
        +properties: dict
    }
    class Sensor
    class Actuator
    class State {
        <<Data Object>>
        +devices: dict
    }
    class Process {
        <<Abstract>>
        +execute(states) Dict[str, State]
        +_execute(states) Dict[str, State]*
        +_import_state(states) None
        +_think(states) Dict[str, State]
        +_export_state(result, original) Dict[str, State]
        +interval_ns: int
        +get_next_execution_time() int
        +get_time() int
        +initialize() None
        +update_execution_count() None
    }
    class StatefulProcess {
        +buffer: Buffer
        +initialize() None
    }
    class Buffer {
        +store(timestamp, states) None
        +get_recent(duration_ns) List
        +get_range(start_ns, end_ns) List
        +prune_before(timestamp) int
    }
    class Collection {
        <<Abstract>>
        +count() int
        +append(process) None
        +remove(name) bool
        +has(name) bool
        +get(name) Process
    }
    class Controller
    class Environment
    class Pipeline {
        +children: List[Process]
    }
    class System {
        +process_heap: List[Tuple[int, Process]]
        +get_next_execution_time() int
    }
    class Runner {
        <<Abstract>>
        +main_process: Process
        +start() None
        +stop() None
        +get_time() int
    }
    class StandardRunner
    class FastRunner
    class TimeSource {
        <<Static>>
        +set_current(runner) None
        +get_current() Runner
        +clear_current() None
    }

    Entity <|-- Device
    Entity <|-- Process
    Entity <|-- Runner
    Device <|-- Sensor
    Device <|-- Actuator
    Process <|-- StatefulProcess
    Process <|-- Collection
    Process <|-- Controller
    Process <|-- Environment
    Collection <|-- Pipeline
    Collection <|-- System
    Runner <|-- StandardRunner
    Runner <|-- FastRunner

    Pipeline o-- "*" Process : children
    System o-- "*" Process : process_heap
    Runner o-- "1" Process : main_process
    StatefulProcess o-- "1" Buffer : buffer
    Environment o-- "*" Device : contains
    Controller ..> State : operates on
    Environment ..> State : produces/consumes
    Buffer ..> State : stores
    TimeSource ..> Runner : manages
```

## Autonomous Execution Architecture

The Runner architecture enables autonomous thermal management operation by separating timing coordination from thermal management logic. StandardRunner provides production execution with real-time timing, while FastRunner enables accelerated testing for rapid validation of complex timing scenarios.

The TimeSource abstraction uses thread-local storage to provide time sources to processes, enabling both real-time operation and deterministic simulation testing. Process.get_time() automatically uses runner-provided time when available, ensuring consistent timing behavior across execution contexts.

Runner lifecycle management includes initialization of the entire process hierarchy timing state, graceful shutdown with proper thread cleanup, and error resilience to maintain thermal control operation despite individual process failures.

## Protocol Layer Architecture

The protocol layer enables remote thermal management across multiple network protocols while maintaining protocol-agnostic core logic. All protocols expose the same underlying pydantic thermal models through different transport mechanisms.

Protocol implementations will include gRPC for high-frequency sensor data streaming and real-time control commands, HTTP/REST for configuration management and status queries, MQTT for distributed sensor networks and pub/sub thermal alerts, WebSocket for real-time dashboard updates, and Prometheus for metrics collection and alerting.

## Serialization Strategy

The architecture separates configuration from runtime state for clean serialization. Pydantic fields contain configuration (PID gains, device names, algorithm parameters) that gets serialized for persistence and network transfer. Runtime state (Buffer contents, numpy arrays, tensorflow models) exists as instance attributes that are not serialized.

Configuration serialization enables system persistence through JSON files, configuration management through REST APIs, and distributed deployment through network protocols. Runtime state gets recreated during `initialize()` based on configuration, ensuring clean startup without complex serialization of temporal data or ML model states.

The architecture uses pydantic models as the single source of truth for configuration data structures, ensuring consistency across protocols and eliminating schema drift. Thermal entities are defined once as pydantic models and exposed across multiple protocols with automatic stub generation and full type checking across network boundaries.

## Testing Strategy

The architecture supports testing through multiple approaches targeting different system layers. Unit tests provide individual component validation with pytest. Pipeline tests validate complete Pipeline execution and controller integration. System tests focus on multi-Pipeline coordination and parallel execution validation.

FastRunner enables rapid testing of long-term thermal behavior and complex timing scenarios without wall-clock delays. Simulation tests will evaluate controller behavior against mathematical thermal models, providing controlled environments for testing control algorithms without requiring physical hardware.

Hardware tests will conduct real-world validation using actual thermal management hardware. Protocol tests will verify multi-protocol serialization and network communication. The simulation environments will enable testing controller stability against both reasonable thermal models and deliberately pathological edge cases.

## Implementation Decisions

**Three-Method Pattern**: Process execution follows the pattern `_import_state()` → `_think()` → `_export_state()` with pass-through defaults in the base class. This enables progressive complexity: stateless processes override only `_think()`, stateful processes add `_import_state()` for memory management, advanced processes override all three for format conversion. The pattern avoids forced abstractions while supporting everything from simple fixed controllers to sophisticated AI algorithms.

**Process Simplicity**: The base Process class provides only execution capability (`execute()`) and timing infrastructure (`get_next_execution_time()`). No children, no persistent state, no complex coordination. This separation enables both simple transformations (Controllers, Environments) and complex coordination (Pipeline, System) through composition.

**Collection Protocol**: Collection defines a coordination interface without specifying container implementation. Pipeline uses a list for serial execution, System uses a priority queue for timing-based parallel coordination. This duck-typed approach enables different storage strategies while maintaining consistent management interface.

**Timing Separation**: Process knows when it wants to execute (`get_next_execution_time()`), Collections coordinate when execution actually occurs, Runner manages autonomous execution lifecycle. This separation enables Pipeline's unified timing (all children execute together) and System's delegated timing (System executes when any child is ready) using the same Process timing interface. System delegates timing to children to achieve event-driven coordination rather than polling.

**Runner Architecture**: Runner provides autonomous execution management with TimeSource abstraction enabling both real-time and accelerated testing. StandardRunner respects process timing for production operation, FastRunner accelerates time for rapid testing validation.

**Permission Enforcement**: Runtime validation prevents Controllers from modifying sensors and prevents Environments from modifying actuators. Call stack inspection identifies the modifying process and validates against domain rules, preventing thermal management violations during execution.

**Immutable Data Flow**: State objects are immutable with copy-on-write semantics, ensuring safe data flow through process pipelines while preventing accidental modification that could corrupt thermal control calculations.

**StatefulProcess Separation**: StatefulProcess extends Process for algorithms requiring memory while maintaining clean State-based interfaces. Configuration (pydantic fields) separates from runtime state (instance attributes), enabling serialization of settings while runtime state gets recreated during `initialize()`. This separation supports system persistence and network protocols without complex serialization of numpy arrays or tensorflow models.

**Buffer Simplicity**: Buffer provides timestamped state storage without complex memory abstraction hierarchies. Single Buffer class supports circular buffering, sliding windows, and time-based queries through simple interface methods. This avoids over-engineering while providing temporal foundation for PID controllers, safety monitoring, and learning algorithms.

**Thread-Local Time Sources**: TimeSource uses thread-local storage to provide time sources to processes, enabling different runners to operate independently in different threads while maintaining consistent timing behavior within each execution context.