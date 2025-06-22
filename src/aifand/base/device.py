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

    Standard property naming conventions for thermal management:
    - value: Current reading/setting
    - unit: Measurement unit (°C, RPM, PWM, etc.)
    - min/max: Operating range limits
    - critical: Critical threshold (for sensors)
    - label: Human-readable description
    - hwmon_path: Linux hwmon filesystem path
    - enable_path: Hardware enable/disable path (for actuators)
    - scale: Conversion factor for raw hardware values
    """

    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible key-value storage for device-specific properties"
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
