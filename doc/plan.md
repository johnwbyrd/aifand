# fanctl Implementation Plan

## Overview

This document outlines the complete implementation strategy for fanctl, organized by functional areas and dependencies. The design uses a unified abstraction hierarchy that enables both single-machine and multi-machine thermal management.

## Core Abstractions

### Device
Base class for all sensors and actuators, handling:
- Value reading and conversion
- Min/max limits with types (warning, critical)
- Scale handling (Celsius, Fahrenheit)
- Ratio conversion (e.g., 57000 → 57.0°C)
- Common metadata and health status

### Sensor and Actuator
Both inherit from Device:
- **Sensor**: Specialized for reading values (temperatures, RPM, etc.)
- **Actuator**: Specialized for control (fan speeds, pump rates, etc.)

### Model
Base class that contains collections of Sensors and Actuators. Three key subclasses:

1. **Forward Model**: Reads sensors, writes actuators (controllers)
   - Echo State Network controller
   - PID controller
   - Rule-based controller

2. **Backward Model**: Writes sensors, reads actuators (systems)
   - Simulation (mathematical relationships)
   - Machine (actual hardware)

3. **Safety Model**: Can read/write both sensors and actuators
   - Override dangerous conditions
   - Detect and correct oscillations
   - Inject test patterns
   - Note: May not be needed if Forward models handle safety adequately

### System
A System is a Model that:
- Contains other Models (Forward, Backward, possibly Safety)
- Includes prescriptive information (temperature targets, preferences)
- Can present itself as virtual sensors/actuators to higher-level Systems
- Enables hierarchical control (PC → Rack → DataCenter)

## Phase 1: Foundation - Core Abstractions

### Objective
Establish the Device/Model/System hierarchy that enables flexible composition.

### Tasks
1. **Define Device abstraction**
   - Value storage and conversion
   - Limit types (warning, critical, min, max)
   - Scale conversion (C/F/K)
   - Ratio handling
   - Health status
   - Timestamp management

2. **Define Sensor and Actuator**
   - Sensor: read-only interface for Forward models
   - Actuator: write interface for Forward models
   - Both: appropriate interfaces for Backward/Safety models
   - Graceful failure handling
   - Caching strategies

3. **Define Model abstraction**
   - Collection management for Devices
   - Forward model interface (read sensors, write actuators)
   - Backward model interface (write sensors, read actuators)
   - Safety model interface (read/write all)
   - Update/step methods

4. **Define System abstraction**
   - Model composition (contains Forward + Backward + Safety)
   - Prescriptive information (targets, margins)
   - Virtual device presentation (System as Model)
   - Pipeline execution order
   - State aggregation

### Key Design Principles
- Unified Device abstraction simplifies many operations
- Model types enforce correct data flow
- System recursion enables hierarchical control
- Clear separation of concerns

## Phase 2: Testing Infrastructure - Simulations

### Objective
Build Simulation (Backward Model) for testing without hardware.

### Tasks
1. **Basic Simulation implementation**
   - Mathematical relationships between actuators and sensors
   - Configurable dynamics (linear, nonlinear)
   - Time-based evolution
   - Deterministic for testing

2. **Physical effects modeling**
   - Heat generation and dissipation
   - Airflow dynamics
   - Thermal mass
   - Transport delays
   - Ambient conditions

3. **Nonlinear behaviors**
   - Recirculation zones
   - Temperature stratification
   - Fan interaction effects
   - Saturation limits
   - Hysteresis

4. **Failure modes**
   - Sensor failures (stuck, drift, noise)
   - Actuator failures (stuck, limited)
   - Communication issues
   - Power fluctuations

5. **Test scenario library**
   - Single fan/sensor relationships
   - Multiple coupled zones
   - Cascade failures
   - Extreme conditions
   - Oscillation triggers

### Key Concepts
- Simulations are Backward Models that generate sensor values
- Different simulations test different control challenges
- Can compose multiple simulations into complex scenarios
- Foundation for algorithm validation

## Phase 3: Echo State Network - Forward Model

### Objective
Implement the learning controller as a Forward Model.

### Tasks
1. **EchoForwardModel class**
   - Inherits from Forward Model
   - Reads all sensors
   - Computes actuator commands
   - Online learning capability

2. **Reservoir implementation**
   - Sparse random initialization
   - Spectral radius control
   - State evolution dynamics
   - Memory of recent history

3. **Learning mechanism**
   - Recursive Least Squares (RLS)
   - Online weight updates
   - Forgetting factor
   - Numerical stability

4. **Influence discovery**
   - Method to extract relationships
   - Confidence estimation
   - Visualization support
   - Interpretability

5. **Persistence**
   - Save/load reservoir state
   - Save/load learned weights
   - Continuous improvement
   - Version compatibility

### Design Notes
- ESN naturally fits Forward Model pattern
- No pre-training required
- Learns from any Backward Model (Simulation or Machine)
- Can be composed with other Forward Models

## Phase 4: Hardware Abstraction - Machine

### Objective
Implement Machine (Backward Model) for real hardware.

### Tasks
1. **HwmonMachine implementation**
   - Discovers hwmon sensors/actuators
   - Creates Device objects
   - Handles hardware variations
   - Manages permissions

2. **Device implementations**
   - Temperature sensors (various types)
   - Fan actuators (PWM control)
   - Other sensors (voltage, current)
   - Other actuators (pumps, valves)

3. **Naming and identification**
   - Parse hwmon labels
   - DMI information integration
   - Human-readable names
   - Consistent identification

4. **Hardware management**
   - Dynamic device discovery
   - Graceful degradation
   - Error recovery
   - Performance optimization

5. **Remote machine support**
   - Network protocol
   - Security/authentication
   - Latency handling
   - Connection management

### Technical Challenges
- Hardware varies between systems
- Permissions and access control
- Real-time constraints
- Reliability requirements

## Phase 5: System Composition and Pipeline

### Objective
Implement System to compose Models into working controllers.

### Tasks
1. **LocalSystem implementation**
   - Composes EchoForwardModel + HwmonMachine
   - Manages execution pipeline
   - Handles timing and scheduling
   - State management

2. **Pipeline execution**
   - Backward models update sensor values
   - Forward models compute actuator commands
   - Safety models (if any) override
   - Proper ordering and timing

3. **Configuration management**
   - Temperature targets
   - Safety margins
   - Model parameters
   - Device mappings

4. **State aggregation**
   - Combine multiple sensor readings
   - Statistical summaries
   - Health indicators
   - Trend detection

5. **Virtual device presentation**
   - System presents simplified interface
   - Aggregate temperature sensor
   - Overall cooling capability
   - Health status

### System Patterns
- Single machine: LocalSystem with one Forward + one Backward
- Test setup: LocalSystem with Forward + Simulation
- Hierarchical: Multiple Systems as Models in larger System

## Phase 6: Safety Architecture

### Objective
Implement safety through appropriate Forward Models and optionally Safety Models.

### Tasks
1. **SafetyForwardModel**
   - Monitors all sensors
   - Detects dangerous conditions
   - Sets fans to safe speeds
   - Simple, reliable logic

2. **Rate limiting**
   - Prevent rapid actuator changes
   - Smooth transitions
   - Protect hardware
   - Maintain stability

3. **Oscillation detection**
   - Monitor actuator patterns
   - Detect unstable control
   - Dampen oscillations
   - Alert operators

4. **Sensor validation**
   - Detect impossible readings
   - Handle sensor failures
   - Maintain last-good values
   - Estimate from other sensors

5. **Override precedence**
   - Clear rules for safety overrides
   - Logging of interventions
   - Performance impact
   - Testing strategies

### Safety Philosophy
- Prefer simple Forward Models that max fans on high temps
- Safety Models only if complex intervention needed
- Fast decision making
- Fail safe, not smart

## Phase 7: Calibration System

### Objective
Implement Gold code calibration to accelerate learning.

### Tasks
1. **CalibrationForwardModel**
   - Generates Gold code patterns
   - Applies to actuators
   - Monitors safety limits
   - Operator interaction

2. **Supervised execution**
   - Clear operator warnings
   - Real-time status display
   - Abort mechanism
   - Progress indication

3. **Calibration parameters**
   - Code length selection
   - Speed ranges (50-70%)
   - Safety thresholds
   - Time limits

4. **Data quality**
   - Ensure good excitation
   - Verify sensor responses
   - Check for coupling
   - Validate results

5. **Integration with learning**
   - Feed high-quality data to ESN
   - Measure improvement
   - Compare with uncalibrated
   - Document benefits

### User Experience
- Optional but recommended
- Clear safety warnings
- Quick process (30-60 seconds)
- Visible results

## Phase 8: Control Loop and Daemon

### Objective
Implement the main execution framework.

### Tasks
1. **Main control loop**
   - System pipeline execution
   - Timing management
   - Error handling
   - Performance monitoring

2. **Daemon infrastructure**
   - Systemd service
   - Signal handling
   - Privilege management
   - Resource limits

3. **Configuration system**
   - YAML/TOML format
   - Model selection
   - Device mapping
   - Hot reload

4. **Logging system**
   - Structured logging
   - Multiple levels
   - Rotation policies
   - Remote logging

5. **State persistence**
   - Periodic snapshots
   - Graceful shutdown
   - Recovery on startup
   - Migration support

### Operational Requirements
- Must run 24/7 reliably
- Minimal resource usage
- Easy troubleshooting
- Graceful degradation

## Phase 9: Multi-System Support and Serialization

### Objective
Enable hierarchical control across multiple machines with abstract serialization.

### Tasks
1. **Serializer abstraction**
   - Base Serializer class for all protocols
   - Serialize/deserialize Device states
   - Serialize/deserialize Model states
   - Handle streaming where supported
   - Protocol-specific authentication

2. **gRPC/ProtoBuf Serializer**
   - For machine-to-machine communication
   - Full bidirectional control
   - Streaming sensor updates
   - Strong typing via Protocol Buffers
   - Built-in TLS/auth

3. **MQTT Serializer**  
   - For IoT and small devices
   - Publish/subscribe model
   - JSON or MessagePack payload
   - Topic hierarchy for devices
   - Lightweight protocol

4. **Prometheus Serializer**
   - For metrics export
   - Read-only gauge format
   - Standard naming conventions
   - Metadata annotations
   - Pull model via HTTP

5. **System aggregation**
   - Multiple Machines in one System
   - Virtual device mapping
   - Latency compensation
   - Failure handling
   - Protocol-agnostic internals

### Serialization Philosophy
- One abstraction, multiple protocols
- Each protocol serves different use cases
- Implementation order based on need
- Easy to add new protocols later
- Core system doesn't care about wire format

## Phase 10: Testing and Validation

### Objective
Comprehensive testing at all levels.

### Tasks
1. **Unit tests**
   - Device abstraction
   - Model interfaces
   - System composition
   - Pipeline execution

2. **Simulation tests**
   - Various dynamics
   - Failure modes
   - Edge cases
   - Performance limits

3. **Integration tests**
   - Hardware discovery
   - Pipeline behavior
   - Configuration loading
   - State persistence

4. **System tests**
   - Single machine control
   - Multi-system coordination
   - Failover behavior
   - Resource usage

5. **Stress tests**
   - Many devices
   - Rapid changes
   - Network issues
   - Resource exhaustion

### Test Strategy
- Test against Simulations first
- Progress to hardware tests
- Use System recursion for complex scenarios
- Measure learning effectiveness

## Phase 11: Packaging and Distribution

### Objective
Make fanctl easily deployable.

### Tasks
1. **Python packaging**
   - Clean dependency management
   - Entry points
   - Plugin system
   - Version management

2. **System packaging**
   - Debian packages
   - RPM packages
   - Container images
   - Ansible playbooks

3. **Documentation**
   - Architecture guide
   - User manual
   - API reference
   - Troubleshooting

4. **Extension documentation**
   - How to add custom Backward Models
   - Example template in src/systems/example.py
   - Required method implementations
   - Testing your custom system
   - Contributing guidelines for mainline inclusion

5. **Example configurations**
   - Single machine
   - Multiple machines
   - Test setups
   - Production deployments
   - Custom system integration

6. **Migration tools**
   - From other fan control systems
   - Configuration converters
   - State migration
   - Rollback support

### Extension Philosophy
- Third-party systems integrate by subclassing BackwardModel
- No complex plugin architecture needed
- Fork, implement, use (or contribute back)
- Clear documentation makes this accessible to Python developers
- Examples show the way

## Phase 12: Monitoring and Observability

### Objective
Enable understanding of system behavior.

### Tasks
1. **Metrics export**
   - Prometheus format
   - Device values
   - Model confidence
   - System health

2. **Visualization**
   - Terminal UI
   - Web dashboard
   - Influence matrix display
   - Learning progress

3. **Debugging tools**
   - Model introspection
   - Pipeline tracing
   - State dumps
   - Replay capability

4. **Alerting**
   - Temperature warnings
   - Device failures
   - Learning issues
   - System problems

5. **Analysis tools**
   - Efficiency reports
   - Trend analysis
   - Anomaly detection
   - Performance tuning

### Visualization Strategy
- fanctl exposes data via gRPC/MQTT
- Separate web GUI project queries fanctl
- Not required for operation
- Examples: Grafana dashboards, custom React app
- Community can build different UIs

## Success Criteria

1. **Architectural Success**
   - Clean Device/Model/System abstractions
   - Easy to extend with new device types
   - Natural composition patterns
   - Clear data flow

2. **Functional Success**
   - Learns thermal relationships automatically
   - Maintains safe temperatures
   - Handles failures gracefully
   - Scales to multiple systems

3. **Operational Success**
   - Simple single-machine deployment
   - Reliable 24/7 operation
   - Low resource usage
   - Easy troubleshooting

4. **User Success**
   - Zero configuration basic use
   - Optional calibration for faster learning
   - Clear documentation
   - Active community

## Future Enhancements

1. **Additional Models**
   - Predictive control
   - Power optimization with energy pricing
   - Time-of-use aware cooling
   - Demand response integration
   - Acoustic optimization
   - Wear leveling

2. **More Device Types**
   - Liquid cooling
   - Peltier coolers
   - Variable speed pumps
   - Environmental sensors

3. **Advanced Systems**
   - Cloud coordination
   - Energy market integration (shift cooling to cheap power)
   - Grid-responsive operation
   - Carbon-aware scheduling
   - Predictive maintenance
   - ML model sharing

4. **Integration Ecosystem**
   - MQTT for small IoT devices
   - Kubernetes operators
   - Cloud provider APIs
   - Building management systems
   - Home Assistant integration
   - Energy management platforms
   