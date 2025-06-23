"""Tests for Runner hierarchy and autonomous execution."""

import threading
import time

import pytest

from src.aifand.base.pipeline import Pipeline
from src.aifand.base.runner import (
    FastRunner,
    StandardRunner,
    TimeSource,
)

from .mocks import MockProcess, MockTimedPipeline


class TestTimeSource:
    """Test TimeSource thread-local storage functionality."""

    def test_timesource_basic_operations(self):
        """Test TimeSource set/get/clear operations."""
        # Initially no runner
        assert TimeSource.get_current() is None

        # Create a mock runner for testing
        pipeline = Pipeline(name="test")
        runner = StandardRunner(name="test_runner", main_process=pipeline)

        # Set current runner
        TimeSource.set_current(runner)
        assert TimeSource.get_current() == runner

        # Clear current runner
        TimeSource.clear_current()
        assert TimeSource.get_current() is None

    def test_timesource_cleanup(self):
        """Test TimeSource cleanup functionality."""
        pipeline = Pipeline(name="test")
        runner = StandardRunner(name="test_runner", main_process=pipeline)

        TimeSource.set_current(runner)
        assert TimeSource.get_current() == runner

        # Clear should remove the reference
        TimeSource.clear_current()
        assert TimeSource.get_current() is None

        # Multiple clears should be safe
        TimeSource.clear_current()
        assert TimeSource.get_current() is None

    def test_timesource_thread_isolation(self):
        """Test TimeSource provides thread isolation for different runners."""
        results = {}

        def thread_function(thread_id):
            pipeline = Pipeline(name=f"test_{thread_id}")
            runner = StandardRunner(
                name=f"runner_{thread_id}", main_process=pipeline
            )
            TimeSource.set_current(runner)
            results[thread_id] = TimeSource.get_current()

        # Start two threads
        thread1 = threading.Thread(target=thread_function, args=(1,))
        thread2 = threading.Thread(target=thread_function, args=(2,))

        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # Each thread should have its own runner
        assert results[1].name == "runner_1"
        assert results[2].name == "runner_2"
        assert results[1] != results[2]


class TestStandardRunner:
    """Test StandardRunner real-time execution."""

    def test_standard_runner_lifecycle_management(self):
        """Test StandardRunner start/stop lifecycle with proper threading."""
        proc = MockProcess(name="test_proc", interval_ns=30_000_000)  # 30ms
        runner = StandardRunner(name="test_runner", main_process=proc)

        # Initially not running
        assert not runner.is_running()

        # Start runner
        runner.start()
        assert runner.is_running()

        # Let it run briefly
        time.sleep(0.05)  # 50ms

        # Stop runner
        runner.stop()
        assert not runner.is_running()

        # Process should have executed at least once
        assert len(proc.execution_timestamps) >= 1

    def test_standard_runner_timing_respect(self):
        """Test StandardRunner respects process timing preferences.

        Test with short intervals.
        """
        proc = MockTimedPipeline(
            name="test_proc", interval_ns=25_000_000
        )  # 25ms
        runner = StandardRunner(name="test_runner", main_process=proc)

        runner.start()
        time.sleep(0.08)  # 80ms - should allow ~3 executions
        runner.stop()

        # Should have executed multiple times
        assert len(proc.execution_timestamps) >= 2

        # Check intervals between executions are roughly correct
        if len(proc.execution_timestamps) >= 2:
            interval_ns = (
                proc.execution_timestamps[1] - proc.execution_timestamps[0]
            )
            # Allow some tolerance (±10ms)
            assert 15_000_000 <= interval_ns <= 35_000_000

    def test_standard_runner_error_resilience(self):
        """Test StandardRunner continues operation despite process failures."""
        from .mocks import FailingMixin

        class FailingProcess(FailingMixin, MockProcess):
            def __init__(self, name: str):
                super().__init__(
                    name=name, fail_after=2, interval_ns=20_000_000
                )  # 20ms, fail after 2 executions

        proc = FailingProcess("failing_proc")
        runner = StandardRunner(name="test_runner", main_process=proc)

        runner.start()
        time.sleep(0.09)  # 90ms - enough for several attempts
        runner.stop()

        # Should have attempted multiple executions despite failures
        assert proc.fail_count >= 3

    def test_standard_runner_graceful_shutdown(self):
        """Test StandardRunner graceful shutdown with proper thread cleanup."""
        proc = MockProcess(name="test_proc", interval_ns=50_000_000)  # 50ms
        runner = StandardRunner(name="test_runner", main_process=proc)

        runner.start()
        assert runner.is_running()

        # Stop should complete within reasonable time
        start_time = time.time()
        runner.stop()
        stop_time = time.time()

        assert not runner.is_running()
        assert stop_time - start_time < 1.0  # Should stop within 1 second


class TestFastRunner:
    """Test FastRunner simulation execution."""

    def test_fast_runner_simulation_time(self):
        """Test FastRunner maintains internal simulation time."""
        proc = MockProcess(name="test_proc", interval_ns=100_000_000)  # 100ms
        runner = FastRunner(name="test_runner", main_process=proc)

        # FastRunner should not support start/stop
        with pytest.raises(NotImplementedError):
            runner.start()

    def test_fast_runner_duration_execution(self):
        """Test FastRunner run_for_duration() method."""
        proc = MockTimedPipeline(
            name="test_proc", interval_ns=50_000_000
        )  # 50ms
        runner = FastRunner(name="test_runner", main_process=proc)

        # Run for 200ms of simulation time
        runner.run_for_duration(0.2)

        # Should have executed approximately 4 times (200ms / 50ms)
        # Allow tolerance due to timing initialization
        assert 3 <= len(proc.execution_timestamps) <= 5

    def test_fast_runner_deterministic_execution(self):
        """Test FastRunner provides deterministic execution.

        Test without real delays.
        """
        proc = MockTimedPipeline(
            name="test_proc", interval_ns=100_000_000
        )  # 100ms
        runner = FastRunner(name="test_runner", main_process=proc)

        # Multiple runs should be deterministic
        runner.run_for_duration(0.3)  # 300ms
        first_run_count = len(proc.execution_timestamps)

        # Reset and run again
        proc.execution_timestamps.clear()
        runner.run_for_duration(0.3)  # 300ms
        second_run_count = len(proc.execution_timestamps)

        # Should execute same number of times
        assert first_run_count == second_run_count

    def test_fast_runner_safety_limits(self):
        """Test FastRunner safety limits prevent infinite loops."""
        proc = MockProcess(
            name="test_proc", interval_ns=1_000_000
        )  # 1ms - very fast
        runner = FastRunner(
            name="test_runner",
            main_process=proc,
            max_duration_ns=100_000_000,
        )  # 100ms limit

        # Try to run for longer than limit
        runner.run_for_duration(1.0)  # 1 second requested

        # Should have stopped due to safety limit
        # Execution count depends on implementation but should be reasonable
        assert len(proc.execution_timestamps) < 1000  # Sanity check


class TestRunnerIntegration:
    """Test Runner integration with Process hierarchy."""

    def test_runner_time_source_integration(self):
        """Test Process.get_time() correctly uses runner time sources.

        Test runner-provided time sources.
        """
        proc = MockProcess(name="test_proc", interval_ns=50_000_000)
        runner = FastRunner(name="test_runner", main_process=proc)

        # Without runner, process uses system time
        system_time = proc.get_time()
        assert system_time > 0

        # During FastRunner execution, should use simulation time
        runner.run_for_duration(0.1)

        # Process should have used runner's time source during execution
        assert len(proc.execution_timestamps) >= 1

    def test_runner_process_initialization(self):
        """Test initialize_timing() propagates through entire process tree."""
        # Create nested structure: Pipeline containing processes
        inner_proc1 = MockProcess(name="inner1", interval_ns=50_000_000)
        inner_proc2 = MockProcess(name="inner2", interval_ns=50_000_000)

        pipeline = Pipeline(name="test_pipeline")
        pipeline.append(inner_proc1)
        pipeline.append(inner_proc2)

        runner = FastRunner(name="test_runner", main_process=pipeline)

        # Run simulation
        runner.run_for_duration(0.1)

        # All processes should have initialized timing with simulation time
        # (starting at 0)
        assert pipeline.start_time == 0
        assert inner_proc1.start_time == 0
        assert inner_proc2.start_time == 0

        # All processes should have executed at least once
        assert pipeline.execution_count >= 1
        assert inner_proc1.execution_count >= 1
        assert inner_proc2.execution_count >= 1

    def test_concurrent_access_multiple_runners(self):
        """Test multiple StandardRunners in different threads."""
        results = {}

        def run_system(system_id):
            proc = MockProcess(
                name=f"proc_{system_id}", interval_ns=30_000_000
            )  # 30ms
            runner = StandardRunner(
                name=f"runner_{system_id}", main_process=proc
            )

            runner.start()
            time.sleep(0.06)  # 60ms
            runner.stop()

            results[system_id] = len(proc.execution_timestamps)

        # Start multiple runners concurrently
        threads = []
        for i in range(3):
            thread = threading.Thread(target=run_system, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()

        # All should have executed
        for i in range(3):
            assert results[i] >= 1
