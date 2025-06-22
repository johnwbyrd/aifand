from uuid import UUID, uuid4
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class Entity(BaseModel):
    """Base class for all identifiable objects in the aifand system.
    
    Provides unique identification through UUID and human-readable naming.
    Supports arbitrary additional fields through pydantic's extra="allow" configuration.
    All entities can be serialized to/from JSON while preserving all fields.
    """
    
    model_config = ConfigDict(extra="allow", frozen=True)
    
    uuid: UUID = Field(default_factory=uuid4, description="Unique identifier for this entity")
    name: str = Field(min_length=1, description="Human-readable name for this entity")
    
    def __repr__(self) -> str:
        """Return a string representation of the entity showing all fields."""
        fields = []
        for field_name, field_value in self.model_dump().items():
            if isinstance(field_value, str):
                fields.append(f"{field_name}='{field_value}'")
            else:
                fields.append(f"{field_name}={field_value}")
        
        return f"{self.__class__.__name__}({', '.join(fields)})"