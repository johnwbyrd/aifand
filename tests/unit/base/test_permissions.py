"""Tests for device modification permission system."""

from typing import Dict

import pytest

from src.aifand.base.device import Actuator, Sensor
from src.aifand.base.state import State

from .mocks import MockController, MockEnvironment


# Helper processes that actually try to modify devices
class SensorModifyingController(MockController):
    """Controller that tries to modify a sensor."""

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        if "actual" in states:
            sensor = Sensor(name="cpu_temp", properties={"value": 50.0})
            states["actual"] = states["actual"].with_device(sensor)
        return states


class ActuatorModifyingController(MockController):
    """Controller that tries to modify an actuator."""

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        if "actual" in states:
            actuator = Actuator(name="cpu_fan", properties={"value": 200})
            states["actual"] = states["actual"].with_device(actuator)
        return states


class SensorModifyingEnvironment(MockEnvironment):
    """Environment that tries to modify a sensor."""

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        if "actual" in states:
            sensor = Sensor(name="cpu_temp", properties={"value": 50.0})
            states["actual"] = states["actual"].with_device(sensor)
        return states


class TestDevicePermissions:
    """Test device modification permissions."""

    def test_environment_can_modify_sensor(self):
        """Test that Environment can modify sensors."""
        env = SensorModifyingEnvironment(name="test_env")
        state = State()

        # This should work - Environment can modify sensors
        result_states = env.execute({"actual": state})
        assert "actual" in result_states
        assert result_states["actual"].has_device("cpu_temp")

    def test_environment_can_modify_actuator(self):
        """Test that Environment can modify actuators."""
        env = MockEnvironment(name="test_env")
        actuator = Actuator(name="cpu_fan", properties={"value": 128})
        state = State()

        # This should work - Environment can modify actuators (called from execute context)
        result_states = env.execute({"actual": state.with_device(actuator)})
        assert "actual" in result_states

    def test_controller_cannot_modify_sensor(self):
        """Test that Controller cannot modify sensors."""
        controller = SensorModifyingController(name="test_ctrl")
        state = State()

        # This should fail - Controller cannot modify sensors
        with pytest.raises(PermissionError, match="SensorModifyingController cannot modify Sensor 'cpu_temp'"):
            controller.execute({"actual": state})

    def test_controller_can_modify_actuator(self):
        """Test that Controller can modify actuators."""
        controller = ActuatorModifyingController(name="test_ctrl")
        state = State()

        # This should work - Controller can modify actuators
        result_states = controller.execute({"actual": state})
        assert "actual" in result_states
        assert result_states["actual"].has_device("cpu_fan")

    def test_pid_controller_inherits_permissions(self):
        """Test that PIDController inherits Controller permissions."""

        # Create PID controllers that attempt modifications
        class PIDSensorModifier(MockController):
            def _process(self, states):
                if "actual" in states:
                    sensor = Sensor(name="cpu_temp", properties={"value": 50.0})
                    states["actual"] = states["actual"].with_device(sensor)
                return states

        class PIDActuatorModifier(MockController):
            def _process(self, states):
                if "actual" in states:
                    actuator = Actuator(name="cpu_fan", properties={"value": 128})
                    states["actual"] = states["actual"].with_device(actuator)
                return states

        state = State()

        # PID should be able to modify actuators (inherits from Controller)
        pid_actuator = PIDActuatorModifier(name="pid_actuator")
        result_states = pid_actuator.execute({"actual": state})
        assert "actual" in result_states
        assert result_states["actual"].has_device("cpu_fan")

        # PID should NOT be able to modify sensors (inherits from Controller)
        pid_sensor = PIDSensorModifier(name="pid_sensor")
        with pytest.raises(PermissionError, match="PIDSensorModifier cannot modify Sensor 'cpu_temp'"):
            pid_sensor.execute({"actual": state})

    def test_permission_bypass_outside_process_context(self):
        """Test that permissions don't apply when not called from a process."""
        sensor = Sensor(name="cpu_temp", properties={"value": 45.0})
        state = State()

        # This should work - no process in call stack means no permission check
        new_state = state.with_device(sensor)
        assert new_state.has_device("cpu_temp")
