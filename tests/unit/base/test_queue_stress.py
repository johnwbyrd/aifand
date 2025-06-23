"""Queue stress tests for large-scale coordination scenarios.

These tests validate System coordination under high load with many
processes, simultaneous readiness, and various stress patterns. Tests
focus on correctness and performance under load without assuming
specific queue implementation.
"""

from src.aifand.base.runner import FastRunner
from src.aifand.base.system import System

from .mocks import MockTimedPipeline


class TestLargeScaleCoordination:
    """Test System coordination with many processes."""

    def test_fifty_process_coordination(self) -> None:
        """Test coordination with 50 processes of diverse intervals."""
        system = System(name="fifty_proc_test")
        processes = []

        # Create 50 processes with intervals from 10ms to 200ms
        for i in range(50):
            interval_ms = 10 + (i * 4)  # 10, 14, 18, 22, ... 206ms
            proc = MockTimedPipeline(
                name=f"proc_{i:02d}_{interval_ms}ms",
                interval_ns=interval_ms * 1_000_000,
            )
            processes.append(proc)
            system.append(proc)

        # Run for 1 second
        runner = FastRunner(name="fifty_runner", main_process=system)
        runner.run_for_duration(1.0)

        # Verify all processes executed at least once
        for i, proc in enumerate(processes):
            assert len(proc.execution_timestamps) > 0, (
                f"Process {i} never executed"
            )

        # Verify execution counts are reasonable for each interval
        for i, proc in enumerate(processes):
            interval_ms = 10 + (i * 4)
            expected_count = (
                1000 - 1
            ) // interval_ms + 1  # Correct calculation for FastRunner timing
            tolerance = 2  # Allow small tolerance for coordination overhead
            actual_count = len(proc.execution_timestamps)
            assert abs(actual_count - expected_count) <= tolerance, (
                f"Process {i} ({interval_ms}ms): expected ~{expected_count}, "
                f"got {actual_count}"
            )

        # Verify total execution count is reasonable
        total_executions = sum(
            len(proc.execution_timestamps) for proc in processes
        )
        # Rough estimate: should be reasonable for 50 processes over 1
        # second
        assert 500 <= total_executions <= 5000, (
            f"Total executions {total_executions} seems unreasonable"
        )

    def test_hundred_process_coordination(self) -> None:
        """Test coordination with 100 processes to stress the system."""
        system = System(name="hundred_proc_test")
        processes = []

        # Create 100 processes with intervals from 5ms to 500ms
        for i in range(100):
            interval_ms = 5 + (i * 5)  # 5, 10, 15, 20, ... 500ms
            proc = MockTimedPipeline(
                name=f"proc_{i:03d}_{interval_ms}ms",
                interval_ns=interval_ms * 1_000_000,
            )
            processes.append(proc)
            system.append(proc)

        # Run for 2 seconds to allow slower processes to execute
        runner = FastRunner(name="hundred_runner", main_process=system)
        runner.run_for_duration(2.0)

        # Verify all processes executed at least once
        for i, proc in enumerate(processes):
            assert len(proc.execution_timestamps) > 0, (
                f"Process {i} never executed"
            )

        # Verify no process was starved (got reasonable execution time)
        for i, proc in enumerate(processes):
            interval_ms = 5 + (i * 5)
            expected_count = (
                2000 - 1
            ) // interval_ms + 1  # Correct calculation for 2 seconds
            actual_count = len(proc.execution_timestamps)

            # Allow wider tolerance for 100 processes
            tolerance = max(
                2, expected_count // 10
            )  # At least 2, or 10% tolerance
            assert abs(actual_count - expected_count) <= tolerance, (
                f"Process {i} ({interval_ms}ms): expected ~{expected_count}, "
                f"got {actual_count}"
            )

    def test_mixed_load_patterns(self) -> None:
        """Test coordination with mixed fast/medium/slow processes."""
        system = System(name="mixed_load_test")

        # Create different categories of processes
        fast_processes = []  # 1-10ms intervals
        medium_processes = []  # 50-100ms intervals
        slow_processes = []  # 500-1000ms intervals

        # 20 fast processes
        for i in range(20):
            interval_ms = 1 + i  # 1, 2, 3, ... 20ms
            proc = MockTimedPipeline(
                name=f"fast_{i:02d}_{interval_ms}ms",
                interval_ns=interval_ms * 1_000_000,
            )
            fast_processes.append(proc)
            system.append(proc)

        # 10 medium processes
        for i in range(10):
            interval_ms = 50 + (i * 5)  # 50, 55, 60, ... 95ms
            proc = MockTimedPipeline(
                name=f"medium_{i:02d}_{interval_ms}ms",
                interval_ns=interval_ms * 1_000_000,
            )
            medium_processes.append(proc)
            system.append(proc)

        # 5 slow processes
        for i in range(5):
            interval_ms = 500 + (i * 100)  # 500, 600, 700, 800, 900ms
            proc = MockTimedPipeline(
                name=f"slow_{i:02d}_{interval_ms}ms",
                interval_ns=interval_ms * 1_000_000,
            )
            slow_processes.append(proc)
            system.append(proc)

        # Run for 3 seconds
        runner = FastRunner(name="mixed_runner", main_process=system)
        runner.run_for_duration(3.0)

        # Verify fast processes executed frequently
        for proc in fast_processes:
            assert len(proc.execution_timestamps) >= 100, (
                "Fast processes should execute frequently"
            )

        # Verify medium processes executed moderately
        for proc in medium_processes:
            assert 20 <= len(proc.execution_timestamps) <= 80, (
                "Medium processes should execute moderately"
            )

        # Verify slow processes executed but not frequently
        for proc in slow_processes:
            assert 1 <= len(proc.execution_timestamps) <= 10, (
                "Slow processes should execute infrequently"
            )


class TestSimultaneousReadiness:
    """Test System behavior with simultaneous process readiness.

    Tests when many processes are ready simultaneously.
    """

    def test_identical_intervals_simultaneous_execution(self) -> None:
        """Test many processes with identical intervals.

        Test executing simultaneously.
        """
        system = System(name="simultaneous_test")
        processes = []

        # Create 30 processes with identical 50ms intervals
        for i in range(30):
            proc = MockTimedPipeline(
                name=f"identical_{i:02d}",
                interval_ns=50_000_000,  # 50ms
            )
            processes.append(proc)
            system.append(proc)

        # Run for 500ms (10 intervals)
        runner = FastRunner(name="simultaneous_runner", main_process=system)
        runner.run_for_duration(0.5)

        # All processes should execute the same number of times
        expected_count = (
            500 - 1
        ) // 50 + 1  # Correct calculation for 500ms, 50ms interval
        for i, proc in enumerate(processes):
            actual_count = len(proc.execution_timestamps)
            assert actual_count == expected_count, (
                f"Process {i}: expected {expected_count}, got {actual_count}"
            )

        # All processes should execute at the same times
        reference_timestamps = processes[0].execution_timestamps
        for i, proc in enumerate(processes[1:], 1):
            assert proc.execution_timestamps == reference_timestamps, (
                f"Process {i} timestamps differ from reference"
            )

    def test_harmonic_intervals_coordination(self) -> None:
        """Test processes with harmonic intervals.

        Test multiples of base frequency.
        """
        system = System(name="harmonic_test")

        # Create processes with harmonic intervals: 10ms, 20ms, 40ms,
        # 80ms
        base_interval = 10_000_000  # 10ms in nanoseconds
        processes = []

        for multiplier in [1, 2, 4, 8]:
            proc = MockTimedPipeline(
                name=f"harmonic_{multiplier}x",
                interval_ns=base_interval * multiplier,
            )
            processes.append(proc)
            system.append(proc)

        # Run for 800ms (80 base intervals)
        runner = FastRunner(name="harmonic_runner", main_process=system)
        runner.run_for_duration(0.8)

        # Verify harmonic relationships
        # 10ms: (800-1)/10 + 1 = 79 + 1 = 80 executions
        # 20ms: (800-1)/20 + 1 = 39 + 1 = 40 executions
        # 40ms: (800-1)/40 + 1 = 19 + 1 = 20 executions
        # 80ms: (800-1)/80 + 1 = 9 + 1 = 10 executions
        expected_counts = [80, 40, 20, 10]

        for i, (proc, expected) in enumerate(
            zip(processes, expected_counts, strict=False)
        ):
            actual_count = len(proc.execution_timestamps)
            assert actual_count == expected, (
                f"Harmonic process {i}: expected {expected}, "
                f"got {actual_count}"
            )

    def test_burst_synchronization(self) -> None:
        """Test coordination when processes synchronize.

        Test at regular intervals.
        """
        system = System(name="burst_sync_test")

        # Create processes that synchronize every 60ms (LCM of 12, 15,
        # 20)
        intervals_ms = [12, 15, 20]  # LCM = 60ms
        processes = []

        for interval in intervals_ms:
            proc = MockTimedPipeline(
                name=f"sync_{interval}ms",
                interval_ns=interval * 1_000_000,
            )
            processes.append(proc)
            system.append(proc)

        # Run for 240ms (4 sync cycles of 60ms each)
        runner = FastRunner(name="sync_runner", main_process=system)
        runner.run_for_duration(0.24)

        # Verify execution counts
        # 12ms: (240-1)/12 + 1 = 19 + 1 = 20 executions
        # 15ms: (240-1)/15 + 1 = 15 + 1 = 16 executions
        # 20ms: (240-1)/20 + 1 = 11 + 1 = 12 executions
        expected_counts = [20, 16, 12]

        for i, (proc, expected) in enumerate(
            zip(processes, expected_counts, strict=False)
        ):
            actual_count = len(proc.execution_timestamps)
            assert actual_count == expected, (
                f"Sync process {intervals_ms[i]}ms: expected {expected}, "
                f"got {actual_count}"
            )

        # Verify synchronization points at 0, 60, 120, 180ms
        sync_points = [
            0,
            60_000_000,
            120_000_000,
            180_000_000,
        ]  # In nanoseconds

        for sync_point in sync_points:
            # Check that all processes have executions at or very close
            # to sync points
            for proc in processes:
                # Find closest execution to sync point
                closest_time = min(
                    proc.execution_timestamps,
                    key=lambda t: abs(t - sync_point),
                )
                # Should be exactly at sync point (within 1ms tolerance)
                assert abs(closest_time - sync_point) <= 1_000_000, (
                    f"Process {proc.name} not synchronized at {sync_point}ns"
                )


class TestStressEdgeCases:
    """Test edge cases and stress scenarios."""

    def test_very_fast_intervals(self) -> None:
        """Test system handles very fast intervals.

        Tests microsecond range intervals.
        """
        system = System(name="fast_intervals_test")
        processes = []

        # Create processes with very fast intervals: 100μs, 200μs,
        # 500μs, 1ms
        intervals_us = [100, 200, 500, 1000]  # microseconds

        for interval_us in intervals_us:
            proc = MockTimedPipeline(
                name=f"fast_{interval_us}us",
                interval_ns=interval_us * 1000,  # Convert to nanoseconds
            )
            processes.append(proc)
            system.append(proc)

        # Run for 10ms (short duration due to very fast intervals)
        runner = FastRunner(name="fast_runner", main_process=system)
        runner.run_for_duration(0.01)

        # Verify execution counts for very fast intervals
        # 100μs: (10000-1)/100 + 1 = 99 + 1 = 100 executions
        # 200μs: (10000-1)/200 + 1 = 49 + 1 = 50 executions
        # 500μs: (10000-1)/500 + 1 = 19 + 1 = 20 executions
        # 1000μs: (10000-1)/1000 + 1 = 9 + 1 = 10 executions
        expected_counts = [100, 50, 20, 10]

        for i, (proc, expected) in enumerate(
            zip(processes, expected_counts, strict=False)
        ):
            actual_count = len(proc.execution_timestamps)
            assert actual_count == expected, (
                f"Fast process {intervals_us[i]}μs: expected {expected}, "
                f"got {actual_count}"
            )

    def test_irregular_intervals(self) -> None:
        """Test coordination with irregular, non-round intervals."""
        system = System(name="irregular_test")

        # Create processes with irregular intervals
        irregular_intervals_ms = [
            7.3,
            13.7,
            23.1,
            41.9,
            67.2,
        ]  # Non-round numbers
        processes = []

        for interval_ms in irregular_intervals_ms:
            proc = MockTimedPipeline(
                name=f"irregular_{interval_ms}ms",
                interval_ns=int(
                    interval_ms * 1_000_000
                ),  # Convert to nanoseconds
            )
            processes.append(proc)
            system.append(proc)

        # Run for 1 second
        runner = FastRunner(name="irregular_runner", main_process=system)
        runner.run_for_duration(1.0)

        # Verify execution counts for irregular intervals
        for proc, interval_ms in zip(
            processes, irregular_intervals_ms, strict=False
        ):
            duration_ns = 1000 * 1_000_000  # 1000ms in nanoseconds
            interval_ns = int(
                interval_ms * 1_000_000
            )  # Convert to nanoseconds
            expected_count = (
                duration_ns - 1
            ) // interval_ns + 1  # Correct calculation
            actual_count = len(proc.execution_timestamps)

            # Allow tolerance for irregular intervals and floating point
            # precision
            tolerance = max(
                2, expected_count // 5
            )  # At least 2, or 20% tolerance
            assert abs(actual_count - expected_count) <= tolerance, (
                f"Irregular process {interval_ms}ms: expected "
                f"~{expected_count}, got {actual_count}"
            )
