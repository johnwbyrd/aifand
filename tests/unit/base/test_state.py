"""Tests for the State class."""

import pytest
from pydantic import ValidationError

from src.aifand.base.device import Actuator, Sensor
from src.aifand.base.state import State


class TestState:
    """Test the State class functionality."""

    def test_state_creation_empty(self):
        """Test creating an empty state."""
        state = State()

        assert state.devices == {}
        assert state.device_count() == 0
        assert state.device_names() == []

    def test_state_creation_with_devices(self):
        """Test creating a state with initial devices."""
        temp_sensor = Sensor(
            name="cpu_temp", properties={"value": 45.0, "unit": "°C"}
        )
        fan_actuator = Actuator(
            name="cpu_fan", properties={"value": 128, "unit": "PWM"}
        )

        devices = {"cpu_temp": temp_sensor, "cpu_fan": fan_actuator}
        state = State(devices=devices)

        assert state.device_count() == 2
        assert "cpu_temp" in state.device_names()
        assert "cpu_fan" in state.device_names()
        assert state.get_device("cpu_temp") == temp_sensor
        assert state.get_device("cpu_fan") == fan_actuator

    def test_state_immutability(self):
        """Test that states cannot be modified after creation."""
        temp_sensor = Sensor(name="cpu_temp", properties={"value": 45.0})
        state = State(devices={"cpu_temp": temp_sensor})

        # State should be frozen
        with pytest.raises(ValidationError):
            state.devices = {}

    def test_state_device_access(self):
        """Test device access methods."""
        temp_sensor = Sensor(name="cpu_temp", properties={"value": 45.0})
        state = State(devices={"cpu_temp": temp_sensor})

        # Test get_device
        assert state.get_device("cpu_temp") == temp_sensor
        assert state.get_device("nonexistent") is None

        # Test has_device
        assert state.has_device("cpu_temp") is True
        assert state.has_device("nonexistent") is False

        # Test device_names and device_count
        assert state.device_names() == ["cpu_temp"]
        assert state.device_count() == 1

    def test_state_with_device(self):
        """Test adding/updating devices with with_device."""
        original_sensor = Sensor(name="cpu_temp", properties={"value": 45.0})
        state = State(devices={"cpu_temp": original_sensor})

        # Add a new device
        fan_actuator = Actuator(name="cpu_fan", properties={"value": 128})
        new_state = state.with_device(fan_actuator)

        # Original state unchanged
        assert state.device_count() == 1
        assert not state.has_device("cpu_fan")

        # New state has both devices
        assert new_state.device_count() == 2
        assert new_state.has_device("cpu_temp")
        assert new_state.has_device("cpu_fan")
        assert new_state.get_device("cpu_fan") == fan_actuator

        # Update existing device
        updated_sensor = Sensor(name="cpu_temp", properties={"value": 50.0})
        updated_state = new_state.with_device(updated_sensor)

        assert updated_state.device_count() == 2
        assert updated_state.get_device("cpu_temp") == updated_sensor
        assert updated_state.get_device("cpu_temp") != original_sensor

    def test_state_with_devices(self):
        """Test adding/updating multiple devices with with_devices."""
        original_state = State()

        devices = {
            "cpu_temp": Sensor(name="cpu_temp", properties={"value": 45.0}),
            "cpu_fan": Actuator(name="cpu_fan", properties={"value": 128}),
        }

        new_state = original_state.with_devices(devices)

        # Original state unchanged
        assert original_state.device_count() == 0

        # New state has devices
        assert new_state.device_count() == 2
        assert new_state.has_device("cpu_temp")
        assert new_state.has_device("cpu_fan")

    def test_state_without_device(self):
        """Test removing devices with without_device."""
        devices = {
            "cpu_temp": Sensor(name="cpu_temp", properties={"value": 45.0}),
            "cpu_fan": Actuator(name="cpu_fan", properties={"value": 128}),
        }
        state = State(devices=devices)

        # Remove existing device
        new_state = state.without_device("cpu_fan")

        # Original state unchanged
        assert state.device_count() == 2
        assert state.has_device("cpu_fan")

        # New state has device removed
        assert new_state.device_count() == 1
        assert new_state.has_device("cpu_temp")
        assert not new_state.has_device("cpu_fan")

        # Remove nonexistent device (should not error)
        same_state = new_state.without_device("nonexistent")
        assert same_state.device_count() == 1

    def test_state_representation(self):
        """Test state string representation."""
        # Empty state
        empty_state = State()
        assert "0 devices" in repr(empty_state)

        # State with devices
        devices = {
            "cpu_temp": Sensor(name="cpu_temp", properties={"value": 45.0}),
            "cpu_fan": Actuator(name="cpu_fan", properties={"value": 128}),
        }
        state = State(devices=devices)
        repr_str = repr(state)

        assert "2 devices" in repr_str
        assert "cpu_temp" in repr_str
        assert "cpu_fan" in repr_str

    def test_state_serialization(self):
        """Test state serialization and deserialization."""
        temp_sensor = Sensor(
            name="cpu_temp", properties={"value": 45.0, "unit": "°C"}
        )
        original_state = State(devices={"cpu_temp": temp_sensor})

        # Serialize to dict
        state_dict = original_state.model_dump()
        assert "devices" in state_dict
        assert "cpu_temp" in state_dict["devices"]

        # Serialize to JSON and back
        state_json = original_state.model_dump_json()
        reconstructed_state = State.model_validate_json(state_json)

        assert (
            reconstructed_state.device_count() == original_state.device_count()
        )
        assert reconstructed_state.has_device("cpu_temp")

        # Device should be equivalent (though potentially different UUID)
        original_device = original_state.get_device("cpu_temp")
        reconstructed_device = reconstructed_state.get_device("cpu_temp")
        assert original_device.name == reconstructed_device.name
        assert original_device.properties == reconstructed_device.properties

    def test_state_equality(self):
        """Test state equality comparison."""
        temp_sensor = Sensor(name="cpu_temp", properties={"value": 45.0})

        state1 = State(devices={"cpu_temp": temp_sensor})
        state2 = State(devices={"cpu_temp": temp_sensor})
        state3 = State()

        # Same devices should be equal
        assert state1 == state2

        # Different device sets should not be equal
        assert state1 != state3
