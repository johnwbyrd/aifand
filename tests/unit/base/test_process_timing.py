"""Tests for Process timing infrastructure."""

import time
from threading import Thread
from typing import Dict, List

import pytest
from pydantic import Field

from src.aifand.base.device import Device
from src.aifand.base.process import Process
from src.aifand.base.state import State

from .mocks import FailingMixin


# Test classes for timing infrastructure testing
class MockTimedProcess(Process):
    """Simple concrete Process implementation for timing tests."""

    call_log: List[str] = Field(default_factory=list, description="Log of method calls for verification")

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Test implementation that logs execution."""
        self.call_log.append(f"_process:{self.execution_count}")
        if "actual" in states:
            test_device = Device(name="test_device", properties={"value": 42, "execution": self.execution_count})
            states["actual"] = states["actual"].with_device(test_device)
        return states

    def _calculate_next_tick_time(self) -> int:
        """Simple fixed interval timing."""
        self.call_log.append(f"_calculate_next_tick_time:{self.execution_count}")
        return self.start_time + (self.execution_count * self.interval_ns)

    def _select_processes_to_execute(self) -> List[Process]:
        """Return all children for unified timing."""
        self.call_log.append(f"_select_processes_to_execute:{self.execution_count}")
        return self.children

    def _before_process(self) -> None:
        """Log before process hook."""
        self.call_log.append(f"_before_process:{self.execution_count}")

    def _after_process(self) -> None:
        """Log after process hook."""
        self.call_log.append(f"_after_process:{self.execution_count}")

    def _before_child_process(self, processes: List[Process]) -> None:
        """Log before child process hook."""
        self.call_log.append(f"_before_child_process:{len(processes)}:{self.execution_count}")

    def _after_child_process(self, processes: List[Process]) -> None:
        """Log after child process hook."""
        self.call_log.append(f"_after_child_process:{len(processes)}:{self.execution_count}")


class FailingTimedProcess(FailingMixin, Process):
    """Process that fails during timing execution."""

    def _calculate_next_tick_time(self) -> int:
        """Simple fixed interval timing."""
        return self.start_time + (self.execution_count * self.interval_ns)

    def _select_processes_to_execute(self) -> List[Process]:
        """Return empty list (no children) to test direct process execution."""
        return []


class VariableTimingProcess(Process):
    """Process with changing timing requirements."""

    intervals: List[int] = Field(
        default_factory=lambda: [50_000_000, 100_000_000, 200_000_000],
        description="Different intervals to cycle through (nanoseconds)",
    )

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Simple state passthrough."""
        return states

    def _calculate_next_tick_time(self) -> int:
        """Variable interval timing based on execution count."""
        # Cycle through different intervals
        interval = self.intervals[self.execution_count % len(self.intervals)]
        return self.start_time + (self.execution_count * interval)

    def _select_processes_to_execute(self) -> List[Process]:
        """Return all children."""
        return self.children


class IncompleteMockProcess(Process):
    """Process that doesn't implement timing methods (for testing abstract enforcement)."""

    def _process(self, states: Dict[str, State]) -> Dict[str, State]:
        """Simple state passthrough."""
        return states


class TestProcessTimingAbstractMethods:
    """Test abstract timing method enforcement."""

    def test_incomplete_process_cannot_be_instantiated(self):
        """Test that Process without timing methods cannot be instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteMockProcess(name="incomplete")

    def test_process_base_class_cannot_be_instantiated(self):
        """Test that Process base class cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            Process(name="base")


class TestProcessTimingBasics:
    """Test basic timing infrastructure."""

    def test_timing_fields_initialization(self):
        """Test that timing fields are properly initialized."""
        process = MockTimedProcess(name="test")

        assert process.interval_ns == 100_000_000  # 100ms default
        assert process.start_time == 0
        assert process.execution_count == 0
        assert process.stop_requested is False

    def test_timing_fields_custom_values(self):
        """Test timing fields with custom values."""
        process = MockTimedProcess(
            name="test",
            interval_ns=50_000_000,  # 50ms
            start_time=1000,
            execution_count=5,
            stop_requested=True,
        )

        assert process.interval_ns == 50_000_000
        assert process.start_time == 1000
        assert process.execution_count == 5
        assert process.stop_requested is True

    def test_get_time_default_implementation(self):
        """Test that get_time() returns nanosecond timestamp."""
        process = MockTimedProcess(name="test")

        start_time = time.time_ns()
        process_time = process.get_time()
        end_time = time.time_ns()

        # Should be within reasonable range
        assert start_time <= process_time <= end_time
        assert isinstance(process_time, int)


class TestProcessTemplateMethodPattern:
    """Test the template method pattern in timing execution."""

    def test_start_stop_basic_functionality(self):
        """Test basic start/stop functionality."""
        process = MockTimedProcess(name="test", interval_ns=20_000_000)  # 20ms

        # Start in background thread
        def run_process():
            process.start()

        thread = Thread(target=run_process, daemon=True)
        thread.start()

        # Let it run briefly
        time.sleep(0.1)  # Should allow ~5 executions at 20ms intervals

        # Stop and wait
        process.stop()
        thread.join(timeout=1.0)

        # Should have executed multiple times
        assert process.execution_count >= 3
        assert process.stop_requested is True
        assert len(process.call_log) > 0

    def test_template_method_call_sequence(self):
        """Test that timing methods are called in correct sequence."""
        process = MockTimedProcess(name="test", interval_ns=10_000_000)  # 10ms for fast testing

        def run_process():
            process.start()

        thread = Thread(target=run_process, daemon=True)
        thread.start()

        # Let it run for one or two cycles
        time.sleep(0.05)
        process.stop()
        thread.join(timeout=1.0)

        # Verify call sequence includes expected pattern
        call_log = process.call_log
        assert len(call_log) > 0

        # Should see the template method pattern
        assert any("_calculate_next_tick_time" in call for call in call_log)
        assert any("_before_process" in call for call in call_log)
        assert any("_select_processes_to_execute" in call for call in call_log)
        assert any("_after_process" in call for call in call_log)

    def test_coordination_hooks_called_with_children(self):
        """Test coordination hooks are called when children exist."""
        parent = MockTimedProcess(name="parent", interval_ns=15_000_000)  # 15ms
        child = MockTimedProcess(name="child")

        parent.append_child(child)

        def run_process():
            parent.start()

        thread = Thread(target=run_process, daemon=True)
        thread.start()

        time.sleep(0.05)
        parent.stop()
        thread.join(timeout=1.0)

        # Should see child coordination hooks
        call_log = parent.call_log
        assert any("_before_child_process:1:" in call for call in call_log)  # 1 child
        assert any("_after_child_process:1:" in call for call in call_log)


class TestProcessTimingErrorHandling:
    """Test error handling in timing execution."""

    def test_execution_continues_on_process_failure(self, caplog):
        """Test that timing execution continues when processes fail."""
        import logging

        caplog.set_level(logging.ERROR)

        process = FailingTimedProcess(name="failing", interval_ns=10_000_000, fail_after=2)

        def run_process():
            process.start()

        thread = Thread(target=run_process, daemon=True)
        thread.start()

        # Let it run long enough for failures to occur
        time.sleep(0.08)
        process.stop()
        thread.join(timeout=1.0)

        # Should have continued executing despite failures
        assert process.execution_count > 3  # More than the fail_after threshold

        # Should have logged errors but continued
        assert "failed during timing execution" in caplog.text
        assert "Simulated failure" in caplog.text

    def test_stop_responsive_shutdown(self):
        """Test that stop() provides responsive shutdown."""
        process = MockTimedProcess(name="test", interval_ns=1_000_000_000)  # 1 second intervals

        def run_process():
            process.start()

        thread = Thread(target=run_process, daemon=True)
        thread.start()

        # Stop immediately and measure response time
        start_stop = time.time()
        process.stop()
        thread.join(timeout=1.0)
        end_stop = time.time()

        # Should stop within reasonable time (much less than 1 second interval)
        stop_duration = end_stop - start_stop
        assert stop_duration < 0.2  # Should be responsive despite long interval


class TestProcessTimingLifecycle:
    """Test start/stop lifecycle management."""

    def test_multiple_start_stop_cycles(self):
        """Test multiple start/stop cycles work correctly."""
        process = MockTimedProcess(name="test", interval_ns=15_000_000)  # 15ms

        # First cycle
        def run_process1():
            process.start()

        thread1 = Thread(target=run_process1, daemon=True)
        thread1.start()

        time.sleep(0.06)  # Longer duration for more executions
        first_count = process.execution_count
        process.stop()
        thread1.join(timeout=1.0)

        # Second cycle - execution count resets on new start()
        def run_process2():
            process.start()

        thread2 = Thread(target=run_process2, daemon=True)
        thread2.start()

        time.sleep(0.06)  # Longer duration for more executions
        second_count = process.execution_count
        process.stop()
        thread2.join(timeout=1.0)

        # Should have executed in both cycles
        assert first_count > 0
        assert second_count > 0  # Second cycle should also execute
        # Note: execution_count resets on each start(), which is correct behavior

    def test_timing_state_persistence(self):
        """Test that timing state persists between executions."""
        process = MockTimedProcess(name="test", interval_ns=15_000_000)  # 15ms

        # Initialize with some state
        process._current_states = {"actual": State()}

        def run_process():
            process.start()

        thread = Thread(target=run_process, daemon=True)
        thread.start()

        time.sleep(0.05)
        process.stop()
        thread.join(timeout=1.0)

        # Should have executed several times
        assert process.execution_count > 0

        # State should persist and be modified
        assert hasattr(process, "_current_states")
        assert "actual" in process._current_states

        # Should have device added by _process method (since no children)
        actual_state = process._current_states["actual"]
        assert actual_state.has_device("test_device")


class TestProcessTimingVariableIntervals:
    """Test processes with variable timing intervals."""

    def test_variable_timing_process(self):
        """Test process with changing interval requirements."""
        intervals = [30_000_000, 60_000_000, 90_000_000]  # 30ms, 60ms, 90ms
        process = VariableTimingProcess(name="variable", intervals=intervals)

        def run_process():
            process.start()

        thread = Thread(target=run_process, daemon=True)
        thread.start()

        time.sleep(0.2)  # Let it cycle through different intervals
        process.stop()
        thread.join(timeout=1.0)

        # Should have executed several times with different intervals
        assert process.execution_count >= 2
