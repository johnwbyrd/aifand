"""Tests for the Device classes."""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src.aifand.base.device import Actuator, Device, Sensor


class TestDevice:
    """Test the base Device class."""

    def test_device_creation_minimal(self):
        """Test creating a device with only required fields."""
        device = Device(name="temp_sensor")

        assert isinstance(device.uuid, UUID)
        assert device.name == "temp_sensor"
        assert device.properties == {}

    def test_device_creation_with_properties(self):
        """Test creating a device with property values."""
        properties = {
            "value": 45.2,
            "unit": "°C",
            "min": 0.0,
            "max": 100.0,
            "label": "CPU Temperature"
        }
        device = Device(name="cpu_temp", properties=properties)

        assert device.name == "cpu_temp"
        assert device.properties == properties
        assert device.properties["value"] == 45.2
        assert device.properties["unit"] == "°C"

    def test_device_properties_access(self):
        """Test accessing properties directly."""
        device = Device(
            name="fan_controller",
            properties={"pwm": 128, "max_pwm": 255}
        )

        assert device.properties["pwm"] == 128
        assert device.properties["max_pwm"] == 255

    def test_device_immutability(self):
        """Test that device properties cannot be modified after creation."""
        device = Device(name="test", properties={"value": 50})

        with pytest.raises(ValidationError):  # pydantic frozen model raises ValidationError
            device.properties = {"value": 60}

    def test_device_serialization(self):
        """Test device serialization to dict/JSON."""
        properties = {"value": 23.5, "unit": "°C", "hwmon_path": "/sys/class/hwmon/hwmon0/temp1_input"}
        device = Device(name="motherboard_temp", properties=properties)

        data = device.model_dump(mode='json')

        assert data["name"] == "motherboard_temp"
        assert data["properties"] == properties
        assert isinstance(data["uuid"], str)

    def test_device_deserialization(self):
        """Test creating device from dict/JSON data."""
        data = {
            "uuid": str(uuid4()),
            "name": "gpu_temp",
            "properties": {"value": 68.0, "unit": "°C", "critical": 95.0}
        }

        device = Device.model_validate(data)

        assert str(device.uuid) == data["uuid"]
        assert device.name == "gpu_temp"
        assert device.properties["value"] == 68.0
        assert device.properties["critical"] == 95.0

    def test_device_equality(self):
        """Test device equality comparison."""
        uuid = uuid4()
        props = {"value": 42, "unit": "RPM"}

        device1 = Device(uuid=uuid, name="fan1", properties=props)
        device2 = Device(uuid=uuid, name="fan1", properties=props)
        device3 = Device(name="fan1", properties=props)  # different UUID

        assert device1 == device2
        assert device1 != device3

    def test_device_representation(self):
        """Test device string representation shows all fields."""
        device = Device(
            name="test_device",
            properties={"value": 100, "unit": "W"}
        )

        repr_str = repr(device)

        assert "Device(" in repr_str
        assert "name='test_device'" in repr_str
        assert "properties={'value': 100, 'unit': 'W'}" in repr_str
        assert "uuid=" in repr_str


class TestSensor:
    """Test the Sensor subclass."""

    def test_sensor_creation(self):
        """Test creating a sensor with thermal properties."""
        sensor = Sensor(
            name="cpu_core_temp",
            properties={
                "value": 52.3,
                "unit": "°C",
                "min": 0.0,
                "max": 100.0,
                "critical": 95.0,
                "hwmon_path": "/sys/class/hwmon/hwmon0/temp2_input",
                "label": "Core 0 Temperature"
            }
        )

        assert isinstance(sensor, Device)
        assert sensor.name == "cpu_core_temp"
        assert sensor.properties["value"] == 52.3
        assert sensor.properties["unit"] == "°C"
        assert sensor.properties["critical"] == 95.0

    def test_sensor_fan_speed(self):
        """Test creating a fan speed sensor."""
        sensor = Sensor(
            name="case_fan_rpm",
            properties={
                "value": 1200,
                "unit": "RPM",
                "min": 0,
                "max": 2000,
                "hwmon_path": "/sys/class/hwmon/hwmon1/fan1_input"
            }
        )

        assert sensor.properties["value"] == 1200
        assert sensor.properties["unit"] == "RPM"
        assert sensor.properties["max"] == 2000

    def test_sensor_inheritance(self):
        """Test that Sensor inherits from Device properly."""
        sensor = Sensor(name="test_sensor", custom_field="custom_value")

        assert isinstance(sensor, Device)
        assert hasattr(sensor, "uuid")
        assert hasattr(sensor, "name")
        assert hasattr(sensor, "properties")
        assert sensor.custom_field == "custom_value"


class TestActuator:
    """Test the Actuator subclass."""

    def test_actuator_creation(self):
        """Test creating an actuator with control properties."""
        actuator = Actuator(
            name="cpu_fan_pwm",
            properties={
                "value": 128,
                "unit": "PWM",
                "min": 0,
                "max": 255,
                "hwmon_path": "/sys/class/hwmon/hwmon0/pwm1",
                "enable_path": "/sys/class/hwmon/hwmon0/pwm1_enable"
            }
        )

        assert isinstance(actuator, Device)
        assert actuator.name == "cpu_fan_pwm"
        assert actuator.properties["value"] == 128
        assert actuator.properties["max"] == 255
        assert "enable_path" in actuator.properties

    def test_actuator_thermal_limit(self):
        """Test creating a thermal limit actuator."""
        actuator = Actuator(
            name="cpu_thermal_limit",
            properties={
                "value": 85.0,
                "unit": "°C",
                "min": 50.0,
                "max": 100.0,
                "hwmon_path": "/sys/class/hwmon/hwmon0/temp1_max"
            }
        )

        assert actuator.properties["value"] == 85.0
        assert actuator.properties["unit"] == "°C"
        assert actuator.properties["min"] == 50.0

    def test_actuator_inheritance(self):
        """Test that Actuator inherits from Device properly."""
        actuator = Actuator(name="test_actuator", control_type="pwm")

        assert isinstance(actuator, Device)
        assert hasattr(actuator, "uuid")
        assert hasattr(actuator, "name")
        assert hasattr(actuator, "properties")
        assert actuator.control_type == "pwm"


class TestDevicePropertyConventions:
    """Test standard property naming conventions for thermal management."""

    def test_temperature_sensor_properties(self):
        """Test standard temperature sensor property names."""
        temp_sensor = Sensor(
            name="cpu_temp",
            properties={
                "value": 45.0,          # Current temperature reading
                "unit": "°C",           # Temperature unit
                "min": 0.0,             # Minimum operating temperature
                "max": 100.0,           # Maximum operating temperature
                "critical": 90.0,       # Critical temperature threshold
                "label": "CPU Temperature",  # Human-readable label
                "hwmon_path": "/sys/class/hwmon/hwmon0/temp1_input",  # Linux hwmon path
                "scale": 0.001          # Scaling factor (millidegrees to degrees)
            }
        )

        # Verify all standard thermal properties are present
        props = temp_sensor.properties
        assert "value" in props
        assert "unit" in props
        assert "min" in props
        assert "max" in props
        assert "critical" in props
        assert "label" in props
        assert "hwmon_path" in props
        assert "scale" in props

    def test_fan_sensor_properties(self):
        """Test standard fan sensor property names."""
        fan_sensor = Sensor(
            name="case_fan",
            properties={
                "value": 1500,          # Current RPM reading
                "unit": "RPM",          # Rotation unit
                "min": 0,               # Minimum RPM (stopped)
                "max": 2000,            # Maximum RPM
                "label": "Case Fan",    # Human-readable label
                "hwmon_path": "/sys/class/hwmon/hwmon1/fan1_input"  # Linux hwmon path
            }
        )

        props = fan_sensor.properties
        assert props["unit"] == "RPM"
        assert props["min"] == 0
        assert isinstance(props["max"], int)

    def test_pwm_actuator_properties(self):
        """Test standard PWM actuator property names."""
        pwm_actuator = Actuator(
            name="cpu_fan_pwm",
            properties={
                "value": 128,           # Current PWM value
                "unit": "PWM",          # PWM unit
                "min": 0,               # Minimum PWM (off)
                "max": 255,             # Maximum PWM (full speed)
                "label": "CPU Fan Control",  # Human-readable label
                "hwmon_path": "/sys/class/hwmon/hwmon0/pwm1",          # Control path
                "enable_path": "/sys/class/hwmon/hwmon0/pwm1_enable"   # Enable path
            }
        )

        props = pwm_actuator.properties
        assert props["unit"] == "PWM"
        assert props["min"] == 0
        assert props["max"] == 255
        assert "enable_path" in props

    def test_thermal_limit_actuator_properties(self):
        """Test standard thermal limit actuator property names."""
        limit_actuator = Actuator(
            name="cpu_thermal_limit",
            properties={
                "value": 85.0,          # Current thermal limit
                "unit": "°C",           # Temperature unit
                "min": 50.0,            # Minimum safe limit
                "max": 100.0,           # Maximum hardware limit
                "label": "CPU Thermal Limit",  # Human-readable label
                "hwmon_path": "/sys/class/hwmon/hwmon0/temp1_max"  # Hardware limit path
            }
        )

        props = limit_actuator.properties
        assert props["unit"] == "°C"
        assert isinstance(props["value"], float)
        assert props["min"] < props["value"] < props["max"]
