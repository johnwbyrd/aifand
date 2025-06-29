# aifand Architecture

This document outlines the software architecture for `aifand`, a Python module and daemon for managing thermal environments. The system serves three primary functions: local thermal control with automatic discovery and learning, distributed thermal state communication over networks, and a class library for experimenting with novel AI-based thermal control architectures.

The architecture is organized in layers, each building upon the previous:
- **Foundation Layer**: Core data structures (Entity, Device, State)
- **Process Layer**: Computational units that transform data
- **Stateful Layer**: Processes that maintain history and memory
- **Specialization Layer**: Domain-specific process types (Environment, Controller)
- **Coordination Layer**: Composing processes into complex systems
- **Execution Layer**: Autonomous operation and testing

A comprehensive test suite validates each layer, using both real-time execution and accelerated simulation to ensure controller stability across diverse thermal environments.

## Architectural Principles

The `aifand` architecture is built on several key design decisions:

**Serialization Architecture**: The system separates configuration (pydantic fields containing algorithm parameters, device names, PID gains) from runtime state (Buffer contents, numpy arrays, tensorflow models). Configuration data serializes cleanly for network transmission and persistence, while runtime state is recreated during initialization. This separation enables distributed thermal management across networks and clean system startup without complex serialization of temporal data or ML model states.

**Data/Computation Separation**: Pure data (`State`) is separated from logic that transforms it (`Process`). States are immutable snapshots that flow safely through process pipelines, while Processes contain all computation logic. This separation enables complex behaviors through composable building blocks.

**Permission-Based Safety**: Controllers can modify actuators but only read sensors. Environments can modify sensors but only read actuators. This domain separation prevents Controllers from corrupting sensor readings and prevents Environments from bypassing controller decisions.

**Compositional Design**: Simple processes combine into complex systems through composition. The architecture supports everything from fixed controllers to sophisticated AI algorithms within the same framework, enabling experimentation with novel thermal control approaches.

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

## Foundation Layer: Data Structures

The foundation layer provides core data structures for identification, hardware abstraction, and state representation.

### Entity

The `Entity` class provides the foundational base for all identifiable objects in the system. Each entity has a unique identifier (`uuid`) and human-readable name, with support for arbitrary additional properties through pydantic's `extra="allow"` configuration.

Entity enables consistent identification, serialization, and extensibility across the architecture. All core classes (`Device`, `Process`, `Runner`) inherit from Entity, ensuring every object can be uniquely identified and serialized for network transmission or persistence.

### Device

The `Device` class represents a single interface point with hardware, extending Entity with a flexible properties dictionary. Properties store arbitrary key-value pairs like value, min, max, label, hwmon_path, scale, and unit, following standard naming conventions for thermal management operations.

Two specialized device types exist: `Sensor` for reporting values from the environment (temperature, fan RPM), and `Actuator` for performing actions (fan PWM control, thermal limits). This separation enables the permission system to enforce domain rules about which processes can modify which device types.

### State

A `State` represents a snapshot of device properties at a specific moment, implemented as a collection of Devices indexed by name. States are unopinionated about their meaning; their role (like "actual" or "desired") is defined by how a Process uses them.

Processes try to implement functions through immutable states for safer data flow, but there are no absolute rules on state mutability. More important is the permission system: Environments can modify Sensors in states, while Controllers can modify Actuators. This ensures proper separation of concerns in thermal management.

### States

`States` is a dictionary mapping state names (like "actual", "desired") to State objects. This enables processes to receive and produce multiple named states, supporting complex control flows where processes need to distinguish between current readings, desired setpoints, and predicted values.

## Process Layer: Computational Units

The process layer defines computational units that transform States using a flexible three-method pattern.

### Process

The `Process` class represents computational units that transform thermal management data. Process provides a template method `execute()` that calls `_execute()` and automatically updates execution count. The base Process class provides only execution capability and timing infrastructure - no children, no persistent state, no complex coordination.

#### Three-Method Pattern

The default `_execute()` implementation uses a three-method pattern that separates the concerns of data format conversion from computation:

```python
def _import_state(self, states: dict[str, State]) -> None:
    """Set up context for thinking - convert aifand States to internal format"""
    
def _think(self) -> None:
    """Pure computation in preferred domain (numpy, tensorflow, etc.)"""
    
def _export_state(self) -> dict[str, State]:
    """Release context - convert internal format back to aifand States"""
```

This pattern solves a critical problem in AI-based thermal control: controller implementers want to work in their preferred computational domain (tensorflow tensors, numpy arrays, scipy matrices) without constantly converting to and from aifand's States-based format. The three-method pattern provides clean boundaries:

- `_import_state()`: Convert aifand States into whatever format the algorithm prefers (tensors, arrays, etc.) and set up any computational context
- `_think()`: Pure computation in the algorithm's native domain - no format conversion, just the core logic
- `_export_state()`: Convert results back to aifand States and clean up computational context

For example, an AI controller using tensorflow:
```python
def _import_state(self, states: dict[str, State]) -> None:
    # Convert States to tensorflow tensors
    self._sensor_tensor = self._states_to_tensor(states["actual"])
    self._context = self._model.create_context()
    
def _think(self) -> None:
    # Pure tensorflow computation - no format concerns
    self._predictions = self._model.predict(self._sensor_tensor, self._context)
    
def _export_state(self) -> dict[str, State]:
    # Convert predictions back to States
    return {"desired": self._tensor_to_states(self._predictions)}
```

This separation enables:
- Simple controllers can override just `_think()` if they're happy with States format
- AI controllers get clean format conversion boundaries
- Testing becomes easier - test `_think()` logic separately from format conversion
- Different algorithms can use completely different internal representations

#### Timing System

Process includes timing infrastructure with nanosecond precision:
- `interval_ns`: Execution interval for autonomous operation
- `get_next_execution_time()`: Calculates when next execution should occur
- `get_time()`: Returns current time, using runner-provided sources when available

#### Permission Model

Device modification permissions enforce thermal management domain rules through runtime validation:
- **Environment processes**: Can modify Sensors but only read Actuators from input state
- **Controller processes**: Can modify Actuators but only read Sensors from input state

This separation prevents Controllers from corrupting sensor readings and prevents Environments from bypassing controller decisions.

## Stateful Layer: Memory and History

The stateful layer adds memory capabilities for processes that need historical data or learning.

### Buffer

The `Buffer` class provides a simple time-series queue for storing timestamped States. Buffer maintains States in chronological order with nanosecond timestamps and provides methods to query time ranges.

Buffer operations include:
- `store(timestamp, states)`: Add new timestamped States to the queue
- `get_recent(duration_ns)`: Retrieve States from the last N nanoseconds
- `get_range(start_ns, end_ns)`: Query States within a specific time range
- `prune_before(timestamp)`: Remove States older than a timestamp
- `get_latest()` / `get_oldest()`: Access the newest or oldest entry

Buffer does not perform any calculations on the stored States - it simply maintains them in chronological order. The process using Buffer (typically a StatefulProcess) is responsible for implementing any time-based calculations like derivatives, integrals, or trend detection using the ordered States that Buffer provides.

### StatefulProcess

The `StatefulProcess` class extends Process to add state management between executions. StatefulProcess automatically creates and manages a Buffer instance for processes that need historical data.

Key features:
- Automatic Buffer creation during `initialize()`
- Configuration fields for buffer size limits and auto-pruning
- Separation of configuration (pydantic fields) from runtime state (instance attributes)
- Default `_import_state()` that stores States in Buffer with timestamps

StatefulProcess is used by:
- PID controllers that need error history for derivative/integral terms
- Safety controllers monitoring temperature trends
- Learning controllers accumulating training data

The separation of configuration from runtime state is architecturally important: configuration (like PID gains or buffer size) serializes cleanly for network transmission, while runtime state (Buffer contents, numpy arrays) is recreated during initialization.

## Specialization Layer: Domain-Specific Processes

The specialization layer defines process types with specific roles in thermal management.

### Environment

The `Environment` class extends Process to interface with the physical or simulated world through a position-independent execution pattern. Unlike other processes that may behave differently based on their position in a pipeline, Environments consistently perform three operations regardless of placement:

1. **Read sensors**: Query the physical or simulated world to create fresh "actual" state
2. **Preserve pipeline data**: Pass through all input states while updating "actual"
3. **Write actuators**: Apply "desired" state to the world (if present)

This position-independent behavior simplifies system composition. An Environment works correctly whether placed at the beginning of a pipeline (creating initial states), in the middle (updating sensor readings), at the end (applying control decisions), or used standalone (complete read-write cycle).

Permission rules for Environments:
- Can create, read, and modify Sensors
- Can read Actuators from input state
- Cannot modify Actuator values in states (only Controllers can do that)
- Can write Actuator values to the physical/simulated world

The distinction between modifying actuator values in states versus writing them to hardware is crucial: Environments translate between the abstract State representation and the concrete world, but only Controllers make control decisions.

Examples include HwmonEnvironment (Linux hardware interface), SimulationEnvironment (physics models), ReplayEnvironment (recorded data playback), and NetworkEnvironment (remote hardware access).

### Controller

The `Controller` class extends Process to implement decision-making logic. Controllers determine actuator settings based on current, previous, and predicted sensor readings.

Permission rules for Controllers:
- Can read Sensors and modify Actuators
- Cannot create or copy Sensors or Actuators (only Environments create devices)

Controllers should implement one specific control algorithm. Multiple controllers can be chained in a Pipeline for complex control logic. Examples include FixedSpeedController, PIDController, SafetyController, and AI-based controllers.

## Coordination Layer: Composing Complex Systems

The coordination layer enables multiple processes to work together through serial and parallel composition.

### Collection

The `Collection` class defines an abstract protocol for managing multiple processes. Collection inherits from Process and adds methods for process management: `count()`, `append()`, `remove()`, `has()`, and `get()`.

Collection uses duck typing - it specifies no internal container type. Any object that can store processes and coordinate their execution is a valid Collection implementation. This flexibility enables different execution strategies in Pipeline and System.

### Pipeline

The `Pipeline` class implements serial execution coordination. Pipeline inherits from Collection and manages an ordered list of processes in its `children` field.

Pipeline execution flows states through children sequentially:
```
input → child1.execute() → child2.execute() → ... → output
```

Each child's output becomes the next child's input, enabling complex transformations through composition. Error handling ensures thermal control continues even if individual processes fail.

Common Pipeline patterns:
- Environment → Controller: Read sensors, compute control, output actuators
- Controller → Controller: Chain multiple control algorithms
- Environment → Controller → Environment: Closed-loop control

### System

The `System` class implements parallel execution coordination for independent processes with different timing requirements. System uses a priority queue (`process_heap`) to track when each child process wants to execute next.

System implements fiber-like cooperative multitasking for thermal control:
- Maintains a priority queue ordered by each process's next execution time
- Services the most timely process next, regardless of order added
- Enables complex non-linear behaviors occurring at varying rates
- Each process executes with empty states (no data sharing)

While Python's GIL prevents true simultaneous execution, System's ability to interleave processes based on timing requirements is architecturally important. It allows modeling of real-world thermal systems where different phenomena occur at different rates - CPU temperatures changing in milliseconds, case temperatures in seconds, and room ambient in minutes.

For example, a System might coordinate:
- CPU thermal control executing every 100ms
- Storage thermal control executing every 1000ms  
- Ambient monitoring executing every 30 seconds

System executes precisely when the next child needs service, implementing event-driven coordination rather than polling. This temporal multiplexing enables sophisticated thermal management across multiple time scales within a single control system.

## Execution Layer: Autonomous Operation

The execution layer provides autonomous execution and testing capabilities for complete thermal management systems.

### Runner

The `Runner` class provides autonomous execution management for processes. Runner executes a process repeatedly according to its timing preferences in a separate thread.

Two Runner implementations serve different purposes:

**StandardRunner** - Production execution with real-time timing:
- Respects process timing intervals with actual sleep delays
- Provides monotonic time for consistent behavior
- Handles graceful shutdown and thread cleanup

**FastRunner** - Accelerated execution for testing:
- Advances simulation time instantly between executions
- No real delays - processes execute as fast as possible
- Enables testing months of thermal behavior in milliseconds
- Essential for validating long-term stability and edge cases

### TimeSource

The `TimeSource` class uses thread-local storage to provide time sources to processes. This enables different runners in different threads to provide different time sources - real time for production, simulated time for testing.

This abstraction is architecturally critical: it allows the same controller code to run in production with real time or in tests with accelerated simulation time, without modification.

## Implementation Examples: Layers in Practice

These examples demonstrate how the architectural layers combine to create thermal control solutions of varying complexity.

### FixedSpeedController

The simplest controller demonstrates the stateless pattern:

```python
class FixedSpeedController(Controller):
    actuator_settings: dict[str, float] = Field(default_factory=dict)
    
    def _think(self) -> None:
        # Override only _think() for simple transformations
        self._result_states = self._apply_fixed_speeds(self._current_states)
```

### PIDController

Demonstrates StatefulProcess with Buffer for historical error tracking:

```python
class PIDController(Controller, StatefulProcess):
    kp: float = Field(default=1.0)
    ki: float = Field(default=0.1) 
    kd: float = Field(default=0.01)
    
    def _import_state(self, states: States) -> None:
        super()._import_state(states)  # Stores in Buffer
        self._current_error = self._calculate_error(states)
    
    def _think(self) -> None:
        # Use Buffer to access error history
        history = self.buffer.get_recent(self.integral_window_ns)
        self._output = self._pid_calculation(history)
```

### SafetyController

Rapid monitoring for thermal protection:

```python
class SafetyController(Controller, StatefulProcess):
    def _think(self) -> None:
        recent = self.buffer.get_recent(5_000_000_000)  # Last 5 seconds
        if self._detect_thermal_runaway(recent):
            self._output = self._emergency_cooling()
```

### HwmonEnvironment

Demonstrates position-independent Environment pattern:

```python
class HwmonEnvironment(Environment):
    def _execute(self, states: States) -> States:
        # Always read current hardware state
        actual = self._read_hwmon_sensors()
        
        # Preserve input states, update actual
        result = States(states) if states else States()
        result["actual"] = actual
        
        # Create initial desired if missing
        if "desired" not in result:
            result["desired"] = State(devices=actual.devices.copy())
        
        # Apply desired state to hardware
        if "desired" in result:
            self._write_hwmon_actuators(result["desired"])
        
        return result
```

### EchoStateNetworkController

AI controller with complete format conversion:

```python
class EchoStateNetworkController(Controller):
    def _import_state(self, states: States) -> None:
        # Convert States to numpy arrays
        self._sensor_array = self._states_to_numpy(states["actual"])
        
    def _think(self) -> None:
        # Pure numpy/tensorflow computation
        self._predictions = self._esn_model.predict(self._sensor_array)
        
    def _export_state(self) -> States:
        # Convert predictions back to States
        return {"desired": self._numpy_to_states(self._predictions)}
```

### System Composition Examples

Position-independent Environments enable simple system composition:

```python
# Read-only monitoring
Pipeline([
    HwmonEnvironment(),    # Creates actual state
    SafetyController(),    # Monitors temperatures
    LoggingEnvironment()   # Records to database
])

# Closed-loop control
Pipeline([
    HwmonEnvironment(),    # Reads sensors, applies previous desired
    PIDController(),       # Computes new desired
    # Same HwmonEnvironment instance applies new desired next cycle
])

# Multi-zone control
System([
    Pipeline([
        HwmonEnvironment(cpu_zone=True),
        CPUController()
    ]),
    Pipeline([
        HwmonEnvironment(gpu_zone=True), 
        GPUController()
    ])
])
```

These examples show how the layered architecture supports different complexity levels within the same framework.

