"""Institutional entities represented in the Observatory topology."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EntityType(str, Enum):
    """Types of institutional entities that may participate in relationships."""

    DEPARTMENT = "department"
    PROGRAM = "program"
    COLLEGE = "college"
    SCHOOL = "school"
    CURRICULUM = "curriculum"
    STRATEGIC_GOAL = "strategic_goal"
    ACCREDITOR = "accreditor"
    FACILITY = "facility"
    INSTITUTION = "institution"
    OTHER = "other"


@dataclass(frozen=True)
class InstitutionalEntity:
    """A uniquely identified institutional entity."""

    id: str
    name: str
    entity_type: EntityType
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("InstitutionalEntity.id must not be empty.")

        if not self.name.strip():
            raise ValueError("InstitutionalEntity.name must not be empty.")
