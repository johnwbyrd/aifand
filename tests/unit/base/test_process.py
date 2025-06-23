"""Tests for the Process classes."""

import logging
from typing import Dict, List

import pytest
from pydantic import Field

from src.aifand.base.device import Actuator, Device, Sensor
from src.aifand.base.process import Controller, Environment, Process
from src.aifand.base.state import State

from .mocks import MockController, MockEnvironment


# Test Process implementations for testing
class SimpleProcess(Process):
    """Concrete Process implementation for testing."""

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Test implementation that adds a test device to the 'actual' state."""
        if "actual" in states:
            test_device = Device(name="test_device", properties={"value": 42, "processed_by": self.name})
            states["actual"] = states["actual"].with_device(test_device)
        return states

    def _calculate_next_tick_time(self) -> int:
        """Simple fixed interval timing for tests."""
        return self.start_time + (self.execution_count * self.interval_ns)

    def _select_processes_to_execute(self) -> List[Process]:
        """Return all children for unified timing (like Pipeline)."""
        return self.children


class MultiplyProcess(Process):
    """Process that multiplies device values by a factor."""

    factor: float = Field(default=2.0, description="Multiplication factor for device values")

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Multiply all device values by the factor."""
        result_states = dict(states)

        for state_name, state in states.items():
            new_devices = {}
            for device_name, device in state.devices.items():
                if "value" in device.properties and isinstance(device.properties["value"], (int, float)):
                    new_properties = dict(device.properties)
                    new_properties["value"] = device.properties["value"] * self.factor
                    new_device = Device(name=device.name, properties=new_properties, uuid=device.uuid)
                    new_devices[device_name] = new_device
                else:
                    new_devices[device_name] = device

            result_states[state_name] = State(devices=new_devices)

        return result_states

    def _calculate_next_tick_time(self) -> int:
        """Simple fixed interval timing for tests."""
        return self.start_time + (self.execution_count * self.interval_ns)

    def _select_processes_to_execute(self) -> List[Process]:
        """Return all children for unified timing (like Pipeline)."""
        return self.children


class FailingProcess(Process):
    """Process that always raises an exception."""

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Always raise an exception."""
        raise RuntimeError("This process always fails")

    def _calculate_next_tick_time(self) -> int:
        """Simple fixed interval timing for tests."""
        return self.start_time + (self.execution_count * self.interval_ns)

    def _select_processes_to_execute(self) -> List[Process]:
        """Return all children for unified timing (like Pipeline)."""
        return self.children


class TestEnvironment(MockEnvironment):
    """Environment implementation for process testing."""

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Test environment that adds a sensor reading."""
        if "actual" in states:
            sensor = Sensor(name="env_sensor", properties={"value": 25.0, "unit": "°C"})
            states["actual"] = states["actual"].with_device(sensor)
        return states


class TestController(MockController):
    """Controller implementation for process testing."""

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Test controller that adds an actuator setting."""
        if "actual" in states:
            actuator = Actuator(name="ctrl_actuator", properties={"value": 128, "unit": "PWM"})
            states["actual"] = states["actual"].with_device(actuator)
        return states


class TestProcessBase:
    """Test the base Process class functionality."""

    def test_process_cannot_be_instantiated_directly(self):
        """Test that Process is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            Process(name="test")

    def test_process_creation(self):
        """Test creating a concrete process."""
        process = SimpleProcess(name="test_process")

        assert process.name == "test_process"
        assert process.children == []
        assert hasattr(process, "uuid")

    def test_process_with_children(self):
        """Test creating a process with child processes."""
        child1 = SimpleProcess(name="child1")
        child2 = SimpleProcess(name="child2")

        parent = SimpleProcess(name="parent", children=[child1, child2])

        assert len(parent.children) == 2
        assert parent.children[0].name == "child1"
        assert parent.children[1].name == "child2"

    def test_process_logger_creation(self):
        """Test that each process gets its own logger."""
        process = SimpleProcess(name="test_process")
        logger = process.get_logger()

        assert isinstance(logger, logging.Logger)
        assert "SimpleProcess" in logger.name
        assert "test_process" in logger.name

    def test_append_child_method(self):
        """Test adding children with append_child method."""
        parent = SimpleProcess(name="parent")
        child = SimpleProcess(name="child")

        # append_child modifies in place (mutable)
        parent.append_child(child)

        # Parent now has child
        assert len(parent.children) == 1
        assert parent.children[0].name == "child"


class TestProcessManipulation:
    """Test process pipeline manipulation methods."""

    def test_insert_before_existing_process(self):
        """Test inserting a process before an existing one."""
        parent = SimpleProcess(name="parent")
        first = SimpleProcess(name="first")
        second = SimpleProcess(name="second")
        new_process = SimpleProcess(name="new")

        parent.append_child(first)
        parent.append_child(second)

        # Insert before second
        parent.insert_before("second", new_process)

        assert len(parent.children) == 3
        assert parent.children[0].name == "first"
        assert parent.children[1].name == "new"
        assert parent.children[2].name == "second"

    def test_insert_before_first_process(self):
        """Test inserting before the first process."""
        parent = SimpleProcess(name="parent")
        first = SimpleProcess(name="first")
        new_process = SimpleProcess(name="new")

        parent.append_child(first)
        parent.insert_before("first", new_process)

        assert len(parent.children) == 2
        assert parent.children[0].name == "new"
        assert parent.children[1].name == "first"

    def test_insert_before_nonexistent_process(self):
        """Test inserting before a process that doesn't exist."""
        parent = SimpleProcess(name="parent")
        first = SimpleProcess(name="first")
        new_process = SimpleProcess(name="new")

        parent.append_child(first)

        with pytest.raises(ValueError, match="Process 'nonexistent' not found in pipeline"):
            parent.insert_before("nonexistent", new_process)

    def test_insert_after_existing_process(self):
        """Test inserting a process after an existing one."""
        parent = SimpleProcess(name="parent")
        first = SimpleProcess(name="first")
        second = SimpleProcess(name="second")
        new_process = SimpleProcess(name="new")

        parent.append_child(first)
        parent.append_child(second)

        # Insert after first
        parent.insert_after("first", new_process)

        assert len(parent.children) == 3
        assert parent.children[0].name == "first"
        assert parent.children[1].name == "new"
        assert parent.children[2].name == "second"

    def test_insert_after_last_process(self):
        """Test inserting after the last process."""
        parent = SimpleProcess(name="parent")
        first = SimpleProcess(name="first")
        new_process = SimpleProcess(name="new")

        parent.append_child(first)
        parent.insert_after("first", new_process)

        assert len(parent.children) == 2
        assert parent.children[0].name == "first"
        assert parent.children[1].name == "new"

    def test_insert_after_nonexistent_process(self):
        """Test inserting after a process that doesn't exist."""
        parent = SimpleProcess(name="parent")
        first = SimpleProcess(name="first")
        new_process = SimpleProcess(name="new")

        parent.append_child(first)

        with pytest.raises(ValueError, match="Process 'nonexistent' not found in pipeline"):
            parent.insert_after("nonexistent", new_process)

    def test_remove_child_existing_process(self):
        """Test removing an existing child process."""
        parent = SimpleProcess(name="parent")
        first = SimpleProcess(name="first")
        second = SimpleProcess(name="second")
        third = SimpleProcess(name="third")

        parent.append_child(first)
        parent.append_child(second)
        parent.append_child(third)

        # Remove middle process
        result = parent.remove_child("second")

        assert result is True
        assert len(parent.children) == 2
        assert parent.children[0].name == "first"
        assert parent.children[1].name == "third"

    def test_remove_child_first_process(self):
        """Test removing the first child process."""
        parent = SimpleProcess(name="parent")
        first = SimpleProcess(name="first")
        second = SimpleProcess(name="second")

        parent.append_child(first)
        parent.append_child(second)

        result = parent.remove_child("first")

        assert result is True
        assert len(parent.children) == 1
        assert parent.children[0].name == "second"

    def test_remove_child_last_process(self):
        """Test removing the last child process."""
        parent = SimpleProcess(name="parent")
        first = SimpleProcess(name="first")
        second = SimpleProcess(name="second")

        parent.append_child(first)
        parent.append_child(second)

        result = parent.remove_child("second")

        assert result is True
        assert len(parent.children) == 1
        assert parent.children[0].name == "first"

    def test_remove_child_nonexistent_process(self):
        """Test removing a process that doesn't exist."""
        parent = SimpleProcess(name="parent")
        first = SimpleProcess(name="first")

        parent.append_child(first)

        result = parent.remove_child("nonexistent")

        assert result is False
        assert len(parent.children) == 1
        assert parent.children[0].name == "first"

    def test_remove_child_empty_pipeline(self):
        """Test removing from an empty pipeline."""
        parent = SimpleProcess(name="parent")

        result = parent.remove_child("nonexistent")

        assert result is False
        assert len(parent.children) == 0


class TestProcessExecution:
    """Test process execution behavior."""

    def test_execute_single_process_no_children(self):
        """Test executing a process with no children."""
        process = SimpleProcess(name="test")

        # Create test states
        initial_device = Device(name="initial", properties={"value": 10})
        initial_state = State(devices={"initial": initial_device})
        states = {"actual": initial_state}

        # Execute process
        result_states = process.execute(states)

        # Should have original device plus test device added by SimpleProcess
        assert "actual" in result_states
        actual_state = result_states["actual"]
        assert actual_state.has_device("initial")
        assert actual_state.has_device("test_device")

        # Test device should have expected properties
        test_device = actual_state.get_device("test_device")
        assert test_device.properties["value"] == 42
        assert test_device.properties["processed_by"] == "test"

    def test_execute_pipeline_with_children(self):
        """Test executing a process with child pipeline."""
        # Create child processes
        multiply_by_2 = MultiplyProcess(name="multiply2", factor=2.0)
        multiply_by_3 = MultiplyProcess(name="multiply3", factor=3.0)

        # Create parent with children
        parent = SimpleProcess(name="parent", children=[multiply_by_2, multiply_by_3])

        # Create test state
        initial_device = Device(name="test_value", properties={"value": 5})
        initial_state = State(devices={"test_value": initial_device})
        states = {"actual": initial_state}

        # Execute pipeline: 5 * 2 * 3 = 30
        result_states = parent.execute(states)

        actual_state = result_states["actual"]
        result_device = actual_state.get_device("test_value")
        assert result_device.properties["value"] == 30

    def test_execute_preserves_input_states(self):
        """Test that input states are never modified."""
        process = SimpleProcess(name="test")

        initial_device = Device(name="test", properties={"value": 10})
        initial_state = State(devices={"test": initial_device})
        original_states = {"actual": initial_state}

        # Execute process
        result_states = process.execute(original_states)

        # Original states should be unchanged
        assert len(original_states["actual"].devices) == 1
        assert not original_states["actual"].has_device("test_device")

        # Result states should have changes
        assert len(result_states["actual"].devices) == 2
        assert result_states["actual"].has_device("test_device")

    def test_execute_multiple_state_types(self):
        """Test execution with multiple named states."""
        process = SimpleProcess(name="test")

        actual_device = Device(name="actual_device", properties={"value": 10})
        desired_device = Device(name="desired_device", properties={"value": 20})

        states = {
            "actual": State(devices={"actual_device": actual_device}),
            "desired": State(devices={"desired_device": desired_device}),
        }

        result_states = process.execute(states)

        # Both states should be present
        assert "actual" in result_states
        assert "desired" in result_states

        # Only "actual" should have the test device (per TestProcess implementation)
        assert result_states["actual"].has_device("test_device")
        assert not result_states["desired"].has_device("test_device")


class TestProcessErrorHandling:
    """Test process error handling behavior."""

    def test_failing_process_with_no_children(self, caplog):
        """Test error handling when a process with no children fails."""
        process = FailingProcess(name="failing")

        initial_device = Device(name="test", properties={"value": 10})
        initial_state = State(devices={"test": initial_device})
        states = {"actual": initial_state}

        # Should not raise exception, but should log error
        with caplog.at_level(logging.ERROR):
            result_states = process.execute(states)

        # Should have error log
        assert "Process failing failed during execution" in caplog.text
        assert "This process always fails" in caplog.text

        # Should return input states unchanged (passthrough)
        assert result_states == states

    def test_failing_child_in_pipeline(self, caplog):
        """Test error handling when a child process fails."""
        # Create pipeline: working -> failing -> working
        working1 = MultiplyProcess(name="working1", factor=2.0)
        failing = FailingProcess(name="failing")
        working2 = MultiplyProcess(name="working2", factor=3.0)

        parent = SimpleProcess(name="parent", children=[working1, failing, working2])

        initial_device = Device(name="test", properties={"value": 5})
        initial_state = State(devices={"test": initial_device})
        states = {"actual": initial_state}

        with caplog.at_level(logging.ERROR):
            result_states = parent.execute(states)

        # Should have error log for failing child
        assert "Process failing failed during execution" in caplog.text
        assert "This process always fails" in caplog.text

        # Pipeline should continue: 5 * 2 = 10 (failing skipped) * 3 = 30
        actual_state = result_states["actual"]
        result_device = actual_state.get_device("test")
        assert result_device.properties["value"] == 30

    def test_multiple_failing_children(self, caplog):
        """Test pipeline continues when multiple children fail."""
        working1 = MultiplyProcess(name="working1", factor=2.0)
        failing1 = FailingProcess(name="failing1")
        failing2 = FailingProcess(name="failing2")
        working2 = MultiplyProcess(name="working2", factor=3.0)

        parent = SimpleProcess(name="parent", children=[working1, failing1, failing2, working2])

        initial_device = Device(name="test", properties={"value": 5})
        initial_state = State(devices={"test": initial_device})
        states = {"actual": initial_state}

        with caplog.at_level(logging.ERROR):
            result_states = parent.execute(states)

        # Should have error logs for both failing children
        assert "Process failing1 failed during execution" in caplog.text
        assert "Process failing2 failed during execution" in caplog.text

        # Pipeline should still work: 5 * 2 = 10, skip fails, * 3 = 30
        actual_state = result_states["actual"]
        result_device = actual_state.get_device("test")
        assert result_device.properties["value"] == 30


class TestEnvironmentController:
    """Test Environment and Controller abstract classes."""

    def test_environment_creation(self):
        """Test creating a concrete Environment."""
        env = TestEnvironment(name="test_env")

        assert isinstance(env, Environment)
        assert isinstance(env, Process)
        assert env.name == "test_env"

    def test_controller_creation(self):
        """Test creating a concrete Controller."""
        ctrl = TestController(name="test_ctrl")

        assert isinstance(ctrl, Controller)
        assert isinstance(ctrl, Process)
        assert ctrl.name == "test_ctrl"

    def test_environment_execution(self):
        """Test Environment execution behavior."""
        env = TestEnvironment(name="test_env")

        states = {"actual": State()}
        result_states = env.execute(states)

        # Should have added sensor
        actual_state = result_states["actual"]
        assert actual_state.has_device("env_sensor")

        sensor = actual_state.get_device("env_sensor")
        assert isinstance(sensor, Sensor)
        assert sensor.properties["value"] == 25.0

    def test_controller_execution(self):
        """Test Controller execution behavior."""
        ctrl = TestController(name="test_ctrl")

        states = {"actual": State()}
        result_states = ctrl.execute(states)

        # Should have added actuator
        actual_state = result_states["actual"]
        assert actual_state.has_device("ctrl_actuator")

        actuator = actual_state.get_device("ctrl_actuator")
        assert isinstance(actuator, Actuator)
        assert actuator.properties["value"] == 128

    def test_environment_controller_cannot_be_instantiated_directly(self):
        """Test that Environment and Controller are abstract."""
        with pytest.raises(TypeError):
            Environment(name="test")

        with pytest.raises(TypeError):
            Controller(name="test")


class TestProcessIntegration:
    """Integration tests combining multiple process types."""

    def test_environment_controller_pipeline(self):
        """Test a realistic pipeline with Environment and Controller."""
        env = TestEnvironment(name="environment")
        ctrl = TestController(name="controller")

        # Create system with environment and controller
        # When a process has children, it executes the children pipeline, not its own _process
        system = SimpleProcess(name="system", children=[env, ctrl])

        states = {"actual": State()}
        result_states = system.execute(states)

        actual_state = result_states["actual"]

        # Should have devices from environment and controller
        assert actual_state.has_device("env_sensor")  # From environment
        assert actual_state.has_device("ctrl_actuator")  # From controller
        # Should NOT have test_device because system has children (executes pipeline, not _process)
        assert not actual_state.has_device("test_device")

    def test_realistic_control_loop(self):
        """Test a realistic control loop pipeline."""
        env = TestEnvironment(name="environment")
        ctrl = TestController(name="controller")

        # Parent process just manages pipeline, doesn't execute its own logic
        parent = SimpleProcess(name="system", children=[env, ctrl])

        states = {"actual": State()}
        result_states = parent.execute(states)

        actual_state = result_states["actual"]

        # Should have devices from environment and controller
        assert actual_state.has_device("env_sensor")  # From environment
        assert actual_state.has_device("ctrl_actuator")  # From controller
        # Should NOT have test_device because parent has children
