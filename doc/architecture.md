# aifand Architecture

This document outlines the software architecture for `aifand`, an adaptive thermal management system designed for both local and remote operation across multiple network protocols.

## Core Philosophy

The `aifand` architecture automatically discovers and learns the thermal properties of hardware without manual configuration. It separates pure data (`State`) from logic that transforms it (`Process`), enabling complex behaviors through composable building blocks. The system supports multiple network protocols for remote monitoring and control while maintaining a single source of truth through pydantic models.

## Key Abstractions and Data Models

### Entity

The `Entity` class serves as the foundational base for all objects within the system. Each entity has a unique identifier (`uuid`) and human-readable name, with support for arbitrary additional properties through pydantic's `extra="allow"` configuration.

**Implementation details:**
- Inherits from `pydantic.BaseModel` with `frozen=True` for immutability
- Automatic UUID generation via `uuid4()` if not provided
- Supports arbitrary key-value pairs alongside core fields
- Full JSON serialization/deserialization support
- String representation shows all fields for debugging

All core classes (`Device`, `Process`, `System`) inherit from `Entity` to ensure consistent identification, serialization, and extensibility across the architecture.

### Data Models

The `Device` class represents a single interface point with hardware. It extends Entity with a flexible properties dictionary storing arbitrary key-value pairs like value, min, max, label, hwmon_path, scale, and unit. Standard property naming conventions ensure consistency across thermal management operations.

Two specialized device types exist: `Sensor` for reporting values from the environment (temperature, fan RPM), and `Actuator` for performing actions (fan PWM control, thermal limits).

A `State` represents a snapshot of device properties at a specific moment, implemented as an immutable collection of Devices indexed by name. States are unopinionated about their meaning; their role (like "actual" or "desired") is defined by how a `Process` uses them. States provide helper methods for device access, addition, and removal while maintaining immutability through copy-on-write semantics.

### Process

The `Process` class represents computational units that transform data within the system. Processes receive a dictionary of named states (e.g., "actual", "desired") and return a transformed dictionary of states. Each process can contain an ordered list of child processes that execute serially to form execution pipelines.

**Key characteristics implemented:**
- **Stateless execution**: No data persists between execute() calls
- **Serial pipeline**: Child processes execute in order with state passthrough
- **Error resilience**: Exceptions are caught, logged, and execution continues with passthrough behavior
- **Immutable operations**: Input states are deep-copied to prevent modification
- **Per-process logging**: Each process gets its own hierarchical logger

**Execution behavior:**
- If a process has no children, it executes its own `_execute_impl()` method
- If a process has children, it executes them serially, passing each child's output as the next child's input
- Failed processes log errors but don't abort the pipeline (critical for thermal systems)

An `Environment` can read and modify sensors, but should only read actuators from its input state. `Simulation` environments may model virtual hardware responses, while `Hardware` environments interface with real hardware via Linux hwmon.

A `Controller` can read and modify actuators, but should only read sensors from its input state. Controllers contain decision-making logic that determines actuator settings based on sensor readings.

### System

The `System` class orchestrates overall operation, managing an environment and ordered controller pipeline. It maintains named states including current system state ("actual") and target state ("desired"). During each update cycle, the system executes its pipeline in sequence, allowing controllers to transform states toward desired outcomes.

**Implementation status**: Not yet implemented. Will handle state persistence between executions, unlike individual Processes.

**Planned features**:
- State management and context handling for named states
- Configuration loading and process instantiation  
- Update loop timing (targeting ~100ms intervals, not hard real-time)
- Inter-system communication capabilities

Systems can publish and receive custom composite states from other systems, enabling abstraction and inter-system communication. Because a system is itself a process, it can be included within higher-level systems for multi-layered architectures.

## Implementation Status and Design Decisions

### Current Implementation (Phase 2 Complete)

The core abstractions are fully implemented and tested:

- **Entity base class**: UUID identification, arbitrary properties, full serialization
- **Device classes**: Sensor and Actuator with flexible property storage
- **State class**: Immutable device collections with helper methods
- **Process architecture**: Abstract base with Environment and Controller subclasses
- **Comprehensive test suite**: 60 tests covering all functionality

### Key Design Decisions Made

**State naming strategy**: Currently using string keys ("actual", "desired") for state dictionaries. Formalization into constants/enums deferred to when System class is implemented and usage patterns become clear.

**Device property validation**: Flexible properties dictionary approach maintained. Validation logic will be implemented in specific controller implementations rather than at the Device level, allowing different controllers to have different requirements.

**Process configuration and discovery**: Deferred to concrete System implementations. Each System will be responsible for instantiating and configuring its process pipeline.

**Performance considerations**: 
- Deep copying of states through process pipelines is acceptable for expected device counts (5-15 temperature sensors, 3-8 fan controllers)
- Update frequency targeting ~100ms intervals (loose real-time requirements)
- Optimization strategy: "gentleman's agreement" to pass minimal state sets rather than premature optimization
- Python's `copy.deepcopy()` creates real copies, not reference updates, but performance impact expected to be negligible at planned scale

**Error handling philosophy**: Never abort thermal control pipelines. Failed processes log errors and continue with passthrough behavior to maintain system stability.

## Protocol Layer Architecture

The protocol layer enables remote thermal management across multiple network protocols while maintaining protocol-agnostic core logic. All protocols expose the same underlying pydantic thermal models through different transport mechanisms.

### Protocol Use Cases

- **gRPC**: High-frequency sensor data streaming, real-time control commands, authenticated remote management
- **HTTP/REST**: Configuration management, status queries, integration with web dashboards
- **MQTT**: Distributed sensor networks, IoT device integration, pub/sub thermal alerts
- **WebSocket**: Real-time dashboard updates, live thermal monitoring
- **Prometheus**: Metrics collection, alerting, performance monitoring

## Serialization Strategy

The architecture assumes that pydantic models serve as the single source of truth for all data structures. This ensures consistency across all protocols and eliminates schema drift.

### Core Serialization Features

- **Single Schema Definition**: Thermal entities defined once as pydantic models
- **Multiple Protocol Support**: Same models exposed via gRPC, HTTP, MQTT, WebSocket
- **Automatic Code Generation**: Protocol stubs generated from pydantic models
- **Type Safety**: Full type checking across network boundaries
- **Arbitrary Properties**: Flexible key-value extension without protocol changes

### Protocol-Specific Adaptations

- **gRPC**: Uses `pydantic-rpc` to automatically generate protobuf definitions from pydantic models
- **HTTP**: Direct FastAPI integration with pydantic models
- **MQTT**: JSON serialization via `model_dump_json()`
- **WebSocket**: Real-time streaming of pydantic model updates
- **Prometheus**: Metric extraction from pydantic model properties

## Concrete Implementations

### Environments

The `Hardware` environment interfaces with physical hardware through the Linux hwmon filesystem. It discovers available sensors and actuators, populates device lists, and implements read/apply methods for real-world interaction.

The `Simulation` environment creates virtual worlds with mathematical thermal models. Multiple simulation types support controller testing: LinearThermal, ThermalMass, RealisticSystem, UnstableSystem, FailureSimulation, and ChaosSystem.

### Controllers

The `SafetyController` implements fail-safe logic, monitoring actual state against critical thresholds and overriding other controllers when triggered. It executes last in the controller pipeline.

The `PIDController` implements standard Proportional-Integral-Derivative control with anti-windup and derivative filtering. Multiple instances can control independent loops.

The `LearningController` uses Echo State Networks to learn thermal relationships and optimize for multiple objectives like efficiency and noise.

## The Execution Pipeline

The system's main loop follows a consistent pattern:

```mermaid
sequenceDiagram
    participant System
    participant Environment
    participant Controller1
    participant Controller2

    loop Every Update Cycle
        System->>Environment: read()
        activate Environment
        Environment-->>System: returns 'actual' State
        deactivate Environment
        System->>System: context["actual"] = State

        System->>System: Load 'desired' State from Profile
        System->>System: context["desired"] = State

        System->>Controller1: execute(context)
        activate Controller1
        Controller1-->>System: returns proposed_state_1
        deactivate Controller1
        
        System->>Controller2: execute(context, proposed_state_1)
        activate Controller2
        Controller2-->>System: returns final_actuator_state
        deactivate Controller2

        System->>Environment: apply(final_actuator_state)
        activate Environment
        Environment-->>System: Acknowledge
        deactivate Environment
        
        System->>System: sleep()
    end
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
    }
    class Controller
    class Environment
    class System
    class ProtocolServer {
        <<Abstract>>
    }
    class gRPCServer
    class HTTPServer
    class MQTTPublisher

    Entity <|-- Device
    Entity <|-- Process
    Sensor --|> Device
    Actuator --|> Device
    Controller --|> Process
    Environment --|> Process
    System --|> Process
    ProtocolServer --|> Entity
    gRPCServer --|> ProtocolServer
    HTTPServer --|> ProtocolServer
    MQTTPublisher --|> ProtocolServer

    System o-- "1" Environment
    System o-- "1..*" Controller
    System o-- "*" State : "manages in context"
    Environment o-- "*" Device : "contains"
    Controller ..> State : "operates on"
    Environment ..> State : "produces/consumes"
    ProtocolServer ..> System : "exposes remotely"
```

## Remote System Communication

Systems can communicate across networks using any supported protocol. A local system can monitor and control remote systems through protocol-specific clients, enabling distributed thermal management across multiple machines or data centers.

### Hierarchical Composition

Systems can be composed hierarchically, with higher-level systems managing collections of lower-level systems. Remote systems appear as virtual devices to parent systems, enabling scalable thermal management architectures.

## Testing Strategy

The architecture supports comprehensive testing through multiple approaches:

### Testing Approach
- **Unit Tests**: Individual component validation with pytest
- **Integration Tests**: Complete system pipeline testing
- **Simulation Tests**: Controller behavior against mathematical thermal models
- **Hardware Tests**: Real-world validation and safety verification
- **Protocol Tests**: Multi-protocol serialization and network communication

The simulation environments enable testing controller stability against both reasonable thermal models and perverse edge cases (positive feedback, chaotic dynamics, hardware failures) without risking physical hardware.