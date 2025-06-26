"""Tests for Buffer timestamped state storage."""

from aifand import Buffer, Sensor, State


class TestBuffer:
    """Test Buffer timestamped state storage functionality."""

    def test_buffer_creation(self) -> None:
        """Test creating an empty buffer."""
        buffer = Buffer(name="test_buffer")

        assert buffer.is_empty()
        assert buffer.count() == 0
        assert buffer.get_latest() is None
        assert buffer.get_oldest() is None

    def test_buffer_store_and_retrieve(self) -> None:
        """Test storing and retrieving states."""
        buffer = Buffer(name="test_buffer")

        # Create test states
        sensor = Sensor(name="temp", properties={"value": 25.0})
        state1 = State(devices={"temp": sensor})
        states1 = {"actual": state1}

        # Store with timestamp
        buffer.store(1000, states1)

        assert not buffer.is_empty()
        assert buffer.count() == 1

        # Retrieve latest
        latest = buffer.get_latest()
        assert latest is not None
        timestamp, states = latest
        assert timestamp == 1000
        assert "actual" in states
        assert states["actual"].has_device("temp")

    def test_buffer_chronological_order(self) -> None:
        """Test states are stored in chronological order."""
        buffer = Buffer(name="test_buffer")

        # Store out of order
        buffer.store(3000, {"state": State()})
        buffer.store(1000, {"state": State()})
        buffer.store(2000, {"state": State()})

        assert buffer.count() == 3

        # Should be in chronological order
        oldest = buffer.get_oldest()
        latest = buffer.get_latest()

        assert oldest[0] == 1000
        assert latest[0] == 3000

    def test_buffer_get_recent(self) -> None:
        """Test getting recent entries within duration."""
        buffer = Buffer(name="test_buffer")

        # Store entries across time
        buffer.store(1000, {"state": State()})
        buffer.store(2000, {"state": State()})
        buffer.store(3000, {"state": State()})
        buffer.store(4000, {"state": State()})

        # Get recent 1500ns (should get 3000 and 4000)
        recent = buffer.get_recent(1500)
        timestamps = [entry[0] for entry in recent]

        assert len(recent) == 2
        assert timestamps == [3000, 4000]

    def test_buffer_get_range(self) -> None:
        """Test getting entries within time range."""
        buffer = Buffer(name="test_buffer")

        # Store entries
        buffer.store(1000, {"state": State()})
        buffer.store(2000, {"state": State()})
        buffer.store(3000, {"state": State()})
        buffer.store(4000, {"state": State()})

        # Get range 1500-3500 (should get 2000 and 3000)
        range_entries = buffer.get_range(1500, 3500)
        timestamps = [entry[0] for entry in range_entries]

        assert len(range_entries) == 2
        assert timestamps == [2000, 3000]

    def test_buffer_prune_before(self) -> None:
        """Test pruning entries before timestamp."""
        buffer = Buffer(name="test_buffer")

        # Store entries
        buffer.store(1000, {"state": State()})
        buffer.store(2000, {"state": State()})
        buffer.store(3000, {"state": State()})
        buffer.store(4000, {"state": State()})

        assert buffer.count() == 4

        # Prune before 2500 (should remove 1000 and 2000)
        removed_count = buffer.prune_before(2500)

        assert removed_count == 2
        assert buffer.count() == 2

        oldest = buffer.get_oldest()
        assert oldest[0] == 3000

    def test_buffer_clear(self) -> None:
        """Test clearing all entries."""
        buffer = Buffer(name="test_buffer")

        # Add entries
        buffer.store(1000, {"state": State()})
        buffer.store(2000, {"state": State()})

        assert buffer.count() == 2

        # Clear
        buffer.clear()

        assert buffer.is_empty()
        assert buffer.count() == 0

    def test_buffer_state_isolation(self) -> None:
        """Test that stored states are properly isolated."""
        buffer = Buffer(name="test_buffer")

        # Create and store state
        sensor = Sensor(name="temp", properties={"value": 25.0})
        original_state = State(devices={"temp": sensor})
        states = {"actual": original_state}

        buffer.store(1000, states)

        # Modify original states dictionary
        sensor2 = Sensor(name="temp2", properties={"value": 30.0})
        states["new"] = State(devices={"temp2": sensor2})

        # Buffer should have isolated copy
        stored = buffer.get_latest()
        assert stored is not None
        _, stored_states = stored

        assert "actual" in stored_states
        assert "new" not in stored_states  # Should not have new entry
