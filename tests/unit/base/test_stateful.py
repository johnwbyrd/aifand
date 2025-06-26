"""Tests for StatefulProcess class."""

from src.aifand.base.device import Sensor
from src.aifand.base.state import State, States
from src.aifand.base.stateful import StatefulProcess


class TestStatefulProcess:
    """Test StatefulProcess state management functionality."""

    def test_stateful_process_creation(self) -> None:
        """Test creating a StatefulProcess."""

        class TestStatefulProcess(StatefulProcess):
            pass

        process = TestStatefulProcess(name="test")

        assert process.name == "test"
        assert process.buffer_size_limit == 1000
        assert process.auto_prune_enabled is True
        assert process.max_age_ns == 300_000_000_000
        assert process.buffer is None  # Not initialized yet

    def test_stateful_process_initialization(self) -> None:
        """Test StatefulProcess initialization creates buffer."""

        class TestStatefulProcess(StatefulProcess):
            pass

        process = TestStatefulProcess(name="test")
        process.initialize()

        assert process.buffer is not None
        assert process.buffer.is_empty()
        assert process.start_time > 0

    def test_stateful_process_import_state(self) -> None:
        """Test default _import_state behavior stores in buffer."""

        class TestStatefulProcess(StatefulProcess):
            pass

        process = TestStatefulProcess(name="test")
        process.initialize()

        # Create test state
        sensor = Sensor(name="temp", properties={"value": 25.0})
        state = State(devices={"temp": sensor})
        states = States({"actual": state})

        # Import state should store in buffer
        process._import_state(states)

        assert not process.buffer.is_empty()
        assert process.buffer.count() == 1

        latest = process.buffer.get_latest()
        assert latest is not None
        _, stored_states = latest
        assert "actual" in stored_states

    def test_stateful_process_auto_pruning_by_size(self) -> None:
        """Test auto-pruning by buffer size limit."""

        class TestStatefulProcess(StatefulProcess):
            pass

        # Create with small buffer limit
        process = TestStatefulProcess(
            name="test", buffer_size_limit=3, auto_prune_enabled=True
        )
        process.initialize()

        # Add more entries than limit
        for _ in range(5):
            states = States({"actual": State()})
            process._import_state(states)

        # Should be pruned to limit
        assert process.buffer.count() <= 3

    def test_stateful_process_auto_pruning_by_age(self) -> None:
        """Test auto-pruning by maximum age."""

        class TestStatefulProcess(StatefulProcess):
            def get_time(self) -> int:
                # Mock time for testing
                return self.mock_time

        process = TestStatefulProcess(
            name="test",
            max_age_ns=1000,  # 1000ns max age
            auto_prune_enabled=True,
        )
        process.mock_time = 0
        process.initialize()

        # Store old entry
        process.mock_time = 500
        process._import_state(States({"actual": State()}))

        # Store new entry that should trigger pruning
        process.mock_time = 2000  # Now old entry is 1500ns old
        process._import_state(States({"actual": State()}))

        # Old entry should be pruned (older than 1000ns)
        assert process.buffer.count() == 1
        latest = process.buffer.get_latest()
        assert latest[0] == 2000

    def test_stateful_process_three_method_integration(self) -> None:
        """Test StatefulProcess works with three-method pattern."""

        class TestController(StatefulProcess):
            def __init__(self, name: str) -> None:
                super().__init__(name=name)
                self.buffer_used = False
                self.history_count = 0
                self._controller_states: States | None = None

            def _import_state(self, states: States) -> None:
                super()._import_state(states)  # Update Buffer
                self._controller_states = states

            def _think(self) -> None:
                # Use buffer data for control logic
                self.buffer_used = True
                if self.buffer and not self.buffer.is_empty():
                    # Get history for computation
                    recent = self.buffer.get_recent(1000000)  # 1ms history
                    self.history_count = len(recent)
                else:
                    self.history_count = 0

            def _export_state(self) -> States:
                return self._controller_states or States()

        controller = TestController(name="test_controller")

        # Execute with states
        sensor = Sensor(name="temp", properties={"value": 25.0})
        state = State(devices={"temp": sensor})
        input_states = States({"actual": state})

        result = controller.execute(input_states)

        assert controller.buffer_used
        assert (
            controller.history_count >= 1
        )  # Should see the state we just stored
        assert result == input_states

    def test_stateful_process_buffer_summary(self) -> None:
        """Test buffer summary for debugging."""

        class TestStatefulProcess(StatefulProcess):
            pass

        process = TestStatefulProcess(name="test")

        # Before initialization
        summary = process.get_buffer_summary()
        assert summary["buffer_initialized"] is False

        # After initialization
        process.initialize()
        summary = process.get_buffer_summary()
        assert summary["buffer_initialized"] is True
        assert summary["entry_count"] == 0
        assert summary["is_empty"] is True

        # After adding entries
        process._import_state(States({"actual": State()}))
        summary = process.get_buffer_summary()
        assert summary["entry_count"] == 1
        assert summary["is_empty"] is False
        assert "oldest_timestamp" in summary
        assert "latest_timestamp" in summary

    def test_stateful_process_custom_configuration(self) -> None:
        """Test StatefulProcess with custom configuration."""

        class TestStatefulProcess(StatefulProcess):
            pass

        process = TestStatefulProcess(
            name="test",
            buffer_size_limit=500,
            auto_prune_enabled=False,
            max_age_ns=60_000_000_000,  # 1 minute
        )

        assert process.buffer_size_limit == 500
        assert process.auto_prune_enabled is False
        assert process.max_age_ns == 60_000_000_000

    def test_stateful_process_serialization(self) -> None:
        """Test StatefulProcess serialization excludes runtime state."""

        class TestStatefulProcess(StatefulProcess):
            pass

        process = TestStatefulProcess(name="test")
        process.initialize()

        # Add some runtime state
        process._import_state(States({"actual": State()}))

        # Serialize - should only include configuration
        data = process.model_dump()

        assert data["name"] == "test"
        assert data["buffer_size_limit"] == 1000
        assert "_entries" not in data  # Buffer internal state excluded
