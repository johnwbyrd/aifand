"""Tests for FixedSpeedController."""

from aifand import Actuator, FixedSpeedController, Sensor, State


class TestFixedSpeedController:
    """Test FixedSpeedController stateless pattern implementation."""

    def test_fixed_speed_controller_creation(self) -> None:
        """Test creating FixedSpeedController with configuration."""
        controller = FixedSpeedController(
            name="test_fixed",
            actuator_settings={"cpu_fan": 128.0, "case_fan": 100.0},
        )

        assert controller.name == "test_fixed"
        assert controller.actuator_settings == {
            "cpu_fan": 128.0,
            "case_fan": 100.0,
        }

    def test_fixed_speed_controller_stateless_pattern(self) -> None:
        """Test controller uses stateless three-method pattern."""
        controller = FixedSpeedController(
            name="test_fixed",
            actuator_settings={"cpu_fan": 150.0},
        )

        # Inherits from StatefulProcess so has buffer, but doesn't use
        # historical data
        assert hasattr(controller, "buffer")

        # Create input states with sensor
        sensor = Sensor(name="cpu_temp", properties={"value": 45.0})
        input_state = State(devices={"cpu_temp": sensor})
        input_states = {"actual": input_state}

        # Execute controller
        result_states = controller.execute(input_states)

        # Should have added actuator to desired state
        assert "desired" in result_states
        assert result_states["desired"].has_device("cpu_fan")

        # Check actuator value
        cpu_fan = result_states["desired"].get_device("cpu_fan")
        assert cpu_fan is not None
        assert isinstance(cpu_fan, Actuator)
        assert cpu_fan.properties["value"] == 150.0

        # Original sensor should still be present in actual state
        assert result_states["actual"].has_device("cpu_temp")

    def test_fixed_speed_controller_multiple_actuators(self) -> None:
        """Test controller with multiple actuator settings."""
        controller = FixedSpeedController(
            name="multi_actuator",
            actuator_settings={
                "cpu_fan": 128.0,
                "case_fan": 100.0,
                "gpu_fan": 200.0,
            },
        )

        input_states = {"actual": State()}
        result_states = controller.execute(input_states)

        # Should have all actuators in desired state
        assert "desired" in result_states
        desired_state = result_states["desired"]
        assert desired_state.has_device("cpu_fan")
        assert desired_state.has_device("case_fan")
        assert desired_state.has_device("gpu_fan")

        # Check values
        assert desired_state.get_device("cpu_fan").properties["value"] == 128.0
        assert (
            desired_state.get_device("case_fan").properties["value"] == 100.0
        )
        assert desired_state.get_device("gpu_fan").properties["value"] == 200.0

    def test_fixed_speed_controller_empty_settings(self) -> None:
        """Test controller with no actuator settings."""
        controller = FixedSpeedController(name="empty")

        input_states = {"actual": State()}
        result_states = controller.execute(input_states)

        # Should pass through unchanged
        assert result_states == input_states

    def test_fixed_speed_controller_creates_desired_state(self) -> None:
        """Test controller creates desired state if missing."""
        controller = FixedSpeedController(
            name="test_create",
            actuator_settings={"fan": 100.0},
        )

        # Input without desired state
        input_states = {"actual": State()}
        result_states = controller.execute(input_states)

        # Should create desired state with actuator
        assert "actual" in result_states
        assert "desired" in result_states
        assert result_states["desired"].has_device("fan")

    def test_fixed_speed_controller_updates_existing_actuator(self) -> None:
        """Test controller updates existing actuator."""
        controller = FixedSpeedController(
            name="test_update",
            actuator_settings={"cpu_fan": 200.0},
        )

        # Input with existing actuator
        existing_actuator = Actuator(
            name="cpu_fan", properties={"value": 50.0}
        )
        input_state = State(devices={"cpu_fan": existing_actuator})
        input_states = {"actual": input_state}

        result_states = controller.execute(input_states)

        # Should add actuator to desired state
        assert "desired" in result_states
        updated_fan = result_states["desired"].get_device("cpu_fan")
        assert updated_fan.properties["value"] == 200.0

    def test_fixed_speed_controller_permissions(self) -> None:
        """Test controller can modify actuators (permissions work)."""
        controller = FixedSpeedController(
            name="test_permissions",
            actuator_settings={"cpu_fan": 128.0},
        )

        input_states = {"actual": State()}

        # This should work - Controller can modify actuators
        result_states = controller.execute(input_states)
        assert result_states["desired"].has_device("cpu_fan")

    def test_fixed_speed_controller_serialization(self) -> None:
        """Test controller configuration can be serialized."""
        controller = FixedSpeedController(
            name="test_serialize",
            actuator_settings={"fan1": 100.0, "fan2": 150.0},
        )

        # Serialize configuration
        data = controller.model_dump()

        assert data["name"] == "test_serialize"
        assert data["actuator_settings"] == {"fan1": 100.0, "fan2": 150.0}

        # Recreate from serialized data
        recreated = FixedSpeedController.model_validate(data)
        assert recreated.name == controller.name
        assert recreated.actuator_settings == controller.actuator_settings
