"""State classes for thermal management system snapshots."""

import inspect
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from aifand.base.device import Actuator, Device, Sensor


class State(BaseModel):
    """A snapshot of device properties at a specific moment.

    State represents a collection of devices and their current
    properties. States are unopinionated about their meaning; their role
    (like "actual" or "desired") is defined by how a Process uses them.

    The devices are stored in a dictionary keyed by device name for
    efficient lookup and modification. States are immutable to prevent
    accidental modification and ensure clean data flow through process
    pipelines.
    """

    model_config = ConfigDict(frozen=True)

    devices: dict[str, Device] = Field(
        default_factory=dict,
        description="Collection of devices indexed by name",
    )

    def get_device(self, name: str) -> Device | None:
        """Get a device by name, returning None if not found."""
        return self.devices.get(name)

    def has_device(self, name: str) -> bool:
        """Check if a device exists in this state.

        Args:
            name: Name of device to check

        Returns:
            True if device exists

        """
        return name in self.devices

    def device_names(self) -> list[str]:
        """Return a list of all device names in this state."""
        return list(self.devices.keys())

    def device_count(self) -> int:
        """Return the number of devices in this state."""
        return len(self.devices)

    def with_device(self, device: Device) -> "State":
        """Return a new State with the given device added or updated."""
        # Check permission for this specific device before adding it
        from aifand.base.permissions import can_process_modify_device

        modifying_process = self._find_calling_process()
        if modifying_process and not can_process_modify_device(
            modifying_process, device
        ):
            msg = (
                f"{modifying_process.__class__.__name__} cannot modify "
                f"{device.__class__.__name__} '{device.name}'"
            )
            raise PermissionError(msg)

        new_devices = dict(self.devices)
        new_devices[device.name] = device
        return State(devices=new_devices)

    def with_devices(self, devices: dict[str, Device]) -> "State":
        """Return a new State with devices added or updated.

        Args:
            devices: Dictionary of devices to add/update

        Returns:
            New State instance with updated devices

        """
        # Check permission for each device before adding it
        from aifand.base.permissions import can_process_modify_device

        modifying_process = self._find_calling_process()
        if modifying_process:
            for device in devices.values():
                if not can_process_modify_device(modifying_process, device):
                    msg = (
                        f"{modifying_process.__class__.__name__} cannot modify"
                        f"{device.__class__.__name__} '{device.name}'"
                    )
                    raise PermissionError(msg)

        new_devices = dict(self.devices)
        new_devices.update(devices)
        return State(devices=new_devices)

    def without_device(self, name: str) -> "State":
        """Return a new State with the specified device removed."""
        new_devices = dict(self.devices)
        new_devices.pop(name, None)
        return State(devices=new_devices)

    @classmethod
    def _find_calling_process(cls) -> Any | None:
        """Find the Process instance in the call stack."""
        for frame_info in inspect.stack():
            frame_locals = frame_info.frame.f_locals
            if (
                "self" in frame_locals
                and hasattr(frame_locals["self"], "execute")
                and hasattr(frame_locals["self"], "__class__")
            ):
                # Check if it's actually a Process instance
                from aifand.base.process import Process

                if isinstance(frame_locals["self"], Process):
                    return frame_locals["self"]
        return None

    def get_sensors(self) -> dict[str, Sensor]:
        """Get all sensor devices in this state.

        Returns:
            Dictionary mapping device names to Sensor objects.
        """
        # Filter devices to only Sensors using dictionary comprehension
        return {
            device_name: device
            for device_name, device in self.devices.items()
            if isinstance(device, Sensor)
        }

    def get_actuators(self) -> dict[str, Actuator]:
        """Get all actuator devices in this state.

        Returns:
            Dictionary mapping device names to Actuator objects.
        """
        # Filter devices to only Actuators using dict comprehension
        return {
            device_name: device
            for device_name, device in self.devices.items()
            if isinstance(device, Actuator)
        }

    def __repr__(self) -> str:
        """Return string representation with device info.

        Shows device count and names.
        """
        device_names = ", ".join(self.device_names())
        return f"State({self.device_count()} devices: {device_names})"


class States(dict[str, State]):
    """Collection of named states for thermal management processes.

    Maps state names (like 'actual', 'desired') to State objects.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Any
    ) -> Any:
        """Provide pydantic core schema for States."""
        # Use dict schema since States inherits from dict
        return handler(dict[str, State])
