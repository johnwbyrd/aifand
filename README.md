# aifand - Adaptive Thermal Management

[![Main CI](https://github.com/johnwbyrd/aifand/actions/workflows/main-ci.yml/badge.svg)](https://github.com/johnwbyrd/aifand/actions/workflows/main-ci.yml)
[![codecov](https://codecov.io/gh/johnwbyrd/aifand/branch/main/graph/badge.svg)](https://codecov.io/gh/johnwbyrd/aifand)
[![Python >=3.12](https://img.shields.io/badge/python->=3.12-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3+](https://img.shields.io/badge/License-AGPL_v3+-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

![aifand android image](https://github.com/user-attachments/assets/6dc35fa3-9b71-4b3e-af18-f87c91695d6d)

**NOTE: This project is currently in the architectural design and development phase. It is not yet ready for deployment or production use.**

## What Is aifand?

`aifand` is a next-generation thermal management system that automatically learns your hardware's thermal behavior and adapts control strategies accordingly. Unlike traditional fan controllers that require manual configuration and use fixed curves, aifand discovers your system's thermal characteristics and optimizes cooling in real-time.

The system serves three distinct purposes:
- **Local thermal control** with zero-configuration automatic discovery and AI-powered adaptation
- **Distributed thermal management** across networks for data centers and multi-machine environments  
- **Experimental platform** for thermal control research across scales from embedded systems to HVAC

## What Makes aifand Different

Traditional fan control tools require you to manually map sensors to fans, define temperature curves, and tune PID parameters for each system. They operate reactively, responding to temperature changes after they occur, and work only on single machines.

aifand takes a fundamentally different approach:

**Automatic Discovery**: No configuration files, no manual sensor mapping. aifand discovers your cooling hardware automatically and learns how it affects temperatures.

**Predictive AI Control**: Using Echo State Networks and other machine learning techniques, aifand learns your system's unique thermal relationships and predicts how control changes will affect temperatures before making adjustments.

**Distributed Architecture**: Built from the ground up for network operation. Monitor and control thermal systems across multiple machines, data centers, or cloud environments through a unified interface.

**Experimental Platform**: Unlike monolithic fan control applications, aifand is designed as a composable class library that enables thermal experimentation across vastly different scales - from small embedded computers to large HVAC systems with strongly non-linear thermal behavior. The modular architecture allows researchers and engineers to experiment with different control strategies to optimize for their specific goals: minimizing cost, reducing noise, maximizing efficiency, or ensuring safety under extreme conditions.

**Safety-First Design**: Layered safety systems ensure your hardware stays protected even while the system is learning or experimenting with new control strategies.

## Key Features

- **Zero Configuration**: Automatic hardware discovery eliminates manual setup
- **AI-Powered Learning**: System learns optimal control strategies for your specific hardware
- **Network Distributed**: Control thermal systems across multiple machines and networks
- **Multi-Algorithm Support**: Classical controllers (PID, fixed curves) and AI algorithms (Echo State Networks, neural networks)
- **Multi-Scale Experimentation**: Test thermal control strategies across different system scales and optimize for cost, noise, efficiency, or safety
- **Safety Guarantees**: Multiple safety layers prevent overheating during learning or experimentation

## Quick Start

*Note: This is a preview of the planned interface - the system is still in development*

```python
from aifand import System, Hardware, EchoStateNetworkController

# Automatic hardware discovery and AI control
system = System([
    Hardware(),  # Auto-discovers sensors and actuators
    EchoStateNetworkController()  # Learns optimal control
])

# Run with safety monitoring
system.run()
```

For distributed operation:
```python
# Monitor remote systems
remote_system = System.connect("thermal-server.local:8080")
print(f"Remote CPU temp: {remote_system.get_sensor('cpu_temp').value}°C")
```

## Development

### Running Tests

```bash
hatch run tests
```

This runs the complete test suite including unit tests, integration tests, and thermal simulation validation.

### Code Quality

All quality checks (linting, type checking, security scans):

```bash
hatch run check
```

## Documentation

- [Architecture Documentation](doc/architecture.md) - Detailed system design and object model
- [Implementation Roadmap](doc/todo.md) - Current development status and planned features

## License

AGPL-3.0-or-later. See LICENSE file for details.