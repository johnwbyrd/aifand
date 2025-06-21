# fanctl Implementation Plan

## Overview

This document outlines the implementation strategy for `fanctl`, an adaptive thermal management system. This plan is based on the principles and class structures defined in `doc/architecture.md`. The implementation is organized into logical phases, each building upon the last to ensure a stable and testable development process.

---

## Phase 1: Foundational Data Models and Processes

### Objective
Establish the core, non-functional data structures and abstract base classes that form the foundation of the entire system.

### Tasks
1.  **Define `Device` Classes**:
    *   Create the base `Device` class with a flexible `properties` dictionary.
    *   Create the `Sensor` and `Actuator` subclasses.

2.  **Define `State` Type**:
    *   Establish the `State` as a type alias for a dictionary (`Dict[str, Dict]`), representing a collection of device properties.

3.  **Define `Process` Abstract Base Class**:
    *   Create the `Process` ABC with an abstract `execute` method.
    *   Define the `Environment` and `Controller` subclasses of `Process`.

4.  **Basic Project Structure**:
    *   Set up the `src/` directory structure.
    *   Initialize a testing framework (e.g., `pytest`).

---

## Phase 2: The Simplest Testable System

### Objective
To create the most minimal, end-to-end working `System` that can be used for integration testing. This proves the core pipeline logic works before adding complexity.

### Tasks
1.  **Implement `System` Process**:
    *   Create the `System` class.
    *   Implement the main loop, including management of the `context` dictionary and the `Controller` pipeline.

2.  **Implement `Simulation` Environment**:
    *   Create a basic `Simulation` class.
    *   Implement `read()` to return a predictable `State`.
    *   Implement `apply()` to accept a `State` and update its internal simulation.
    *   Start with a simple linear model (e.g., `temp = ambient + fan_speed * factor`).

3.  **Implement a `FixedSpeedController`**:
    *   Create a trivial `Controller` that ignores all inputs and returns a `State` that sets a specific actuator to a hard-coded value.

4.  **Write First Integration Test**:
    *   Create a test that initializes a `System` with the `Simulation` and the `FixedSpeedController`.
    *   Run the `System` for several cycles and assert that the `Simulation`'s internal state reflects the controller's commands.

---

## Phase 3: Core Controller Implementation

### Objective
Develop the primary `Controller`s that provide the system's main functionality. These will be tested against the `Simulation` environment.

### Tasks
1.  **Implement `SafetyController`**:
    *   Create a `Controller` that checks the `actual_state` against critical thresholds.
    *   If a threshold is exceeded, it returns a `State` setting all fans to 100%.

2.  **Implement `PIDController`**:
    *   Create a generic PID controller `Process`.
    *   It should be configurable with a target sensor, an actuator to control, and a setpoint from a `desired_state`.
    *   Write tests to verify its control loop behavior in the `Simulation`.

3.  **Implement `LearningController`**:
    *   Create the ESN-based `Controller`.
    *   Implement the reservoir and the Recursive Least Squares (RLS) learning mechanism.
    *   Initially, test its ability to learn the simple relationships in the `Simulation`.

---

## Phase 4: Real-World Integration

### Objective
Connect the `fanctl` system to physical hardware.

### Tasks
1.  **Implement `Hardware` Environment**:
    *   Create the `Hardware` class.
    *   Implement `hwmon` discovery to find and instantiate `Device` objects for all available sensors and actuators.
    *   Implement `read()` to get current values from the filesystem.
    *   Implement `apply()` to write new values to the filesystem.

2.  **Hardware-in-the-Loop Testing**:
    *   Manually run and test the system on real hardware.
    *   Test the `SafetyController` and `PIDController` with the `Hardware` environment.

---

## Phase 5: Configuration and Usability

### Objective
Make the system configurable and runnable as a standalone service.

### Tasks
1.  **Implement `Profile` Loading**:
    *   Create a parser (e.g., using PyYAML) to load `Profile` files containing named `State`s.
    *   Integrate this loading into the `System`'s initialization.

2.  **Create Main Executable**:
    *   Create a main script (`fanctl.py` or similar) that can load a `System` configuration from a file and run the main loop.

3.  **Daemonization**:
    *   Provide a `systemd` service file to allow `fanctl` to run as a background service.

---

## Phase 6: Advanced Features & Extensibility

### Objective
Build upon the core system to add powerful features and document how users can extend it.

### Tasks
1.  **Hierarchical System Support**:
    *   Implement a serialization mechanism (e.g., gRPC) to allow a `System` to communicate with other `System`s running on remote machines.
    *   This will enable a `System` to use another `System` as a `Device` in its `Environment`.

2.  **Developer Documentation**:
    *   Write a clear tutorial on how to create a custom `Controller`.
    *   Provide well-documented examples of the included `Controller`s.
    *   Set up auto-generated API documentation from docstrings.

---

## Future Phases (Post-Core-Implementation)

*   **Packaging**: Create system packages (e.g., `.deb`, `.rpm`) for easy distribution.
*   **Monitoring**: Implement a Prometheus exporter to expose internal metrics.
*   **Calibration**: Implement an optional calibration `Controller` to accelerate the `LearningController`'s training.
*   **UI/Visualization**: Develop a separate tool for visualizing system state and performance.
