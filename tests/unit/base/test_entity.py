import json
from uuid import UUID

import pytest
from pydantic import ValidationError

from aifand.base.entity import Entity


@pytest.mark.unit
class TestEntity:
    """Test cases for the Entity base class."""

    def test_entity_creation_with_defaults(self):
        """Test entity creation with default UUID generation."""
        entity = Entity(name="test_entity")

        assert entity.name == "test_entity"
        assert isinstance(entity.uuid, UUID)
        assert entity.uuid is not None

    def test_entity_creation_with_provided_uuid(self, sample_uuid, sample_name):
        """Test entity creation with explicitly provided UUID."""
        entity = Entity(uuid=sample_uuid, name=sample_name)

        assert entity.uuid == sample_uuid
        assert entity.name == sample_name

    def test_entity_name_validation(self, sample_uuid):
        """Test that entity name validation works correctly."""
        # Valid names should work
        entity = Entity(uuid=sample_uuid, name="valid_name")
        assert entity.name == "valid_name"

        # Empty name should raise validation error
        with pytest.raises(ValidationError):
            Entity(uuid=sample_uuid, name="")

    def test_entity_uuid_immutability(self, sample_uuid, sample_name):
        """Test that UUID cannot be changed after creation."""
        entity = Entity(uuid=sample_uuid, name=sample_name)
        original_uuid = entity.uuid

        # pydantic models are immutable by default in v2
        with pytest.raises((AttributeError, ValidationError)):
            entity.uuid = UUID("87654321-4321-8765-cba9-987654321abc")

        assert entity.uuid == original_uuid

    def test_entity_serialization(self, sample_uuid, sample_name):
        """Test entity serialization to JSON."""
        entity = Entity(uuid=sample_uuid, name=sample_name)

        # Test model serialization to dict (preserves UUID objects)
        entity_dict = entity.model_dump()
        assert entity_dict["uuid"] == sample_uuid

        # Test JSON-mode serialization (converts UUID to string)
        entity_dict_json = entity.model_dump(mode="json")
        assert entity_dict_json["uuid"] == str(sample_uuid)
        assert entity_dict["name"] == sample_name

        # Test JSON serialization
        entity_json = entity.model_dump_json()
        parsed = json.loads(entity_json)
        assert parsed["uuid"] == str(sample_uuid)
        assert parsed["name"] == sample_name

    def test_entity_deserialization(self, sample_uuid, sample_name):
        """Test entity deserialization from JSON."""
        original_entity = Entity(uuid=sample_uuid, name=sample_name)
        entity_json = original_entity.model_dump_json()

        # Deserialize from JSON
        reconstructed_entity = Entity.model_validate_json(entity_json)

        assert reconstructed_entity.uuid == sample_uuid
        assert reconstructed_entity.name == sample_name
        assert reconstructed_entity == original_entity

    def test_entity_equality(self, sample_uuid, sample_name):
        """Test entity equality comparison."""
        entity1 = Entity(uuid=sample_uuid, name=sample_name)
        entity2 = Entity(uuid=sample_uuid, name=sample_name)
        entity3 = Entity(uuid=sample_uuid, name="different_name")

        # Same UUID and name should be equal
        assert entity1 == entity2

        # Different name but same UUID should not be equal
        assert entity1 != entity3

    def test_entity_representation(self, sample_uuid, sample_name):
        """Test entity string representation shows all fields."""
        entity = Entity(uuid=sample_uuid, name=sample_name)

        repr_str = repr(entity)
        assert sample_name in repr_str
        assert str(sample_uuid) in repr_str
        assert "Entity(" in repr_str

        # Test representation with arbitrary fields
        entity_with_extras = Entity(uuid=sample_uuid, name=sample_name, temperature=72.5, status="active")

        repr_with_extras = repr(entity_with_extras)
        assert sample_name in repr_with_extras
        assert str(sample_uuid) in repr_with_extras
        assert "72.5" in repr_with_extras
        assert "active" in repr_with_extras

    def test_entity_arbitrary_key_value_pairs(self, sample_uuid, sample_name):
        """Test that Entity accepts and preserves arbitrary key/value pairs."""
        # Create entity with arbitrary additional fields
        entity = Entity(
            uuid=sample_uuid,
            name=sample_name,
            temperature=72.5,
            status="active",
            metadata={"sensor_type": "thermal", "location": "cpu"},
            count=42,
            enabled=True,
        )

        # Verify all fields are accessible
        assert entity.uuid == sample_uuid
        assert entity.name == sample_name
        assert entity.temperature == 72.5
        assert entity.status == "active"
        assert entity.metadata == {"sensor_type": "thermal", "location": "cpu"}
        assert entity.count == 42
        assert entity.enabled is True

    def test_entity_arbitrary_fields_serialization(self, sample_uuid, sample_name):
        """Test that arbitrary fields are properly serialized and deserialized."""
        original_data = {
            "uuid": sample_uuid,
            "name": sample_name,
            "custom_float": 3.14159,
            "custom_string": "test_value",
            "custom_list": [1, 2, 3],
            "custom_dict": {"nested": "value"},
            "custom_bool": False,
        }

        # Create entity with arbitrary fields
        entity = Entity(**original_data)

        # Test serialization preserves all fields
        serialized = entity.model_dump(mode="json")
        assert serialized["uuid"] == str(sample_uuid)
        assert serialized["name"] == sample_name
        assert serialized["custom_float"] == 3.14159
        assert serialized["custom_string"] == "test_value"
        assert serialized["custom_list"] == [1, 2, 3]
        assert serialized["custom_dict"] == {"nested": "value"}
        assert serialized["custom_bool"] is False

        # Test JSON serialization/deserialization roundtrip
        json_data = entity.model_dump_json()
        reconstructed = Entity.model_validate_json(json_data)

        assert reconstructed.uuid == sample_uuid
        assert reconstructed.name == sample_name
        assert reconstructed.custom_float == 3.14159
        assert reconstructed.custom_string == "test_value"
        assert reconstructed.custom_list == [1, 2, 3]
        assert reconstructed.custom_dict == {"nested": "value"}
        assert reconstructed.custom_bool is False

    def test_entity_arbitrary_fields_equality(self, sample_uuid, sample_name):
        """Test that arbitrary fields are included in equality comparison."""
        entity1 = Entity(uuid=sample_uuid, name=sample_name, extra_field="value1")
        entity2 = Entity(uuid=sample_uuid, name=sample_name, extra_field="value1")
        entity3 = Entity(uuid=sample_uuid, name=sample_name, extra_field="value2")

        # Same arbitrary fields should be equal
        assert entity1 == entity2

        # Different arbitrary field values should not be equal
        assert entity1 != entity3

    def test_entity_arbitrary_fields_access(self, sample_uuid, sample_name):
        """Test accessing arbitrary fields through attribute and dict-like access."""
        entity = Entity(uuid=sample_uuid, name=sample_name, dynamic_field="dynamic_value")

        # Test attribute access
        assert entity.dynamic_field == "dynamic_value"

        # Test dict-like access through model_dump
        data = entity.model_dump()
        assert data["dynamic_field"] == "dynamic_value"

    def test_entity_inheritance_with_arbitrary_fields(self, sample_uuid, sample_name):
        """Test that inheritance works with arbitrary fields."""

        class TestSubEntity(Entity):
            typed_field: str = "default"

        # Create with both typed and arbitrary fields
        sub_entity = TestSubEntity(
            uuid=sample_uuid, name=sample_name, typed_field="typed_value", arbitrary_field="arbitrary_value"
        )

        assert isinstance(sub_entity, Entity)
        assert sub_entity.uuid == sample_uuid
        assert sub_entity.name == sample_name
        assert sub_entity.typed_field == "typed_value"
        assert sub_entity.arbitrary_field == "arbitrary_value"
