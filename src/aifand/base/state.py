"""State classes for thermal management system snapshots."""

from typing import Dict

from pydantic import BaseModel, ConfigDict, Field

from .device import Device


class State(BaseModel):
    """A snapshot of device properties at a specific moment.

    State represents a collection of devices and their current properties.
    States are unopinionated about their meaning; their role (like "actual"
    or "desired") is defined by how a Process uses them.

    The devices are stored in a dictionary keyed by device name for efficient
    lookup and modification. States are immutable to prevent accidental
    modification and ensure clean data flow through process pipelines.
    """

    model_config = ConfigDict(frozen=True)

    devices: Dict[str, Device] = Field(default_factory=dict, description="Collection of devices indexed by name")

    def get_device(self, name: str) -> Device | None:
        """Get a device by name, returning None if not found."""
        return self.devices.get(name)

    def has_device(self, name: str) -> bool:
        """Check if a device with the given name exists in this state."""
        return name in self.devices

    def device_names(self) -> list[str]:
        """Return a list of all device names in this state."""
        return list(self.devices.keys())

    def device_count(self) -> int:
        """Return the number of devices in this state."""
        return len(self.devices)

    def with_device(self, device: Device) -> "State":
        """Return a new State with the given device added or updated."""
        new_devices = dict(self.devices)
        new_devices[device.name] = device
        return State(devices=new_devices)

    def with_devices(self, devices: Dict[str, Device]) -> "State":
        """Return a new State with the given devices added or updated."""
        new_devices = dict(self.devices)
        new_devices.update(devices)
        return State(devices=new_devices)

    def without_device(self, name: str) -> "State":
        """Return a new State with the specified device removed."""
        new_devices = dict(self.devices)
        new_devices.pop(name, None)
        return State(devices=new_devices)

    def __repr__(self) -> str:
        """Return a string representation showing device count and names."""
        device_names = ", ".join(self.device_names())
        return f"State({self.device_count()} devices: {device_names})"
