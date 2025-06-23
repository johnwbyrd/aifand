"""Timing stress tests for complex coordination scenarios.

These tests validate System coordination under mathematically challenging
timing scenarios using prime intervals, coprime relationships, and burst patterns.
Tests focus on observable behavior rather than implementation details.
"""

from src.aifand.base.runner import FastRunner
from src.aifand.base.system import System

from .mocks import MockTimedPipeline


class TestPrimeIntervalCoordination:
    """Test System coordination with prime number intervals."""

    def test_prime_interval_coordination(self):
        """Test coordination with prime intervals (7ms, 11ms, 13ms, 17ms)."""
        system = System(name="prime_test")

        # Create processes with prime intervals
        proc_7ms = MockTimedPipeline(name="proc_7ms", interval_ns=7_000_000)  # 7ms
        proc_11ms = MockTimedPipeline(name="proc_11ms", interval_ns=11_000_000)  # 11ms
        proc_13ms = MockTimedPipeline(name="proc_13ms", interval_ns=13_000_000)  # 13ms
        proc_17ms = MockTimedPipeline(name="proc_17ms", interval_ns=17_000_000)  # 17ms

        system.append(proc_7ms)
        system.append(proc_11ms)
        system.append(proc_13ms)
        system.append(proc_17ms)

        # Run for 1 second (1000ms) simulation time
        runner = FastRunner(name="stress_runner", main_process=system)
        runner.run_for_duration(1.0)

        # Calculate expected execution counts: duration / interval + 1 (for t=0)
        # 7ms:  1000ms / 7ms = 142.857... → 142 + 1 = 143
        # 11ms: 1000ms / 11ms = 90.909... → 90 + 1 = 91
        # 13ms: 1000ms / 13ms = 76.923... → 76 + 1 = 77
        # 17ms: 1000ms / 17ms = 58.823... → 58 + 1 = 59
        assert len(proc_7ms.execution_timestamps) == 143
        assert len(proc_11ms.execution_timestamps) == 91
        assert len(proc_13ms.execution_timestamps) == 77
        assert len(proc_17ms.execution_timestamps) == 59

    def test_coprime_intervals_pattern_verification(self):
        """Test coprime intervals create predictable interference patterns."""
        system = System(name="coprime_test")

        # Use 7ms and 11ms (coprime, LCM = 77ms)
        proc_7ms = MockTimedPipeline(name="proc_7ms", interval_ns=7_000_000)
        proc_11ms = MockTimedPipeline(name="proc_11ms", interval_ns=11_000_000)

        system.append(proc_7ms)
        system.append(proc_11ms)

        # Run for 3 complete cycles: 3 * 77ms = 231ms
        runner = FastRunner(name="coprime_runner", main_process=system)
        runner.run_for_duration(0.231)

        # In 231ms:
        # 7ms process: (231-1)/7 + 1 = 32.857.. -> 32 + 1 = 33 executions
        # 11ms process: (231-1)/11 + 1 = 20.909.. -> 20 + 1 = 21 executions
        assert len(proc_7ms.execution_timestamps) == 33
        assert len(proc_11ms.execution_timestamps) == 21

        # Verify timing patterns: first few executions should be at predictable times
        # 7ms: 0, 7, 14, 21, 28, 35, 42, 49, 56, 63, 70, 77, ...
        # 11ms: 0, 11, 22, 33, 44, 55, 66, 77, ...
        expected_7ms_times = [i * 7_000_000 for i in range(min(10, len(proc_7ms.execution_timestamps)))]
        expected_11ms_times = [i * 11_000_000 for i in range(min(10, len(proc_11ms.execution_timestamps)))]

        actual_7ms_times = proc_7ms.execution_timestamps[: len(expected_7ms_times)]
        actual_11ms_times = proc_11ms.execution_timestamps[: len(expected_11ms_times)]

        assert actual_7ms_times == expected_7ms_times
        assert actual_11ms_times == expected_11ms_times

    def test_extreme_interval_differences(self):
        """Test coordination with vastly different intervals (burst patterns)."""
        system = System(name="burst_test")

        # Create processes with extreme interval differences
        fast_proc = MockTimedPipeline(name="fast", interval_ns=1_000_000)  # 1ms - very fast
        medium_proc = MockTimedPipeline(name="medium", interval_ns=100_000_000)  # 100ms - medium
        slow_proc = MockTimedPipeline(name="slow", interval_ns=1_000_000_000)  # 1000ms - very slow

        system.append(fast_proc)
        system.append(medium_proc)
        system.append(slow_proc)

        # Run for 1.5 seconds to see slow process execute twice
        runner = FastRunner(name="burst_runner", main_process=system)
        runner.run_for_duration(1.5)

        # Calculate expected execution counts:
        # Fast (1ms): (1500-1)/1 + 1 = 1499 + 1 = 1500
        # Medium (100ms): (1500-1)/100 + 1 = 14 + 1 = 15
        # Slow (1000ms): (1500-1)/1000 + 1 = 1 + 1 = 2
        assert len(fast_proc.execution_timestamps) == 1500
        assert len(medium_proc.execution_timestamps) == 15
        assert len(slow_proc.execution_timestamps) == 2

        # Verify no process was starved - all should execute
        assert len(fast_proc.execution_timestamps) > 0
        assert len(medium_proc.execution_timestamps) > 0
        assert len(slow_proc.execution_timestamps) > 0


class TestComplexTimingScenarios:
    """Test complex timing coordination scenarios."""

    def test_many_prime_intervals(self):
        """Test coordination with many different prime intervals."""
        system = System(name="many_primes_test")

        # Create processes with various prime intervals
        primes_ms = [3, 5, 7, 11, 13, 17, 19, 23, 29, 31]  # First 10 primes
        processes = []

        for prime in primes_ms:
            proc = MockTimedPipeline(
                name=f"proc_{prime}ms",
                interval_ns=prime * 1_000_000,  # Convert to nanoseconds
            )
            processes.append(proc)
            system.append(proc)

        # Run for 1 second
        runner = FastRunner(name="many_primes_runner", main_process=system)
        runner.run_for_duration(1.0)

        # Verify each process executed the expected number of times
        for i, prime in enumerate(primes_ms):
            expected_count = (1000 - 1) // prime + 1  # Correct calculation for FastRunner timing
            actual_count = len(processes[i].execution_timestamps)
            assert actual_count == expected_count, f"Process {prime}ms: expected {expected_count}, got {actual_count}"

    def test_fibonacci_intervals(self):
        """Test coordination with Fibonacci sequence intervals."""
        system = System(name="fibonacci_test")

        # Use Fibonacci numbers as intervals: 1, 2, 3, 5, 8, 13, 21, 34, 55ms
        fibonacci_ms = [1, 2, 3, 5, 8, 13, 21, 34, 55]
        processes = []

        for fib in fibonacci_ms:
            proc = MockTimedPipeline(name=f"fib_{fib}ms", interval_ns=fib * 1_000_000)
            processes.append(proc)
            system.append(proc)

        # Run for 500ms (shorter duration due to very fast 1ms process)
        runner = FastRunner(name="fibonacci_runner", main_process=system)
        runner.run_for_duration(0.5)

        # Verify execution counts for each Fibonacci interval
        for i, fib in enumerate(fibonacci_ms):
            expected_count = (500 - 1) // fib + 1  # Correct calculation for FastRunner timing
            actual_count = len(processes[i].execution_timestamps)
            assert actual_count == expected_count, f"Fibonacci {fib}ms: expected {expected_count}, got {actual_count}"

    def test_power_of_two_intervals(self):
        """Test coordination with power-of-2 intervals."""
        system = System(name="power2_test")

        # Use powers of 2: 1, 2, 4, 8, 16, 32, 64, 128ms
        powers_ms = [2**i for i in range(8)]  # [1, 2, 4, 8, 16, 32, 64, 128]
        processes = []

        for power in powers_ms:
            proc = MockTimedPipeline(name=f"pow2_{power}ms", interval_ns=power * 1_000_000)
            processes.append(proc)
            system.append(proc)

        # Run for 1 second
        runner = FastRunner(name="power2_runner", main_process=system)
        runner.run_for_duration(1.0)

        # Verify execution counts - powers of 2 should have clean division relationships
        for i, power in enumerate(powers_ms):
            expected_count = (1000 - 1) // power + 1  # Correct calculation for FastRunner timing
            actual_count = len(processes[i].execution_timestamps)
            assert actual_count == expected_count, f"Power2 {power}ms: expected {expected_count}, got {actual_count}"

        # Verify mathematical relationships between power-of-2 intervals
        # Each power should execute exactly half as often as the previous
        for i in range(1, len(processes)):
            current_executions = len(processes[i].execution_timestamps)
            previous_executions = len(processes[i - 1].execution_timestamps)

            # Allow for rounding differences, but should be approximately 2:1 ratio
            expected_ratio = previous_executions / current_executions
            assert 1.9 <= expected_ratio <= 2.1, (
                f"Ratio between {powers_ms[i - 1]}ms and {powers_ms[i]}ms should be ~2:1"
            )
