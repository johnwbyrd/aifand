"""Device modification permission matrix for thermal management.

This module enforces critical separation of concerns in thermal
management systems:
- Environment processes read sensors and may update sensor readings from
  hardware
- Controller processes read sensors but can only modify actuators
  (decision-making)
- No process should corrupt sensor readings from other processes

The permission system prevents controllers from accidentally or
maliciously modifying sensor readings, which would corrupt the thermal
control feedback loop. This is essential for safety in thermal
management where incorrect sensor readings could lead to inadequate
cooling and hardware damage.

Permission checking occurs at runtime using call stack inspection to
identify the modifying process when State.with_device() is called. The
permission matrix uses class-based rules with inheritance support and
ordered precedence checking.

Without this system, a buggy PID controller could modify temperature
sensor readings and create false feedback, potentially causing thermal
runaway or inadequate cooling.
"""

from typing import TYPE_CHECKING, Any, List, Tuple, Type

if TYPE_CHECKING:
    from .device import Device
    from .process import Process

# Permission matrix: List of ((ProcessClass, DeviceClass), bool) in
# order of precedence
# More specific rules are checked first
DEVICE_PERMISSIONS: List[Tuple[Tuple[Type[Any], Type[Any]], bool]] = []


def register_permissions() -> None:
    """Register device modification permissions.

    This function registers the permission matrix for device
    modifications by processes after all necessary imports are
    available.
    """
    from .device import Actuator, Device, Sensor
    from .process import Controller, Environment, Process

    global DEVICE_PERMISSIONS
    DEVICE_PERMISSIONS = [
        # More specific rules first - these override general rules
        ((Environment, Sensor), True),
        ((Environment, Actuator), True),
        ((Controller, Actuator), True),
        # Controllers cannot modify Sensors - explicitly denied
        ((Controller, Sensor), False),
        # General fallback for testing - base Process can modify
        # anything
        ((Process, Device), True),
    ]


def can_process_modify_device(process: "Process", device: "Device") -> bool:
    """Check if a process is allowed to modify a device.

    Args:
        process: The process attempting the modification
        device: The device being modified

    Returns:
        True if modification is allowed, False otherwise (default
        deny)

    """
    if not DEVICE_PERMISSIONS:
        register_permissions()

    for (process_class, device_class), allowed in DEVICE_PERMISSIONS:
        if isinstance(process, process_class) and isinstance(
            device, device_class
        ):
            return bool(allowed)

    return False  # Default deny - must be explicitly granted
