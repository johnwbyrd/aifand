"""Base entity class for identifiable objects."""

from typing import Any
from uuid import NAMESPACE_DNS, UUID, getnode, uuid4, uuid5

from pydantic import BaseModel, ConfigDict, Field


class Entity(BaseModel):
    """Base class for all identifiable objects in the aifand system.

    Provides unique identification through UUID and human-readable
    naming. Supports arbitrary additional fields through pydantic's
    extra="allow" configuration. All entities can be serialized to/from
    JSON while preserving all fields.
    """

    model_config = ConfigDict(extra="allow", frozen=True)

    uuid: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this entity",
    )
    name: str = Field(
        min_length=1, description="Human-readable name for this entity"
    )

    def __init__(self, unique_id: str | None = None, **data: Any) -> None:
        """Initialize Entity with automatic UUID generation.

        Args:
            unique_id: Optional unique identifier for deterministic
                UUID. If provided, creates a deterministic UUID based
                on this machine and the unique identifier. Used for
                hardware entities that need stable UUIDs across
                restarts.
            **data: Field values for the entity
        """
        if unique_id is not None and "uuid" not in data:
            # Create deterministic UUID from machine ID + unique_id
            machine_id = getnode()
            dns_name = f"{machine_id}.{unique_id}.uuid.aifand.com"
            data["uuid"] = uuid5(NAMESPACE_DNS, dns_name)
        super().__init__(**data)

    def __repr__(self) -> str:
        """Return string representation showing all fields."""
        fields = []
        for field_name, field_value in self.model_dump().items():
            if isinstance(field_value, str):
                fields.append(f"{field_name}='{field_value}'")
            else:
                fields.append(f"{field_name}={field_value}")

        return f"{self.__class__.__name__}({', '.join(fields)})"
