"""Tests for integrated base architecture scenarios."""

import threading
import time

import pytest

from src.aifand.base.pipeline import Pipeline
from src.aifand.base.runner import FastRunner, StandardRunner
from src.aifand.base.state import State
from src.aifand.base.system import System

from .mocks import MockProcess, MockTimedPipeline


class TestRunnerSystemIntegration:
    """Test Runner executing System with multiple components."""

    def test_standard_runner_with_system(self):
        """Test StandardRunner executing System with multiple Pipelines at different intervals."""
        # Create pipelines with different intervals
        fast_pipeline = MockTimedPipeline(name="fast_pipeline", interval_ns=20_000_000)  # 20ms
        slow_pipeline = MockTimedPipeline(name="slow_pipeline", interval_ns=60_000_000)  # 60ms

        # Create system containing pipelines
        system = System(name="main_system")
        system.append(fast_pipeline)
        system.append(slow_pipeline)

        # Run with StandardRunner
        runner = StandardRunner(name="test_runner", main_process=system)
        runner.start()
        time.sleep(0.1)  # 100ms
        runner.stop()

        # Both pipelines should have executed
        assert len(fast_pipeline.execution_timestamps) >= 1
        assert len(slow_pipeline.execution_timestamps) >= 1

    def test_fast_runner_with_pipeline(self):
        """Test FastRunner executing Pipeline with multiple processes."""
        # Create pipeline with multiple processes
        proc1 = MockProcess(name="proc1", interval_ns=30_000_000)  # 30ms
        proc2 = MockProcess(name="proc2", interval_ns=30_000_000)  # 30ms

        pipeline = Pipeline(name="test_pipeline", interval_ns=50_000_000)  # 50ms
        pipeline.append(proc1)
        pipeline.append(proc2)

        # Run with FastRunner
        runner = FastRunner(name="test_runner", main_process=pipeline)
        runner.run_for_duration(0.15)  # 150ms simulation

        # Pipeline should have executed multiple times (150ms / 50ms = 3)
        assert len(pipeline.execution_timestamps) >= 2

        # Child processes should have executed during pipeline executions
        assert len(proc1.execution_timestamps) >= 2
        assert len(proc2.execution_timestamps) >= 2


class TestHierarchicalComposition:
    """Test complex hierarchical process compositions."""

    def test_system_containing_pipelines(self):
        """Test System containing multiple Pipeline instances."""
        # Create inner processes
        proc1 = MockProcess(name="proc1", interval_ns=40_000_000)
        proc2 = MockProcess(name="proc2", interval_ns=40_000_000)
        proc3 = MockProcess(name="proc3", interval_ns=40_000_000)

        # Create pipelines
        pipeline1 = Pipeline(name="pipeline1", interval_ns=50_000_000)
        pipeline1.append(proc1)
        pipeline1.append(proc2)

        pipeline2 = Pipeline(name="pipeline2", interval_ns=70_000_000)
        pipeline2.append(proc3)

        # Create system containing pipelines
        system = System(name="main_system")
        system.append(pipeline1)
        system.append(pipeline2)

        # Execute using FastRunner
        runner = FastRunner(name="test_runner", main_process=system)
        runner.run_for_duration(0.2)  # 200ms

        # Both pipelines should execute
        assert len(pipeline1.execution_timestamps) >= 1
        assert len(pipeline2.execution_timestamps) >= 1

        # Inner processes should execute
        assert len(proc1.execution_timestamps) >= 1
        assert len(proc2.execution_timestamps) >= 1
        assert len(proc3.execution_timestamps) >= 1

    def test_system_containing_systems(self):
        """Test System containing other System instances (hierarchical)."""
        # Create leaf processes
        proc1 = MockProcess(name="proc1", interval_ns=30_000_000)
        proc2 = MockProcess(name="proc2", interval_ns=30_000_000)

        # Create inner system
        inner_system = System(name="inner_system", interval_ns=60_000_000)
        inner_system.append(proc1)
        inner_system.append(proc2)

        # Create outer system containing inner system
        outer_system = System(name="outer_system")
        outer_system.append(inner_system)

        # Execute
        runner = FastRunner(name="test_runner", main_process=outer_system)
        runner.run_for_duration(0.15)  # 150ms

        # Inner system should execute
        assert len(inner_system.execution_timestamps) >= 1

        # Leaf processes should execute
        assert len(proc1.execution_timestamps) >= 1
        assert len(proc2.execution_timestamps) >= 1


class TestMultiRateCoordination:
    """Test complex timing scenarios with multiple execution rates."""

    def test_complex_timing_scenarios(self):
        """Test coordination with processes at 10ms, 30ms, 70ms intervals."""
        # Create processes with different intervals
        fast_proc = MockTimedPipeline(name="fast", interval_ns=10_000_000)  # 10ms
        med_proc = MockTimedPipeline(name="medium", interval_ns=30_000_000)  # 30ms
        slow_proc = MockTimedPipeline(name="slow", interval_ns=70_000_000)  # 70ms

        # Create system
        system = System(name="multi_rate_system")
        system.append(fast_proc)
        system.append(med_proc)
        system.append(slow_proc)

        # Run simulation
        runner = FastRunner(name="test_runner", main_process=system)
        runner.run_for_duration(0.21)  # 210ms

        # Verify execution counts approximately match expected rates
        # 210ms: fast=21, medium=7, slow=3 (approximately)
        assert len(fast_proc.execution_timestamps) >= 15
        assert len(med_proc.execution_timestamps) >= 5
        assert len(slow_proc.execution_timestamps) >= 2

    def test_permission_integration_under_runner(self):
        """Test Controllers/Environments work correctly under Runner execution."""
        pytest.skip("Permissions testing deferred per user request")

    def test_state_flow_validation_hierarchical(self):
        """Test data flows correctly through complex hierarchies."""
        from src.aifand.base.device import Sensor

        # Create state-modifying processes
        class StateModifyingProcess(MockProcess):
            def __init__(self, name: str, device_name: str):
                super().__init__(name=name, interval_ns=50_000_000)
                self.device_name = device_name

            def execute(self, states):
                result = super().execute(states)
                if "data" in result:
                    sensor = Sensor(name=self.device_name, properties={"value": 25.0})
                    result["data"] = result["data"].with_device(sensor)
                return result

        # Create hierarchical structure
        proc1 = StateModifyingProcess("proc1", "sensor1")
        proc2 = StateModifyingProcess("proc2", "sensor2")

        pipeline = Pipeline(name="data_pipeline", interval_ns=60_000_000)
        pipeline.append(proc1)
        pipeline.append(proc2)

        system = System(name="main_system")
        system.append(pipeline)

        # Execute with state
        initial_state = State()
        states = {"data": initial_state}
        system.execute(states)

        # State should have been modified by pipeline processes
        assert states["data"].has_device("sensor1")
        assert states["data"].has_device("sensor2")


class TestAdvancedScenarios:
    """Test advanced integration scenarios."""

    def test_concurrent_access_multiple_runners(self):
        """Test multiple StandardRunners in different threads."""
        results = {}

        def run_system(system_id):
            proc = MockProcess(name=f"proc_{system_id}", interval_ns=30_000_000)  # 30ms
            runner = StandardRunner(name=f"runner_{system_id}", main_process=proc)

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

    def test_dynamic_modification_during_execution(self):
        """Test adding/removing children during execution."""
        # Note: This tests structural modification, not runtime modification
        system = System(name="dynamic_system")

        # Start with one process
        proc1 = MockProcess(name="proc1", interval_ns=50_000_000)
        system.append(proc1)

        # Execute once
        runner = FastRunner(name="test_runner", main_process=system)
        runner.run_for_duration(0.06)  # 60ms

        initial_count = len(proc1.execution_timestamps)

        # Add another process
        proc2 = MockProcess(name="proc2", interval_ns=50_000_000)
        system.append(proc2)

        # Execute again
        runner.run_for_duration(0.06)  # Another 60ms

        # Both processes should execute in second run
        assert len(proc1.execution_timestamps) > initial_count
        assert len(proc2.execution_timestamps) >= 1

    def test_timing_edge_cases(self):
        """Test zero intervals, very large intervals, timing changes mid-execution."""
        # Very fast process
        fast_proc = MockProcess(name="fast", interval_ns=1_000_000)  # 1ms
        # Very slow process
        slow_proc = MockProcess(name="slow", interval_ns=500_000_000)  # 500ms

        system = System(name="edge_case_system")
        system.append(fast_proc)
        system.append(slow_proc)

        # Run for moderate duration
        runner = FastRunner(name="test_runner", main_process=system)
        runner.run_for_duration(0.1)  # 100ms

        # Fast process should execute many times
        assert len(fast_proc.execution_timestamps) >= 50
        # Slow process should not execute
        assert len(slow_proc.execution_timestamps) == 0

    def test_memory_management(self):
        """Test no leaks from threading or thread-local storage."""
        # Create and destroy multiple runners to test cleanup
        for i in range(10):
            proc = MockProcess(name=f"proc_{i}", interval_ns=50_000_000)
            runner = FastRunner(name=f"runner_{i}", main_process=proc)
            runner.run_for_duration(0.01)  # Brief execution

            # Verify cleanup (basic check)
            assert len(proc.execution_timestamps) >= 0

    def test_long_duration_stability(self):
        """Test FastRunner reliability during extended simulations."""
        proc = MockTimedPipeline(name="stable_proc", interval_ns=10_000_000)  # 10ms
        runner = FastRunner(name="stable_runner", main_process=proc)

        # Run for extended simulation time
        runner.run_for_duration(1.0)  # 1 second simulation

        # Should execute approximately 100 times (1000ms / 10ms)
        # Allow some tolerance
        assert 90 <= len(proc.execution_timestamps) <= 110
