# aifand Implementation Todo

## Overview

This document outlines the remaining implementation tasks for `aifand`.

---

## System Implementation

### Objective
Create the System class for coordinating multiple Pipelines in complex thermal management scenarios.

### Tasks
1. **Implement `System` Process** (src/aifand/base/system.py):
   - Create `System` class extending Process for multi-Pipeline coordination
   - Support both sequential and parallel Pipeline execution models
   - Implement Pipeline management: add, remove, configure
   - Add comprehensive status aggregation across managed Pipelines

2. **System Execution Models**:
   - **Parallel mode**: Concurrent Pipeline execution with result aggregation
   - **Sequential mode**: Ordered Pipeline execution for dependent thermal zones
   - **Mixed mode**: Parallel groups with sequential group execution
   - Resource coordination and thermal policy management across Pipelines

3. **System Testing**:
   - Multi-Pipeline coordination val idation
   - Parallel vs sequential execution testing
   - Resource contention and conflict resolution
   - Hierarchical System composition (Systems containing Systems)


  Phase 1: Process Infrastructure Updates

  1. Extract _initialize_timing() method from Process.start()
    - Move initialization logic (start_time, execution_count, stop_requested, _current_states) to new method
    - Update Process.start() to call _initialize_timing()
    - Run existing tests to verify no regressions

  Phase 2: Basic System Implementation

  2. Implement System class structure in src/aifand/base/system.py
    - Extend Process with states field (like Pipeline)
    - Add basic class documentation and imports
  3. Implement System timing coordination methods
    - _calculate_next_tick_time(): Query children and return earliest time
    - _select_processes_to_execute(): Return children ready to execute
    - _execute_selected_processes(): Execute ready children with state management
    - _process(): Handle edge case of System with no children
  4. Update module exports
    - Add System to src/aifand/base/__init__.py

  Phase 3: System Testing

  5. Create System test mocks in tests/unit/base/mocks.py
    - MockProcess with configurable timing intervals
    - Timing behavior variants for coordination testing
  6. Implement comprehensive System tests in tests/unit/base/test_system.py
    - Basic System creation and structure
    - Timing coordination with multiple children
    - Mixed children (Pipelines and Systems)
    - State isolation verification
    - Error handling and failure isolation
    - Hierarchical composition testing

  Phase 4: Integration Verification

  7. Run full test suite
    - Verify no regressions in existing Process/Pipeline functionality
    - Confirm System integrates properly with existing architecture

---

## Simulation Environments

### Objective
Implement multiple simulation environments with deliberately pathological thermal models to test controller stability under extreme conditions. Focus on adversarial testing with chaotic dynamics, positive feedback loops, sudden discontinuities, and failure modes that real hardware might never produce.

### Tasks
1. **Implement Adversarial Simulation Environments** (src/aifand/environments/simulation.py):
   - **LinearThermal**: Simple linear heat transfer model (`temp_change = (heat_input - heat_dissipation) / thermal_mass`)
   - **ThermalMass**: Multi-zone model with thermal inertia and time delays
   - **RealisticSystem**: Computer thermal model with CPU load-based heat generation
   - **UnstableSystem**: Positive feedback dynamics designed to induce thermal runaway
   - **ChaosSystem**: Non-linear, chaotic thermal behavior with sudden discontinuities and bifurcations
   - **FailureSimulation**: Random sensor dropouts, actuator failures, and hardware malfunctions
   - **MaliciousSystem**: Deliberately perverse thermal physics designed to break controllers
   - **RandomizedSystem**: Wildly varying parameters and dynamics to test adaptability

2. **Pathological Testing Framework**:
   - Random parameter variation to create unpredictable thermal environments
   - Stress testing with extreme thermal gradients and rapid state changes
   - Controller stability validation against pessimal thermal conditions
   - Detection of controller "flying off the deep end" under adversarial conditions

---

## Basic Controllers

### Objective
Implement fundamental controllers for Pipeline testing and validation.

### Tasks
1. **Implement Basic Controllers**:
   - **FixedSpeedController** (src/aifand/controllers/fixed.py): Static actuator control for initial testing
   - **SafetyController** (src/aifand/controllers/safety.py): Fail-safe logic with threshold monitoring
   - State transformation and validation logic
   - Controller configuration and parameter management

2. **Controller Testing Framework**:
   - Integration tests for complete Pipeline execution with controllers
   - Controller stability tests against each simulation environment
   - Quantitative metrics: overshoot, settling time, oscillation detection
   - Test scenarios: step response, disturbance rejection, setpoint tracking
   - Data collection: time series of sensor/actuator values, performance metrics

---

## Advanced Controller Development

### Objective
Implement sophisticated controllers and test them against simulation environments to validate stability and performance.

### Tasks
1. **Implement `PIDController`** (src/aifand/controllers/pid.py):
   - Create configurable PID controller with tunable parameters
   - Support multiple independent control loops
   - Implement setpoint tracking from desired state
   - Add anti-windup and derivative filtering

2. **Implement `LearningController` with Echo State Network** (src/aifand/controllers/learning.py):
   - Create ESN-based controller using reservoir computing
   - Implement Recursive Least Squares (RLS) for online learning
   - Support multi-input, multi-output control scenarios
   - Implement state space exploration

3. **Gold Code Training**:
   - Generate reference control sequences from PID controllers
   - Collect training datasets for different thermal scenarios
   - Implement ESN training pipeline with Gold code sequences
   - Create performance validation and comparison tools

4. **Controller Testing and Benchmarking**:
   - Test each controller against all simulation environments
   - Measure performance metrics: stability, efficiency, response time
   - Identify failure modes and unstable behavior
   - Compare controller performance across different scenarios

## Hardware Integration

### Objective
Direct hwmon filesystem integration for real-world thermal management. Critical for production deployment - controllers must work reliably with actual hardware, handle I/O failures gracefully, and maintain safety under all conditions.

### Tasks
1. **Implement `Hardware` Environment** (src/aifand/environments/hardware.py):
   - Direct hwmon filesystem I/O (/sys/class/hwmon/hwmon*/temp*_input, pwm*, fan*_input)
   - Automatic discovery of available sensors and actuators via filesystem enumeration
   - Robust device capability detection (readable/writable, min/max values, scaling factors)
   - Comprehensive error handling for hardware failures, missing devices, permission issues

2. **Hardware Interface Implementation**:
   - Robust `read()` with proper scaling, unit conversion, and error recovery
   - Safe `apply()` with value validation, bounds checking, and write verification
   - Handle filesystem I/O failures, device disappearance, and permission changes
   - Implement hardware-specific workarounds for quirky thermal sensors

3. **Hardware Validation Testing**:
   - Real hardware testing procedures with actual thermal loads
   - Safety mechanism validation under thermal stress conditions
   - Controller stability testing with real thermal dynamics
   - Hardware-specific calibration and characterization procedures

---

## Daemon Implementation

### Objective
Implement the daemon entry point and make the system runnable as a systemd service.

### Tasks
1. **Implement Daemon Entry Point** (src/aifand/daemon.py):
   - Create main executable that instantiates and runs the System
   - Implement signal handling for graceful shutdown
   - Add configuration loading from files
   - Implement daemon behavior and PID management

2. **System Serialization**:
   - Implement System.save() and System.load() methods
   - Serialize system state and configuration to JSON files
   - Support saving/loading of devices, controllers, and current states
   - Add configuration validation and error reporting

3. **Service Infrastructure**:
   - Add systemd integration with service files and dependencies
   - Implement graceful shutdown and restart capabilities
   - Configure logging to systemd journal

4. **User and Permissions**:
   - Create dedicated user and group for aifand service
   - Set appropriate file permissions and access controls
   - Implement privilege separation

5. **Operational Support**:
   - Integrate with systemd journal for logging
   - Add configuration directory structure (`/etc/aifand/`)
   - Implement service status monitoring
   - Create installation and uninstallation procedures

---

## Protocol Layer Implementation

### Objective
Implement multi-protocol remote access layer enabling distributed thermal management.

### Tasks
1. **gRPC Protocol Implementation** (src/aifand/protocols/grpc/):
   - Implement gRPC server using `pydantic-rpc` for automatic protobuf generation
   - Create gRPC client for remote thermal management
   - Support streaming for real-time sensor data
   - Implement authentication and secure communication

2. **HTTP REST API** (src/aifand/protocols/http/):
   - Implement FastAPI server with direct pydantic integration
   - Create REST endpoints for configuration management
   - Add HTTP client for programmatic access
   - Support JSON serialization of all thermal entities

3. **MQTT Integration** (src/aifand/protocols/mqtt/):
   - Implement MQTT publisher for distributed sensor networks
   - Create MQTT subscriber for remote thermal sensors
   - Support pub/sub thermal alerts and notifications
   - Enable IoT device integration

4. **Real-time Dashboard** (src/aifand/protocols/dashboard/):
   - Implement WebSocket server for real-time updates
   - Create HTML templates and static assets
   - Support live thermal monitoring and control
   - Add responsive web interface

5. **Prometheus Metrics** (src/aifand/protocols/prometheus/):
   - Implement metrics exporter for thermal data
   - Define standard thermal management metrics
   - Support alerting and performance monitoring
   - Enable integration with monitoring infrastructure

---

## Distribution & Packaging

### Objective
Create distribution packages for installation, upgrade, and removal of aifand.

### Tasks
1. **Python Package Distribution**:
   - Automated wheel and source distribution building via CI/CD
   - Package integrity verification with twine
   - GitHub Artifacts for development builds
   - Future PyPI publication for stable releases

2. **Debian Package Creation**:
   - Create `debian/` directory structure
   - Implement control files with dependencies and metadata
   - Add package descriptions and documentation
   - Create debhelper configuration

3. **Package Installation Scripts**:
   - Implement `postinst` scripts for service installation and configuration
   - Create `prerm` and `postrm` scripts for uninstallation
   - Add user and group management in package scripts
   - Implement configuration file handling

4. **Build and Testing**:
   - Set up automated package building with pbuilder/sbuild
   - Create package testing procedures
   - Implement dependency resolution and conflict checking
   - Add package repository creation

---

### Current Implementation Considerations

**Pipeline vs System Architecture**: Pipeline manages single control flows with state persistence, while System coordinates multiple Pipelines for complex scenarios. This separation enables both simple single-zone control and complex multi-zone coordination.

**Update Loop Timing**: Target ~100ms intervals, loose real-time constraints acceptable for thermal management use case. Modulo-based timing ensures consistent intervals regardless of execution duration.