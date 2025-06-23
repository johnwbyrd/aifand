"""Tests for the Pipeline class."""

import time
from threading import Thread
from typing import Dict

from src.aifand.base.device import Actuator, Sensor
from src.aifand.base.pipeline import Pipeline
from src.aifand.base.process import Environment
from src.aifand.base.state import State

from .mocks import CountingMixin, FailingMixin, MockController, MockEnvironment


# Test implementations for Pipeline testing
class TestEnvironment(CountingMixin, MockEnvironment):
    """Test environment that adds sensor readings."""

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Add sensor reading with incrementing counter."""
        # Call parent to increment counter
        states = super()._process(states)

        if "actual" in states:
            sensor = Sensor(
                name="temp_sensor",
                properties={
                    "value": 25.0 + self.counter,  # Temperature rises each cycle
                    "unit": "°C",
                    "execution": self.counter,
                },
            )
            states["actual"] = states["actual"].with_device(sensor)
        else:
            # Create actual state if it doesn't exist
            sensor = Sensor(
                name="temp_sensor", properties={"value": 25.0 + self.counter, "unit": "°C", "execution": self.counter}
            )
            states["actual"] = State(devices={"temp_sensor": sensor})

        return states


class TestController(CountingMixin, MockController):
    """Test controller that adds actuator settings."""

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Add actuator setting based on sensor reading."""
        # Call parent to increment counter
        states = super()._process(states)

        if "actual" in states:
            # Read temperature from sensor
            temp_sensor = states["actual"].get_device("temp_sensor")
            temp_value = temp_sensor.properties["value"] if temp_sensor else 25.0

            # Set fan speed based on temperature
            fan_speed = min(255, max(50, int((temp_value - 20) * 10)))

            actuator = Actuator(
                name="fan_control", properties={"value": fan_speed, "unit": "PWM", "execution": self.counter}
            )
            states["actual"] = states["actual"].with_device(actuator)

        return states


class FailingController(FailingMixin, MockController):
    """Controller that fails after a certain number of executions."""

    pass


class TestPipelineBasics:
    """Test basic Pipeline functionality."""

    def test_pipeline_creation(self):
        """Test creating a Pipeline."""
        pipeline = Pipeline(name="test_pipeline")

        assert pipeline.name == "test_pipeline"
        assert pipeline.states == {}
        assert pipeline.interval_ns == 100_000_000  # 100ms in nanoseconds
        assert pipeline.children == []
        assert not pipeline.stop_requested

    def test_pipeline_with_custom_interval(self):
        """Test creating Pipeline with custom timing interval."""
        pipeline = Pipeline(name="fast_pipeline", interval_ns=50_000_000)  # 50ms

        assert pipeline.interval_ns == 50_000_000

    def test_pipeline_with_initial_states(self):
        """Test creating Pipeline with initial states."""
        initial_state = State(devices={"test": Sensor(name="test", properties={"value": 10})})
        pipeline = Pipeline(name="test_pipeline", states={"actual": initial_state})

        assert "actual" in pipeline.states
        assert pipeline.states["actual"].has_device("test")

    def test_pipeline_inheritance(self):
        """Test that Pipeline properly inherits from Process."""
        pipeline = Pipeline(name="test")

        assert hasattr(pipeline, "execute")
        assert hasattr(pipeline, "append_child")
        assert hasattr(pipeline, "get_logger")


class TestPipelineConfiguration:
    """Test Pipeline configuration methods."""

    def test_set_environment(self):
        """Test setting Environment in pipeline."""
        pipeline = Pipeline(name="test_pipeline")
        env = TestEnvironment(name="test_env")

        pipeline.set_environment(env)

        assert len(pipeline.children) == 1
        assert pipeline.children[0] == env
        assert isinstance(pipeline.children[0], Environment)

    def test_set_environment_replaces_existing(self):
        """Test that set_environment replaces existing Environment."""
        pipeline = Pipeline(name="test_pipeline")
        env1 = MockEnvironment(name="env1")
        env2 = MockEnvironment(name="env2")
        ctrl = TestController(name="ctrl")

        # Add first environment and controller
        pipeline.set_environment(env1)
        pipeline.add_controller(ctrl)

        # Replace environment
        pipeline.set_environment(env2)

        assert len(pipeline.children) == 2
        assert pipeline.children[0] == env2  # New environment first
        assert pipeline.children[1] == ctrl  # Controller preserved

    def test_add_controller(self):
        """Test adding Controllers to pipeline."""
        pipeline = Pipeline(name="test_pipeline")
        env = TestEnvironment(name="env")
        ctrl1 = TestController(name="ctrl1")
        ctrl2 = TestController(name="ctrl2")

        pipeline.set_environment(env)
        pipeline.add_controller(ctrl1)
        pipeline.add_controller(ctrl2)

        assert len(pipeline.children) == 3
        assert pipeline.children[0] == env  # Environment first
        assert pipeline.children[1] == ctrl1  # Controllers in order
        assert pipeline.children[2] == ctrl2

    def test_add_controller_order(self):
        """Test that Controllers are added in order after Environment."""
        pipeline = Pipeline(name="test_pipeline")
        ctrl1 = TestController(name="ctrl1")
        ctrl2 = TestController(name="ctrl2")
        env = TestEnvironment(name="env")

        # Add controllers first, then environment
        pipeline.add_controller(ctrl1)
        pipeline.add_controller(ctrl2)
        pipeline.set_environment(env)

        assert len(pipeline.children) == 3
        assert pipeline.children[0] == env  # Environment moves to first
        assert pipeline.children[1] == ctrl1  # Controllers maintain order
        assert pipeline.children[2] == ctrl2


class TestPipelineExecution:
    """Test Pipeline execution as a Process."""

    def test_execute_with_no_children(self):
        """Test Pipeline execute() when no children configured."""
        pipeline = Pipeline(name="empty_pipeline")

        initial_states = {"actual": State()}
        result_states = pipeline.execute(initial_states)

        # Should return states unchanged (passthrough)
        assert result_states == initial_states

    def test_execute_with_environment_and_controller(self):
        """Test Pipeline execute() with Environment and Controller."""
        pipeline = Pipeline(name="test_pipeline")
        env = TestEnvironment(name="env")
        ctrl = TestController(name="ctrl")

        pipeline.set_environment(env)
        pipeline.add_controller(ctrl)

        initial_states = {"actual": State()}
        result_states = pipeline.execute(initial_states)

        # Should have devices from both Environment and Controller
        actual_state = result_states["actual"]
        assert actual_state.has_device("temp_sensor")  # From Environment
        assert actual_state.has_device("fan_control")  # From Controller

        # Verify execution counters
        assert env.counter == 1
        assert ctrl.counter == 1

    def test_execute_preserves_input_states(self):
        """Test that execute() doesn't modify input states."""
        pipeline = Pipeline(name="test_pipeline")
        env = TestEnvironment(name="env")

        pipeline.set_environment(env)

        initial_states = {"actual": State()}
        original_device_count = len(initial_states["actual"].devices)

        result_states = pipeline.execute(initial_states)

        # Input states should be unchanged
        assert len(initial_states["actual"].devices) == original_device_count

        # Result states should have new devices
        assert len(result_states["actual"].devices) > original_device_count

    def test_execute_state_flow(self):
        """Test that states flow correctly through pipeline stages."""
        pipeline = Pipeline(name="test_pipeline")
        env = TestEnvironment(name="env")
        ctrl = TestController(name="ctrl")

        pipeline.set_environment(env)
        pipeline.add_controller(ctrl)

        initial_states = {"actual": State()}
        result_states = pipeline.execute(initial_states)

        # Verify sensor from Environment
        temp_sensor = result_states["actual"].get_device("temp_sensor")
        assert temp_sensor is not None
        assert temp_sensor.properties["value"] == 26.0  # 25.0 + 1 execution

        # Verify actuator from Controller (based on sensor reading)
        fan_control = result_states["actual"].get_device("fan_control")
        assert fan_control is not None
        # Fan speed should be based on temperature: (26 - 20) * 10 = 60
        assert fan_control.properties["value"] == 60


class TestPipelineTimingExecution:
    """Test Pipeline timing-driven execution."""

    def test_start_stop_basic(self):
        """Test basic start/stop functionality."""
        pipeline = Pipeline(name="test_pipeline", interval_ns=50_000_000)  # 50ms
        env = TestEnvironment(name="env")

        pipeline.set_environment(env)
        pipeline.states = {"actual": State()}

        # Start in background thread
        def run_pipeline():
            pipeline.start()

        thread = Thread(target=run_pipeline, daemon=True)
        thread.start()

        # Let it run for a short time
        time.sleep(0.2)  # Should allow ~4 executions at 50ms intervals

        # Stop and wait
        pipeline.stop()
        thread.join(timeout=1.0)

        # Should have executed multiple times
        assert env.counter >= 3  # At least a few executions
        assert pipeline.stop_requested

    def test_timing_consistency(self):
        """Test that timing intervals are consistent."""
        pipeline = Pipeline(name="test_pipeline", interval_ns=25_000_000)  # 25ms = 40 Hz
        env = TestEnvironment(name="env")

        pipeline.set_environment(env)
        pipeline.states = {"actual": State()}

        start_time = time.time()

        def run_pipeline():
            pipeline.start()

        thread = Thread(target=run_pipeline, daemon=True)
        thread.start()

        # Run for specific duration
        time.sleep(0.15)  # Should allow ~6 executions at 25ms intervals
        pipeline.stop()
        thread.join(timeout=1.0)

        end_time = time.time()
        duration = end_time - start_time

        # Check execution rate is roughly correct
        expected_executions = duration / 0.025  # 25ms = 0.025s
        assert abs(env.counter - expected_executions) < 2  # Allow some tolerance

    def test_state_persistence_between_executions(self):
        """Test that states persist between timing executions."""
        pipeline = Pipeline(name="test_pipeline", interval_ns=30_000_000)  # 30ms
        env = TestEnvironment(name="env")

        pipeline.set_environment(env)
        pipeline.states = {"actual": State()}

        def run_pipeline():
            pipeline.start()

        thread = Thread(target=run_pipeline, daemon=True)
        thread.start()

        # Let it run
        time.sleep(0.1)
        pipeline.stop()
        thread.join(timeout=1.0)

        # Check that final states contain accumulated results
        assert "actual" in pipeline.states
        temp_sensor = pipeline.states["actual"].get_device("temp_sensor")
        assert temp_sensor is not None

        # Temperature should have increased over multiple executions
        assert temp_sensor.properties["value"] > 26.0  # Started at 25 + counter

    def test_error_handling_continues_execution(self, caplog):
        """Test that execution continues even when processes fail."""
        pipeline = Pipeline(name="test_pipeline", interval_ns=20_000_000)  # 20ms
        env = TestEnvironment(name="env")
        failing_ctrl = FailingController(name="failing", fail_after=2)

        pipeline.set_environment(env)
        pipeline.add_controller(failing_ctrl)
        pipeline.states = {"actual": State()}

        def run_pipeline():
            pipeline.start()

        thread = Thread(target=run_pipeline, daemon=True)
        thread.start()

        # Let it run long enough for failures to occur
        time.sleep(0.15)
        pipeline.stop()
        thread.join(timeout=1.0)

        # Should have continued executing despite failures
        assert env.counter > 3  # More than the fail_after threshold

        # Should have logged errors but continued
        assert "Process failing failed during execution" in caplog.text

    def test_stop_responsive_shutdown(self):
        """Test that stop() provides responsive shutdown."""
        pipeline = Pipeline(name="test_pipeline", interval_ns=1_000_000_000)  # 1 second intervals
        env = TestEnvironment(name="env")

        pipeline.set_environment(env)
        pipeline.states = {"actual": State()}

        def run_pipeline():
            pipeline.start()

        thread = Thread(target=run_pipeline, daemon=True)
        thread.start()

        # Stop immediately and measure response time
        start_stop = time.time()
        pipeline.stop()
        thread.join(timeout=1.0)
        end_stop = time.time()

        # Should stop within reasonable time (much less than 1 second interval)
        stop_duration = end_stop - start_stop
        assert stop_duration < 0.2  # Should be responsive despite long interval


class TestPipelineEdgeCases:
    """Test Pipeline edge cases and error conditions."""

    def test_empty_pipeline_timing_execution(self):
        """Test timing execution with no children configured."""
        pipeline = Pipeline(name="empty_pipeline", interval_ns=30_000_000)  # 30ms
        pipeline.states = {"actual": State()}

        def run_pipeline():
            pipeline.start()

        thread = Thread(target=run_pipeline, daemon=True)
        thread.start()

        time.sleep(0.1)
        pipeline.stop()
        thread.join(timeout=1.0)

        # Should have executed without errors
        assert pipeline.execution_count > 0

    def test_multiple_start_calls(self):
        """Test behavior when start() is called multiple times."""
        pipeline = Pipeline(name="test_pipeline", interval_ns=50_000_000)  # 50ms
        env = TestEnvironment(name="env")

        pipeline.set_environment(env)
        pipeline.states = {"actual": State()}

        # First start
        def run_pipeline1():
            pipeline.start()

        thread1 = Thread(target=run_pipeline1, daemon=True)
        thread1.start()

        time.sleep(0.05)
        first_count = env.counter

        # Stop first execution
        pipeline.stop()
        thread1.join(timeout=1.0)

        # Second start should reset and work normally
        def run_pipeline2():
            pipeline.start()

        thread2 = Thread(target=run_pipeline2, daemon=True)
        thread2.start()

        time.sleep(0.05)
        second_count = env.counter

        pipeline.stop()
        thread2.join(timeout=1.0)

        # Should have executed in both runs
        assert first_count > 0
        assert second_count > first_count

    def test_pipeline_process_mode_ignores_persistent_states(self):
        """Test that Process execution ignores persistent states."""
        pipeline = Pipeline(name="test_pipeline")
        env = TestEnvironment(name="env")

        pipeline.set_environment(env)

        # Set persistent states with existing data
        existing_sensor = Sensor(name="existing", properties={"value": 999})
        pipeline.states = {"actual": State(devices={"existing": existing_sensor})}

        # Execute as Process with different input states
        input_states = {"actual": State()}
        result_states = pipeline.execute(input_states)

        # Result should be based on input_states, not persistent states
        assert not result_states["actual"].has_device("existing")
        assert result_states["actual"].has_device("temp_sensor")  # From Environment

        # Persistent states should be unchanged
        assert pipeline.states["actual"].has_device("existing")
        assert not pipeline.states["actual"].has_device("temp_sensor")
