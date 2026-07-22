"""Governed institutional academic-unit definitions and exact-name resolution.

The registry records reviewed organizational facts. It does not infer a unit's
formal type or analytical role from its name.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Optional, Tuple

import yaml

from app.semantic_identity import InstitutionalEntity


DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "config" / "institutional_units.yaml"

VALID_FORMAL_UNIT_TYPES = {
    "department", "independent_school", "dependent_school", "college",
    "faculty", "academic_program", "interdisciplinary_program",
    "university_unit", "unknown",
}
VALID_OPERATIONAL_ROLES = {
    "department_equivalent", "college_equivalent", "department_member",
    "faculty_home_unit", "workforce_allocation_unit", "dean_level_unit",
    "parent_academic_unit", "budgetary_rollup_unit",
    "intermediate_academic_unit", "interdisciplinary", "service_subject",
    "non_workforce_unit", "unresolved",
}


def _normalize_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


@dataclass(frozen=True)
class AcademicUnitDefinition:
    unit_id: str
    published_name: str
    aliases: Tuple[str, ...]
    entity_type: str
    formal_unit_type: str
    parent_unit_id: Optional[str]
    governance_level: str
    leadership_type: Optional[str]
    has_dean: Optional[bool]
    contains_subordinate_departments: bool
    operational_roles: Tuple[str, ...]
    subordinate_unit_ids: Tuple[str, ...] = ()
    abbreviation: Optional[str] = None
    specialties: Tuple[str, ...] = ()
    deprecated: bool = False

    def to_entity(self) -> InstitutionalEntity:
        return InstitutionalEntity(
            entity_type=self.entity_type,
            entity_id=self.unit_id,
            published_name=self.published_name,
            formal_unit_type=self.formal_unit_type,
            operational_roles=self.operational_roles,
            parent_unit_id=self.parent_unit_id,
            governance_level=self.governance_level,
            leadership_type=self.leadership_type,
            has_dean=self.has_dean,
            contains_subordinate_departments=self.contains_subordinate_departments,
        )

    @property
    def is_department_workforce_unit(self) -> bool:
        return self.formal_unit_type == "department" or "department_equivalent" in self.operational_roles


class AcademicUnitRegistry:
    def __init__(
        self,
        units: Iterable[AcademicUnitDefinition],
        version: str = "1",
    ):
        self.version = version
        self._units = {unit.unit_id: unit for unit in units}
        aliases = {}
        for unit in self._units.values():
            for label in (unit.published_name, unit.abbreviation, *unit.aliases):
                if not label:
                    continue
                key = _normalize_label(label)
                prior = aliases.get(key)
                if prior and prior != unit.unit_id:
                    raise ValueError(f"Academic-unit alias {label!r} is ambiguous")
                aliases[key] = unit.unit_id
        for unit in self._units.values():
            if unit.parent_unit_id and unit.parent_unit_id not in self._units:
                raise ValueError(f"Unknown parent unit {unit.parent_unit_id!r} for {unit.unit_id}")
            unknown = set(unit.subordinate_unit_ids) - set(self._units)
            if unknown:
                raise ValueError(f"Unknown subordinate units for {unit.unit_id}: {sorted(unknown)}")
        self._aliases = aliases

    @classmethod
    def load(cls, path: Path = DEFAULT_REGISTRY) -> "AcademicUnitRegistry":
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        units = tuple(_unit_from_dict(value) for value in payload.get("units") or ())
        return cls(units, str(payload.get("version", "1")))

    def get(self, unit_id: str) -> AcademicUnitDefinition:
        return self._units[unit_id]

    def resolve(self, published_label: Optional[str]) -> Optional[AcademicUnitDefinition]:
        if not published_label:
            return None
        unit_id = self._aliases.get(_normalize_label(published_label))
        return self._units.get(unit_id) if unit_id else None

    def parent_of(self, unit: AcademicUnitDefinition) -> Optional[AcademicUnitDefinition]:
        return self._units.get(unit.parent_unit_id) if unit.parent_unit_id else None

    @property
    def units(self) -> Tuple[AcademicUnitDefinition, ...]:
        return tuple(self._units.values())



def is_department_workforce_entity(value: Any) -> bool:
    """Return true for a formal department or explicitly governed equivalent."""
    if isinstance(value, InstitutionalEntity):
        entity_type = value.entity_type
        formal_type = value.formal_unit_type
        roles = value.operational_roles
    elif isinstance(value, Mapping):
        entity_type = str(value.get("entity_type") or "")
        metadata = value.get("metadata") or {}
        formal_type = value.get("formal_unit_type") or metadata.get("formal_unit_type")
        roles = tuple(value.get("operational_roles") or metadata.get("operational_roles") or ())
    else:
        entity_type = str(getattr(value, "entity_type", "") or "")
        formal_type = getattr(value, "formal_unit_type", None)
        metadata = getattr(value, "metadata", {}) or {}
        roles = tuple(getattr(value, "operational_roles", ()) or metadata.get("operational_roles") or ())
    return entity_type == "department" or formal_type == "department" or "department_equivalent" in roles


def _unit_from_dict(value: Mapping[str, Any]) -> AcademicUnitDefinition:
    return AcademicUnitDefinition(
        unit_id=str(value["unit_id"]), published_name=str(value["published_name"]),
        aliases=tuple(map(str, value.get("aliases") or ())),
        entity_type=str(value["entity_type"]), formal_unit_type=str(value["formal_unit_type"]),
        parent_unit_id=value.get("parent_unit_id"), governance_level=str(value["governance_level"]),
        leadership_type=value.get("leadership_type"),
        has_dean=value.get("has_dean"),
        contains_subordinate_departments=bool(value.get("contains_subordinate_departments", False)),
        operational_roles=tuple(map(str, value.get("operational_roles") or ())),
        subordinate_unit_ids=tuple(map(str, value.get("subordinate_unit_ids") or ())),
        abbreviation=value.get("abbreviation"),
        specialties=tuple(map(str, value.get("specialties") or ())),
        deprecated=bool(value.get("deprecated", False)),
    )


__all__ = [
    "AcademicUnitDefinition",
    "AcademicUnitRegistry",
    "VALID_FORMAL_UNIT_TYPES",
    "VALID_OPERATIONAL_ROLES",
    "is_department_workforce_entity",
]
