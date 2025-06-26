"""Tests for device modification permission system."""

import pytest

from aifand import Actuator, Sensor, State

from .mocks import MockController, MockEnvironment


# Helper processes that actually try to modify devices
class SensorModifyingController(MockController):
    """Controller that tries to modify a sensor."""

    def _execute(self, states: dict[str, State]) -> dict[str, State]:
        if "actual" in states:
            sensor = Sensor(name="cpu_temp", properties={"value": 50.0})
            states["actual"] = states["actual"].with_device(sensor)
        return states


class ActuatorModifyingController(MockController):
    """Controller that tries to modify an actuator."""

    def _execute(self, states: dict[str, State]) -> dict[str, State]:
        if "actual" in states:
            actuator = Actuator(name="cpu_fan", properties={"value": 200})
            states["actual"] = states["actual"].with_device(actuator)
        return states


class SensorModifyingEnvironment(MockEnvironment):
    """Environment that tries to modify a sensor."""

    def _execute(self, states: dict[str, State]) -> dict[str, State]:
        if "actual" in states:
            sensor = Sensor(name="cpu_temp", properties={"value": 50.0})
            states["actual"] = states["actual"].with_device(sensor)
        return states


class TestDevicePermissions:
    """Test device modification permissions."""

    def test_environment_can_modify_sensor(self) -> None:
        """Test that Environment can modify sensors."""
        env = SensorModifyingEnvironment(name="test_env")
        state = State()

        # This should work - Environment can modify sensors
        result_states = env.execute({"actual": state})
        assert "actual" in result_states
        assert result_states["actual"].has_device("cpu_temp")

    def test_environment_cannot_modify_actuator(self) -> None:
        """Test that Environment cannot modify actuators."""
        state = State()

        # This should fail - Environment cannot modify actuators
        # We need a test environment that tries to modify an actuator
        class ActuatorModifyingEnvironment(MockEnvironment):
            def _execute(self, states: dict[str, State]) -> dict[str, State]:
                if "actual" in states:
                    actuator = Actuator(
                        name="cpu_fan", properties={"value": 200}
                    )
                    states["actual"] = states["actual"].with_device(actuator)
                return states

        env = ActuatorModifyingEnvironment(name="test_env")
        with pytest.raises(
            PermissionError,
            match=(
                "ActuatorModifyingEnvironment cannot modify Actuator 'cpu_fan'"
            ),
        ):
            env.execute({"actual": state})

    def test_controller_cannot_modify_sensor(self) -> None:
        """Test that Controller cannot modify sensors."""
        controller = SensorModifyingController(name="test_ctrl")
        state = State()

        # This should fail - Controller cannot modify sensors
        with pytest.raises(
            PermissionError,
            match="SensorModifyingController cannot modify Sensor 'cpu_temp'",
        ):
            controller.execute({"actual": state})

    def test_controller_can_modify_actuator(self) -> None:
        """Test that Controller can modify actuators."""
        controller = ActuatorModifyingController(name="test_ctrl")
        state = State()

        # This should work - Controller can modify actuators
        result_states = controller.execute({"actual": state})
        assert "actual" in result_states
        assert result_states["actual"].has_device("cpu_fan")

    def test_environment_can_read_actuator_from_input(self) -> None:
        """Test that Environment can read actuators from input state."""
        # Create state with actuator (outside process context)
        actuator = Actuator(name="cpu_fan", properties={"value": 128})
        state = State().with_device(actuator)

        # Environment that reads actuator and uses its value
        class ActuatorReadingEnvironment(MockEnvironment):
            def _execute(self, states: dict[str, State]) -> dict[str, State]:
                if "actual" in states:
                    # Read actuator value from input state
                    fan_actuator = states["actual"].get_device("cpu_fan")
                    if fan_actuator and isinstance(fan_actuator, Actuator):
                        # Use the actuator value to update a sensor
                        # (simulating reading back the actual fan speed)
                        fan_speed = fan_actuator.properties.get("value", 0)
                        sensor = Sensor(
                            name="cpu_fan_rpm",
                            properties={"value": fan_speed * 10},
                        )
                        states["actual"] = states["actual"].with_device(sensor)
                return states

        env = ActuatorReadingEnvironment(name="test_env")
        result_states = env.execute({"actual": state})

        # Environment should be able to read actuator and create sensor
        assert "actual" in result_states
        assert result_states["actual"].has_device("cpu_fan_rpm")
        fan_sensor = result_states["actual"].get_device("cpu_fan_rpm")
        assert fan_sensor.properties["value"] == 1280  # 128 * 10

    def test_pid_controller_inherits_permissions(self) -> None:
        """Test that PIDController inherits Controller permissions."""

        # Create PID controllers that attempt modifications
        class PIDSensorModifier(MockController):
            def _execute(self, states: dict[str, State]) -> dict[str, State]:
                if "actual" in states:
                    sensor = Sensor(
                        name="cpu_temp", properties={"value": 50.0}
                    )
                    states["actual"] = states["actual"].with_device(sensor)
                return states

        class PIDActuatorModifier(MockController):
            def _execute(self, states: dict[str, State]) -> dict[str, State]:
                if "actual" in states:
                    actuator = Actuator(
                        name="cpu_fan", properties={"value": 128}
                    )
                    states["actual"] = states["actual"].with_device(actuator)
                return states

        state = State()

        # PID should be able to modify actuators (inherits from
        # Controller)
        pid_actuator = PIDActuatorModifier(name="pid_actuator")
        result_states = pid_actuator.execute({"actual": state})
        assert "actual" in result_states
        assert result_states["actual"].has_device("cpu_fan")

        # PID should NOT be able to modify sensors (inherits from
        # Controller)
        pid_sensor = PIDSensorModifier(name="pid_sensor")
        with pytest.raises(
            PermissionError,
            match="PIDSensorModifier cannot modify Sensor 'cpu_temp'",
        ):
            pid_sensor.execute({"actual": state})

    def test_permission_bypass_outside_process_context(self) -> None:
        """Test permissions don't apply outside process context.

        Tests when not called from a process.
        """
        sensor = Sensor(name="cpu_temp", properties={"value": 45.0})
        state = State()

        # This should work - no process in call stack means no
        # permission check
        new_state = state.with_device(sensor)
        assert new_state.has_device("cpu_temp")
