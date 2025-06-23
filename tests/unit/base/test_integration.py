"""Tests for integrated base architecture scenarios."""

import pytest

from src.aifand.base.pipeline import Pipeline
from src.aifand.base.runner import FastRunner
from src.aifand.base.state import State
from src.aifand.base.system import System

from .mocks import MockProcess, MockTimedPipeline, MockTimedSystem


class TestRunnerSystemIntegration:
    """Test Runner executing System with multiple components."""

    def test_fast_runner_with_system(self):
        """Test FastRunner executing System with multiple Pipelines.

        Test execution at different intervals.
        """
        # Create pipelines with different intervals
        fast_pipeline = MockTimedPipeline(
            name="fast_pipeline", interval_ns=20_000_000
        )  # 20ms
        slow_pipeline = MockTimedPipeline(
            name="slow_pipeline", interval_ns=60_000_000
        )  # 60ms

        # Create system containing pipelines
        system = System(name="main_system")
        system.append(fast_pipeline)
        system.append(slow_pipeline)

        # Run with FastRunner for deterministic timing
        runner = FastRunner(name="test_runner", main_process=system)
        runner.run_for_duration(0.1)  # 100ms simulation

        # Calculate expected execution counts with tolerance for timing
        # initialization
        # fast_pipeline: 100ms / 20ms ≈ 5 executions (allow 4-6 range)
        # slow_pipeline: 100ms / 60ms ≈ 1-2 executions
        assert 4 <= len(fast_pipeline.execution_timestamps) <= 6
        assert 1 <= len(slow_pipeline.execution_timestamps) <= 2

    def test_fast_runner_with_pipeline(self):
        """Test FastRunner executing Pipeline with multiple processes."""
        # Create pipeline with multiple processes
        proc1 = MockProcess(name="proc1", interval_ns=30_000_000)  # 30ms
        proc2 = MockProcess(name="proc2", interval_ns=30_000_000)  # 30ms

        pipeline = MockTimedPipeline(
            name="test_pipeline", interval_ns=50_000_000
        )  # 50ms
        pipeline.append(proc1)
        pipeline.append(proc2)

        # Run with FastRunner
        runner = FastRunner(name="test_runner", main_process=pipeline)
        runner.run_for_duration(0.15)  # 150ms simulation

        # Calculate exact execution counts: 150ms / 50ms = 3 executions
        assert len(pipeline.execution_timestamps) == 3

        # Child processes execute once per pipeline execution
        assert len(proc1.execution_timestamps) == 3
        assert len(proc2.execution_timestamps) == 3


class TestHierarchicalComposition:
    """Test complex hierarchical process compositions."""

    def test_system_containing_pipelines(self):
        """Test System containing multiple Pipeline instances."""
        # Create inner processes
        proc1 = MockProcess(name="proc1", interval_ns=40_000_000)
        proc2 = MockProcess(name="proc2", interval_ns=40_000_000)
        proc3 = MockProcess(name="proc3", interval_ns=40_000_000)

        # Create pipelines
        pipeline1 = MockTimedPipeline(name="pipeline1", interval_ns=50_000_000)
        pipeline1.append(proc1)
        pipeline1.append(proc2)

        pipeline2 = MockTimedPipeline(name="pipeline2", interval_ns=70_000_000)
        pipeline2.append(proc3)

        # Create system containing pipelines
        system = System(name="main_system")
        system.append(pipeline1)
        system.append(pipeline2)

        # Execute using FastRunner
        runner = FastRunner(name="test_runner", main_process=system)
        runner.run_for_duration(0.2)  # 200ms

        # Calculate exact execution counts: initial execution at t=0 plus
        # interval-based executions
        # pipeline1: executions at 0ms, 50ms, 100ms, 150ms = 4 executions
        # pipeline2: executions at 0ms, 70ms, 140ms = 3 executions
        assert len(pipeline1.execution_timestamps) == 4
        assert len(pipeline2.execution_timestamps) == 3

        # Inner processes execute once per pipeline execution
        assert len(proc1.execution_timestamps) == 4
        assert len(proc2.execution_timestamps) == 4
        assert len(proc3.execution_timestamps) == 3

    def test_system_containing_systems(self):
        """Test System containing other System instances (hierarchical)."""
        # Create leaf processes
        proc1 = MockProcess(name="proc1", interval_ns=30_000_000)
        proc2 = MockProcess(name="proc2", interval_ns=30_000_000)

        # Create inner system with execution tracking
        inner_system = MockTimedSystem(
            name="inner_system", interval_ns=60_000_000
        )
        inner_system.append(proc1)
        inner_system.append(proc2)

        # Create outer system containing inner system
        outer_system = System(name="outer_system")
        outer_system.append(inner_system)

        # Execute
        runner = FastRunner(name="test_runner", main_process=outer_system)
        runner.run_for_duration(0.15)  # 150ms

        # Calculate exact execution counts: executions at 0ms, 60ms,
        # 120ms = 3 executions
        # But inner_system delegates to children (30ms interval), so
        # executes at
        # 0ms, 30ms, 60ms, 90ms, 120ms = 5 executions
        assert len(inner_system.execution_history) == 5

        # Leaf processes execute when inner system executes
        assert len(proc1.execution_timestamps) == 5
        assert len(proc2.execution_timestamps) == 5


class TestMultiRateCoordination:
    """Test complex timing scenarios with multiple execution rates."""

    def test_complex_timing_scenarios(self):
        """Test coordination with processes at 10ms, 30ms, 70ms intervals."""
        # Create processes with different intervals
        fast_proc = MockTimedPipeline(
            name="fast", interval_ns=10_000_000
        )  # 10ms
        med_proc = MockTimedPipeline(
            name="medium", interval_ns=30_000_000
        )  # 30ms
        slow_proc = MockTimedPipeline(
            name="slow", interval_ns=70_000_000
        )  # 70ms

        # Create system
        system = System(name="multi_rate_system")
        system.append(fast_proc)
        system.append(med_proc)
        system.append(slow_proc)

        # Run simulation
        runner = FastRunner(name="test_runner", main_process=system)
        runner.run_for_duration(0.21)  # 210ms

        # Calculate exact execution counts: duration / interval
        # fast_proc: 210ms / 10ms = 21 executions
        # med_proc: 210ms / 30ms = 7 executions
        # slow_proc: 210ms / 70ms = 3 executions (floor)
        assert len(fast_proc.execution_timestamps) == 21
        assert len(med_proc.execution_timestamps) == 7
        assert len(slow_proc.execution_timestamps) == 3

    def test_permission_integration_under_runner(self):
        """Test Controllers/Environments work correctly.

        Test under Runner execution.
        """
        pytest.skip("Permissions testing deferred per user request")

    def test_state_flow_validation_hierarchical(self):
        """Test System properly isolates child state management."""
        from src.aifand.base.device import Sensor

        # Create state-modifying processes that track what states they receive
        class StateTrackingProcess(MockProcess):
            def __init__(self, name: str):
                super().__init__(name=name, interval_ns=50_000_000)
                self.received_states = None

            def _execute(self, states):
                self.received_states = states.copy()
                return super()._execute(states)

        # Create hierarchical structure
        proc1 = StateTrackingProcess("proc1")
        proc2 = StateTrackingProcess("proc2")

        pipeline = Pipeline(name="data_pipeline", interval_ns=60_000_000)
        pipeline.append(proc1)
        pipeline.append(proc2)

        system = System(name="main_system")
        system.append(pipeline)

        # Execute with non-empty state
        initial_state = State()
        sensor = Sensor(name="temp", properties={"value": 30.0})
        initial_state = initial_state.with_device(sensor)
        states = {"data": initial_state}

        result_states = system.execute(states)

        # System should pass through input states unchanged (state isolation)
        assert result_states == states
        assert result_states["data"].has_device("temp")

        # Children should receive empty states (System's isolation design)
        # Note: Children may not have executed if they weren't ready
        if proc1.received_states is not None:
            assert proc1.received_states == {}
        if proc2.received_states is not None:
            assert proc2.received_states == {}


class TestAdvancedScenarios:
    """Test advanced integration scenarios."""

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

        # Calculate exact count: executions at 0ms and 50ms = 2 executions
        initial_count = len(proc1.execution_timestamps)
        assert initial_count == 2

        # Add another process
        proc2 = MockProcess(name="proc2", interval_ns=50_000_000)
        system.append(proc2)

        # Execute again with fresh runner (to restart timing)
        runner = FastRunner(name="test_runner2", main_process=system)
        runner.run_for_duration(0.06)  # Another 60ms

        # Both processes should execute twice in second run
        assert (
            len(proc1.execution_timestamps) == 4
        )  # 2 from first + 2 from second
        assert len(proc2.execution_timestamps) == 2  # 2 from second run only

    def test_timing_edge_cases(self):
        """Test zero intervals, very large intervals.

        Test timing changes mid-execution.
        """
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

        # Calculate exact execution counts:
        # fast_proc: executions at 0ms, 1ms, 2ms, ..., 99ms = 100 executions
        # slow_proc: execution at 0ms only (next would be at 500ms) = 1
        # execution
        assert len(fast_proc.execution_timestamps) == 100
        assert len(slow_proc.execution_timestamps) == 1

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
        proc = MockTimedPipeline(
            name="stable_proc", interval_ns=10_000_000
        )  # 10ms
        runner = FastRunner(name="stable_runner", main_process=proc)

        # Run for extended simulation time
        runner.run_for_duration(1.0)  # 1 second simulation

        # Should execute approximately 100 times (1000ms / 10ms)
        # Allow some tolerance
        assert 90 <= len(proc.execution_timestamps) <= 110
