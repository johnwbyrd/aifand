# Claude Instructions for aifand Project

## Working Philosophy

This project values careful planning, objective analysis, and precise technical communication. Code quality emerges from thoughtful design, not rapid implementation.

## Planning and Design Requirements

**Always plan before implementing.** Use sequential thinking tools or explicit written planning to work through problems before writing code. Consider the problem space, evaluate alternatives, identify dependencies, and design the approach. Planning prevents rework and produces better architectures.

**Think through testing strategy.** Define specific test scenarios, quantitative success criteria, and failure modes. For aifand specifically, this means creating multiple simulation environments with different thermal behaviors (reasonable and perverse) to test whether controllers remain stable or "fly off the deep end."

**Less but better code.** Choose abstractions carefully. Don't just add new objects or data structures for the sake of adding them; think about how existing architectures can be re-used. Prefer extremely tight and expressive architectures to sprawling or overly complex ones. Simplify designs where they can be simplified. Re-use code, or bring in industry-standard libraries if needed.  Don't confuse code (which should be small) with documentation (Which should be expressive).

## Communication Standards

**Use objective, technical language.** Avoid promotional adjectives like "robust," "comprehensive," "cutting-edge," "powerful," "advanced," "sophisticated," "state-of-the-art," or "professional-grade." These words make claims without evidence. Instead, describe what the code actually does and what specific requirements it meets.

**Write in prose paragraphs for complex topics.** Bullet points fragment information and make relationships unclear. Use structured paragraphs to explain concepts, relationships, and reasoning. Reserve bullet points for simple lists of items or tasks.

**No emojis.** Do not use emojis in code, documentation, commit messages, or any project communication.

**Be specific about implementations.** Instead of "configuration management system," specify "system serialization to/from JSON files." Instead of "comprehensive testing," specify "unit tests, integration tests, and controller stability tests against six simulation environments."

## Project-Specific Detils

**Thermal management specifics.** This project implements adaptive thermal control using Echo State Networks, PID controllers, and safety overrides. The core abstraction separates pure data (State) from logic that transforms it (Process). Controllers operate in pipelines, and systems can be composed hierarchically.

**Simulation-driven development.** Create multiple simulation environments with different thermal behaviors. Test controllers against both reasonable models (linear heat transfer, thermal mass) and perverse models (positive feedback, chaotic dynamics, hardware failures) to validate stability and identify failure modes.

**Deployment scenarios.** Support both standalone daemon operation (systemd service) and library integration (Python module). This requires careful package structure and API design.

**Gold code training.** For the Echo State Network controller, implement training using reference control sequences generated from expert controllers (like well-tuned PID controllers) to accelerate learning compared to pure online learning.

**Architecture.** The system uses Entity (base class with UUID and name), Device (sensors and actuators with flexible properties), State (collections of device properties), and Process (computational units that transform states). The System class orchestrates environments and controller pipelines.

**Controllers.** Implement SafetyController (fail-safe overrides), PIDController (traditional control loops), and LearningController (Echo State Network). Controllers operate in sequence, with safety always last.

**Environments.** Hardware environment interfaces with Linux hwmon filesystem. Simulation environments model thermal behavior mathematically for testing and development.

This project builds a production thermal management system that can also serve as a library for other thermal control applications. The implementation must be reliable enough for real hardware while remaining flexible enough for research and experimentation.