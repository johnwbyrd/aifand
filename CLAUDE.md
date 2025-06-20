# Claude Code Development Guide for fanctl

This document captures the design decisions and development approach for fanctl, an adaptive thermal management system for Linux.

## Project Overview

fanctl automatically learns the relationships between cooling devices (fans) and temperature sensors without manual configuration. It uses machine learning (specifically Echo State Networks) to discover these relationships and provide intelligent thermal control.

## Key Design Decisions

### 1. Clean Abstractions
- **Sensor/Actuator**: Generic base classes, not tied to temperature/fans
- **System**: Groups sensors and actuators together
- **Model**: Transforms sensor readings into actuator commands
- No implementation details leaked into base classes

### 2. Safety Through Composition
- Safety is not a special mode but another Model in the pipeline
- Multiple models can run in series, each potentially overriding previous decisions
- This allows adding safety layers without modifying existing code

### 3. Testing Strategy
- Provides mathematical relationships between sensors/actuators
- Can simulate linear, nonlinear, and chaotic dynamics
- Allows thorough testing without hardware
- Each test scenario is a different TestSystem configuration

### 4. Implementation Choices
- **Echo State Networks (ESN)** for learning
  - Fixed random reservoir, only train output weights
  - Online learning via Recursive Least Squares (RLS)
  - Works immediately without pre-training
  - Natural handling of temporal dynamics
- **1Hz update rate** by default (configurable)
- **Python-first** implementation for accessibility
- **hwmon interface** for Linux integration

### 5. Naming and Structure
- Project name: fanctl (we own fanctl.com but don't mention it yet)
- Clean directory structure without project name embedding:
  ```
  src/
  ├── core/       # Base abstractions
  ├── model/     # Control algorithms
  ├── hal/        # Hardware abstraction
  ├── system/    # System implementations
  └── util/      # Helpers
  ```

### 6. Rejected Approaches
- **CNN/LSTM**: Overkill for this problem, ESN is simpler and works online
- **Manual zone configuration**: Whole point is automatic discovery
- **Special "emergency mode"**: Safety is just another model in the pipeline

### 7. Calibration Strategy
- **Gold codes as optional bootstrap**: Supervised calibration mode for operators
- **Purpose**: Generate high-quality orthogonal training data for ESN
- **Duration**: 30-60 seconds with operator watching temperatures
- **Safety**: Gentle excitation (50-70% fan speeds), operator can abort anytime
- **Benefit**: ESN learns fan-sensor relationships much faster than from normal operation
- **Optional**: System works without calibration, just learns more slowly

## Development Approach

See plan.md for detailed implementation phases and task ordering.

## Performance Targets

- **CPU usage**: < 1% on modern systems
- **Memory usage**: < 100MB resident
- **Response time**: < 100ms for normal operation
- **Emergency response**: < 1 second
- **Learning convergence**: < 5 minutes

## Future Considerations

1. **Multi-zone support**: Handle multiple independent thermal zones
2. **Predictive control**: Anticipate thermal changes
3. **Power optimization**: Balance cooling and power consumption
4. **Remote monitoring**: Export metrics to Prometheus/Grafana
5. **Hardware expansion**: Support for i2c sensors, GPIO fans

## Summary

fanctl combines machine learning with practical engineering to solve a real problem: automatic thermal management without configuration. By using Echo State Networks, we get a system that learns online, handles failures gracefully, and keeps hardware safe through layered protection. The modular design allows easy extension and testing, while the clean abstractions keep the code maintainable.

Remember: The goal is zero-configuration thermal management that just works.