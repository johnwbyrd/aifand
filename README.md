# aifand - Adaptive Thermal Management

**NOTE: This project is currently in the architectural design and development phase. It is not yet ready for deployment or production use.**

## Project Purpose and Goals

`aifand` is an intelligent, adaptive thermal management system for Linux-based computers. The primary goal of this project is to create a "zero-configuration" fan controller that automatically learns the thermal characteristics of a system and adjusts cooling devices to maintain optimal temperatures without requiring any manual setup.

### Key Goals:

-   **Automatic Discovery**: Eliminate the need for users to manually configure thermal zones, map sensors to fans, or define control curves. `aifand` will discover the system's cooling devices and temperature sensors automatically.
-   **Intelligent Control**: Utilize machine learning techniques (specifically, Echo State Networks) to learn the unique thermal relationships within a system. This allows `aifand` to predict how changes in fan speed will affect temperatures, leading to more efficient and stable cooling.
-   **Safety and Reliability**: Implement a robust, layered safety model to prevent overheating and ensure that hardware is always protected, even while the system is learning or encountering unexpected conditions.
-   **Extensibility**: Design a modular, composable architecture that allows developers to easily extend the system with new controllers, support new hardware, or even create complex, hierarchical control systems for multi-machine environments like data centers.
-   **Efficiency**: Optimize cooling to be "just right," avoiding the common issue of fans running at maximum speed unnecessarily, thereby reducing noise and power consumption.

## Current Status

The project is actively under development. The core architecture has been designed, focusing on a pipeline of composable `Stage`s (`Controllers` and `Environments`) managed by a central `System` orchestrator.

We are currently in the process of implementing the foundational classes and testing frameworks.
