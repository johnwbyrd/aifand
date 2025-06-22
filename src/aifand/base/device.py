"""Device classes for thermal management hardware abstraction."""

from typing import Any, Dict

from pydantic import Field

from .entity import Entity


class Device(Entity):
    """Base class for hardware interface points (sensors and actuators).

    A Device represents a single interface point with hardware, storing
    arbitrary key-value pairs in its properties dictionary. This flexible
    approach supports different hardware types while maintaining consistent
    access patterns.

    Common property naming conventions for thermal management:
    - value: Current reading/setting
    - unit: Measurement unit (C, RPM, PWM, etc.)
    - type: Type of device (e.g., 'temperature', 'fan', 'voltage'
    - min/max: Operating range limits (note: these are themselves dicts with options like 'warning' and 'critical')
    - label: Human-readable description
    - priority: "Importance" of the device, which optimizers can use to prioritize goals
      Higher numbers indicate higher priority, unlike Linux priority levels
      Generally, higher priority devices should be optimized first
    - hwmon_path: Linux hwmon filesystem path
    - enable_path: Hardware enable/disable path (for actuators)
    - scale: Conversion factor for raw hardware values; multiply the raw value by this to get the real value
    - desire: +1 for when we prefer the "value" property to go up, -1 for when we prefer it to go down
      Generally we prefer temperatures to go down, fan speeds to go down, and power consumption to go down,
      but you may prefer green power consumption to go up
    - timestamp: A nanosecond timestamp of the last valid update
    - quality: How well the device is functioning, e.g., "valid", "stale", "failed", "unavailable", etc.
    """

    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Flexible key-value storage for device-specific properties"
    )


class Sensor(Device):
    """A device that reports values from the environment.

    Sensors read environmental conditions like temperature, fan speed,
    voltage, or power consumption. They typically have read-only access
    to hardware and report current state.

    Common sensor types:
    - Temperature sensors (CPU, GPU, motherboard)
    - Fan speed sensors (case fans, CPU cooler)
    - Voltage/power sensors
    - Hardware monitoring sensors
    """

    pass


class Actuator(Device):
    """A device that performs actions on the environment.

    Actuators control hardware settings like fan speeds, thermal limits,
    or power states. They typically have write access to hardware and
    can modify system behavior.

    Common actuator types:
    - PWM fan controllers
    - Thermal limit controllers
    - Power management actuators
    - Hardware enable/disable controls
    """

    pass
