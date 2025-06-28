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

## Project Purpose and Goals

`aifand` is a Python module and daemon for managing thermal environments.

aifand uses classical and AI algorithms to achieve maximal cooling efficiency, for your own definition of "maximal".  You can choose from either classical algorithms such as PID and envelope-based temperature controls, or you can try the novel AI algorithms that learn your temperature environment over time.

Real-world temperature enviroments are complex, non-linear, and can be hard to model in software.  `aifand` is designed to be a forward-thinking class library, permitting multiple generations of AI experiments to determine the "best" cooling algorithms over a variety of environments.  It comes with a number of simulations, that allow you to test your controller algorithms against likely as well as pessimal thermal environment models.

### Key Goals:

-   **Automatic Discovery**: Eliminate the need for users to manually configure thermal zones, map sensors to fans, or define control curves. `aifand` will discover the system's cooling devices and temperature sensors automatically.
-   **Intelligent Control**: Utilize machine learning techniques (specifically, Echo State Networks) to learn the unique thermal relationships within a system. This allows `aifand` to predict how changes in fan speed will affect temperatures, leading to more efficient and stable cooling.
-   **Safety and Reliability**: Implement a robust, layered safety model to prevent overheating and ensure that hardware is always protected, even while the system is learning or encountering unexpected conditions.
-   **Extensibility**: Design a modular, composable architecture that allows developers to easily extend the system with new controllers, support new hardware, or even create complex, hierarchical control systems for multi-machine environments like data centers.
-   **Efficiency**: Optimize cooling to be "just right," avoiding the common issue of fans running at maximum speed unnecessarily, thereby reducing noise and power consumption.

## Development

### Running Tests

```bash
pytest tests/ -v --cov=src/aifand --cov-report=term-missing
```

### Code Quality Checks

Run all quality checks (linting, type checking, tests, security scans):

```bash
hatch run check
```

This mirrors the same checks run in CI/CD.

