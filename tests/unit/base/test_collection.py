"""Tests for Collection protocol compliance and implementations."""

from src.aifand.base.collection import Collection
from src.aifand.base.pipeline import Pipeline
from src.aifand.base.system import System

from .mocks import MockProcess


class TestCollectionProtocol:
    """Test Collection protocol compliance for Pipeline and System."""

    def test_pipeline_implements_collection_protocol(self) -> None:
        """Test Pipeline correctly implements Collection interface."""
        pipeline = Pipeline(name="test_pipeline")

        # Verify Pipeline is a Collection
        assert isinstance(pipeline, Collection)

        # Test all Collection protocol methods exist
        assert hasattr(pipeline, "count")
        assert hasattr(pipeline, "append")
        assert hasattr(pipeline, "remove")
        assert hasattr(pipeline, "has")
        assert hasattr(pipeline, "get")

        # Test basic functionality
        assert pipeline.count() == 0
        assert not pipeline.has("nonexistent")
        assert pipeline.get("nonexistent") is None

    def test_system_implements_collection_protocol(self) -> None:
        """Test System correctly implements Collection interface."""
        system = System(name="test_system")

        # Verify System is a Collection
        assert isinstance(system, Collection)

        # Test all Collection protocol methods exist
        assert hasattr(system, "count")
        assert hasattr(system, "append")
        assert hasattr(system, "remove")
        assert hasattr(system, "has")
        assert hasattr(system, "get")

        # Test basic functionality
        assert system.count() == 0
        assert not system.has("nonexistent")
        assert system.get("nonexistent") is None

    def test_collection_storage_strategy_verification(self) -> None:
        """Test Pipeline uses list, System uses priority queue."""
        pipeline = Pipeline(name="test_pipeline")
        system = System(name="test_system")

        # Pipeline should use list storage
        assert hasattr(pipeline, "children")
        assert isinstance(pipeline.children, list)

        # System should use priority queue storage
        assert hasattr(system, "process_heap")
        assert isinstance(system.process_heap, list)  # heapq uses list

    def test_collection_edge_cases(self) -> None:
        """Test collection edge cases.

        Tests empty collections, missing processes, duplicate names.
        """
        pipeline = Pipeline(name="test_pipeline")
        system = System(name="test_system")

        for collection in [pipeline, system]:
            # Empty collection behavior
            assert collection.count() == 0
            assert not collection.remove("nonexistent")
            assert not collection.has("missing")
            assert collection.get("missing") is None

            # Add a process
            process = MockProcess(name="test_process")
            collection.append(process)
            assert collection.count() == 1
            assert collection.has("test_process")
            assert collection.get("test_process") == process

            # Test duplicate name handling (should replace/update)
            process2 = MockProcess(name="test_process")  # Same name
            collection.append(process2)
            # Should still only have one process (behavior varies by
            # implementation)
            found_process = collection.get("test_process")
            assert found_process is not None

    def test_collection_child_management(self) -> None:
        """Test collection child management methods.

        Tests count(), append(), remove(), has(), get() work correctly.
        """
        pipeline = Pipeline(name="test_pipeline")
        system = System(name="test_system")

        for collection in [pipeline, system]:
            # Start empty
            assert collection.count() == 0

            # Add processes
            proc1 = MockProcess(name="process1")
            proc2 = MockProcess(name="process2")
            proc3 = MockProcess(name="process3")

            collection.append(proc1)
            assert collection.count() == 1
            assert collection.has("process1")
            assert collection.get("process1") == proc1

            collection.append(proc2)
            collection.append(proc3)
            assert collection.count() == 3

            # Remove process
            assert collection.remove("process2")
            assert collection.count() == 2
            assert not collection.has("process2")
            assert collection.get("process2") is None

            # Remove nonexistent
            assert not collection.remove("nonexistent")
            assert collection.count() == 2

    def test_collection_timing_integration(self) -> None:
        """Test initialize_timing() propagation.

        Tests propagation correctly to all children.
        """
        pipeline = Pipeline(name="test_pipeline")
        system = System(name="test_system")

        for collection in [pipeline, system]:
            # Add mock processes
            proc1 = MockProcess(
                name="process1", interval_ns=50_000_000
            )  # 50ms
            proc2 = MockProcess(
                name="process2", interval_ns=100_000_000
            )  # 100ms

            collection.append(proc1)
            collection.append(proc2)

            # Initialize timing
            collection.initialize_timing()

            # Verify timing was initialized on collection
            assert collection.start_time > 0
            assert collection.execution_count == 0

            # Verify timing was propagated to children
            assert proc1.start_time > 0
            assert proc1.execution_count == 0
            assert proc2.start_time > 0
            assert proc2.execution_count == 0
