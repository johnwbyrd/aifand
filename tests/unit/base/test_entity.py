import pytest
from uuid import UUID
import json
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
        
        # Test model serialization
        entity_dict = entity.model_dump()
        assert entity_dict["uuid"] == str(sample_uuid)
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
        """Test entity string representation."""
        entity = Entity(uuid=sample_uuid, name=sample_name)
        
        repr_str = repr(entity)
        assert sample_name in repr_str
        assert str(sample_uuid) in repr_str

    def test_entity_inheritance_compatibility(self, sample_uuid, sample_name):
        """Test that Entity can be properly inherited."""
        class TestSubEntity(Entity):
            extra_field: str = "default"
        
        sub_entity = TestSubEntity(uuid=sample_uuid, name=sample_name, extra_field="test")
        
        assert isinstance(sub_entity, Entity)
        assert sub_entity.uuid == sample_uuid
        assert sub_entity.name == sample_name
        assert sub_entity.extra_field == "test"