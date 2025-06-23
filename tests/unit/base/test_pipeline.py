"""Tests for Pipeline serial coordination."""

import pytest

from src.aifand.base.device import Sensor
from src.aifand.base.pipeline import Pipeline
from src.aifand.base.state import State

from .mocks import CountingMixin, FailingMixin, MockProcess


class TestPipelineSerialCoordination:
    """Test Pipeline serial coordination for thermal control flows."""

    def test_pipeline_state_flow_validation(self) -> None:
        """Test input → child1.execute() → child2.execute() → output."""
        pipeline = Pipeline(name="test_pipeline")

        # Create mock processes that modify states
        class StateModifyingProcess(MockProcess):
            def __init__(self, name: str, add_device: str) -> None:
                super().__init__(name=name)
                self.add_device = add_device

            def _execute(self, states: dict[str, State]) -> dict[str, State]:
                result = super()._execute(states)
                if "data" in result:
                    sensor = Sensor(
                        name=self.add_device, properties={"value": 25.0}
                    )
                    result["data"] = result["data"].with_device(sensor)
                return result

        proc1 = StateModifyingProcess("proc1", "sensor1")
        proc2 = StateModifyingProcess("proc2", "sensor2")

        pipeline.append(proc1)
        pipeline.append(proc2)

        # Execute pipeline with initial state
        initial_state = State()
        result_states = pipeline.execute({"data": initial_state})

        # Verify both processes executed and modified state
        assert proc1.execution_timestamps
        assert proc2.execution_timestamps
        assert result_states["data"].has_device("sensor1")
        assert result_states["data"].has_device("sensor2")

    def test_pipeline_execution_order(self) -> None:
        """Test children execute in append order consistently."""
        pipeline = Pipeline(name="test_pipeline")

        # Create counting processes
        class CountingProcess(CountingMixin, MockProcess):
            pass

        proc1 = CountingProcess(name="proc1")
        proc2 = CountingProcess(name="proc2")
        proc3 = CountingProcess(name="proc3")

        pipeline.append(proc1)
        pipeline.append(proc2)
        pipeline.append(proc3)

        # Execute pipeline
        pipeline.execute({"test": State()})

        # Verify execution order by timestamps
        assert len(proc1.execution_timestamps) == 1
        assert len(proc2.execution_timestamps) == 1
        assert len(proc3.execution_timestamps) == 1

        # Timestamps should be in order (proc1 before proc2 before
        # proc3)
        assert proc1.execution_timestamps[0] <= proc2.execution_timestamps[0]
        assert proc2.execution_timestamps[0] <= proc3.execution_timestamps[0]

    def test_pipeline_error_resilience(self) -> None:
        """Test failed children don't break pipeline.

        Tests execution continues despite failures.
        """
        pipeline = Pipeline(name="test_pipeline")

        # Create mix of good and failing processes
        class CountingProcess(CountingMixin, MockProcess):
            pass

        class FailingProcess(FailingMixin, MockProcess):
            def __init__(self, name: str) -> None:
                super().__init__(name=name, fail_after=0)  # Fail immediately

        proc1 = CountingProcess(name="good1")
        proc2 = FailingProcess(name="bad1")
        proc3 = CountingProcess(name="good2")

        pipeline.append(proc1)
        pipeline.append(proc2)
        pipeline.append(proc3)

        # Execute pipeline - should not raise exception
        result_states = pipeline.execute({"test": State()})

        # Good processes should have executed
        assert proc1.counter == 1
        assert proc3.counter == 1

        # Pipeline should return result despite failures
        assert "test" in result_states

    def test_pipeline_permission_integration(self) -> None:
        """Test PermissionErrors bubble up correctly."""
        pytest.skip("Permissions testing deferred per user request")

    def test_pipeline_empty_handling(self) -> None:
        """Test graceful handling with no children.

        Tests passthrough behavior.
        """
        pipeline = Pipeline(name="empty_pipeline")

        # Create initial state
        sensor = Sensor(name="temp", properties={"value": 30.0})
        initial_state = State(devices={"temp": sensor})
        input_states = {"actual": initial_state, "desired": State()}

        # Execute empty pipeline
        result_states = pipeline.execute(input_states)

        # Should pass states through unchanged
        assert result_states == input_states
        assert result_states["actual"].has_device("temp")
        assert (
            result_states["actual"].get_device("temp").properties["value"]
            == 30.0
        )

    def test_pipeline_list_storage(self) -> None:
        """Test child management operations work correctly.

        Test with internal list.
        """
        pipeline = Pipeline(name="test_pipeline")

        # Test list storage directly
        assert isinstance(pipeline.children, list)
        assert len(pipeline.children) == 0

        # Add processes
        proc1 = MockProcess(name="proc1")
        proc2 = MockProcess(name="proc2")
        proc3 = MockProcess(name="proc3")

        pipeline.append(proc1)
        pipeline.append(proc2)
        pipeline.append(proc3)

        # Verify list storage
        assert len(pipeline.children) == 3
        assert pipeline.children[0] == proc1
        assert pipeline.children[1] == proc2
        assert pipeline.children[2] == proc3

        # Test removal
        pipeline.remove("proc2")
        assert len(pipeline.children) == 2
        assert pipeline.children[0] == proc1
        assert pipeline.children[1] == proc3  # proc3 shifted down
