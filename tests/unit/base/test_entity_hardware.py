"""Tests for Entity hardware UUID functionality."""

from uuid import NAMESPACE_DNS, getnode, uuid5

from aifand import Entity


class TestEntityHardwareUUID:
    """Test Entity's deterministic UUID generation for hardware."""

    def test_entity_with_unique_id_creates_deterministic_uuid(self) -> None:
        """Test hardware entity gets deterministic UUID."""
        unique_id = "/sys/devices/platform/coretemp.0"
        entity1 = Entity(name="cpu_temp", unique_id=unique_id)
        entity2 = Entity(name="cpu_temp", unique_id=unique_id)

        # Same unique_id should create same UUID
        assert entity1.uuid == entity2.uuid

        # UUID should be deterministic based on machine + unique_id
        expected_uuid = uuid5(
            NAMESPACE_DNS, f"{getnode()}.{unique_id}.uuid.aifand.com"
        )
        assert entity1.uuid == expected_uuid

    def test_entity_without_unique_id_gets_random_uuid(self) -> None:
        """Test software entity gets random UUID."""
        entity1 = Entity(name="controller")
        entity2 = Entity(name="controller")

        # Different instances should have different UUIDs
        assert entity1.uuid != entity2.uuid

    def test_explicit_uuid_overrides_unique_id(self) -> None:
        """Test explicit uuid parameter overrides unique_id."""
        import uuid

        explicit_uuid = uuid.uuid4()

        entity = Entity(
            name="test", unique_id="/some/path", uuid=explicit_uuid
        )

        # Should use explicit UUID, not generate from unique_id
        assert entity.uuid == explicit_uuid

    def test_different_unique_ids_create_different_uuids(self) -> None:
        """Test different hardware paths get different UUIDs."""
        entity1 = Entity(
            name="sensor1", unique_id="/sys/devices/platform/coretemp.0"
        )
        entity2 = Entity(
            name="sensor2", unique_id="/sys/devices/platform/coretemp.1"
        )

        assert entity1.uuid != entity2.uuid

    def test_entity_serialization_with_unique_id(self) -> None:
        """Test entity created with unique_id serializes correctly."""
        unique_id = "/sys/devices/platform/hwmon.0"
        entity = Entity(name="test_sensor", unique_id=unique_id)

        # Serialize
        data = entity.model_dump()

        # unique_id is not persisted - only uuid and name
        assert "unique_id" not in data
        assert "uuid" in data
        assert "name" in data

        # Deserialize - creates new entity with same UUID
        entity2 = Entity.model_validate(data)
        assert entity2.uuid == entity.uuid
        assert entity2.name == entity.name
