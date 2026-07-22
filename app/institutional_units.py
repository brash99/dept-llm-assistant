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
    "non_workforce_unit", "academic_coordination", "curriculum_ownership_unit",
    "university_wide_program", "unresolved",
}


def _normalize_label(value: str) -> str:
    value = value.casefold().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


_EMERITUS = re.compile(r"\bemerit(?:us|a)\b", re.IGNORECASE)
_CONTAMINATION = re.compile(
    r"\b(?:b\.?\s*(?:a|s|ed|b\.?\s*a)|m\.?\s*(?:a|s|ed|fin)|"
    r"ph\.?\s*(?:d|b)|ed\.?\s*d|j\.?\s*d)\b|\b(?:university|college)\b",
    re.IGNORECASE,
)
_GOVERNED_ROLE_PREFIX = re.compile(
    r"^(Graduate Program Director)\s*-\s*(.+)$", re.IGNORECASE,
)


@dataclass(frozen=True)
class AcademicUnitResolution:
    original_label: str
    cleaned_label: str
    unit: "AcademicUnitDefinition | None"
    resolution_method: str
    classification: str
    active_workforce_eligible: bool
    exclusion_reason: str | None = None
    parser_contamination_detected: bool = False
    competing_unit_ids: Tuple[str, ...] = ()
    role_title: str | None = None

    @property
    def resolved(self) -> bool:
        return self.unit is not None

    @property
    def unit_id(self) -> str | None:
        return self.unit.unit_id if self.unit else None


@dataclass(frozen=True)
class FacultyWorkforceEligibility:
    active_workforce_eligible: bool
    exclusion_reason: str | None
    matched_published_values: Tuple[str, ...]


def assess_faculty_workforce_eligibility(value: Mapping[str, Any] | Any) -> FacultyWorkforceEligibility:
    """Exclude only explicit published emeritus/emerita status from active work."""
    fields = (
        "published_title", "published_titles", "published_category",
        "published_department", "academic_unit", "profile_heading",
    )
    published = []
    for field in fields:
        item = value.get(field) if isinstance(value, Mapping) else getattr(value, field, None)
        if isinstance(item, (tuple, list, set)):
            published.extend(str(part) for part in item if part)
        elif item:
            published.append(str(item))
    matches = tuple(sorted({item for item in published if _EMERITUS.search(item)}))
    return FacultyWorkforceEligibility(
        active_workforce_eligible=not matches,
        exclusion_reason="explicit_emeritus_or_emerita" if matches else None,
        matched_published_values=matches,
    )


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
    successor_unit_ids: Tuple[str, ...] = ()
    active_current_unit: bool = True
    valid_curriculum_ownership_unit: bool = False
    valid_faculty_home_unit: bool = False
    valid_conventional_denominator_unit: bool = False
    valid_analytical_rollup_unit: bool = False

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
            deprecated=self.deprecated,
        )

    @property
    def is_department_workforce_unit(self) -> bool:
        return not self.deprecated and (
            self.formal_unit_type == "department"
            or "department_equivalent" in self.operational_roles
        )


class AcademicUnitRegistry:
    def __init__(
        self,
        units: Iterable[AcademicUnitDefinition],
        version: str = "1",
    ):
        self.version = version
        self._units = {unit.unit_id: unit for unit in units}
        canonical = {}
        aliases = {}
        for unit in self._units.values():
            canonical_key = _normalize_label(unit.published_name)
            prior = canonical.get(canonical_key)
            if prior and prior != unit.unit_id:
                raise ValueError(f"Academic-unit canonical name {unit.published_name!r} is ambiguous")
            canonical[canonical_key] = unit.unit_id
            for label in (unit.abbreviation, *unit.aliases):
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
            unknown_successors = set(unit.successor_unit_ids) - set(self._units)
            if unknown_successors:
                raise ValueError(
                    f"Unknown successor units for {unit.unit_id}: {sorted(unknown_successors)}"
                )
        self._validate_acyclic()
        self._canonical = canonical
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
        key = _normalize_label(published_label)
        unit_id = self._canonical.get(key) or self._aliases.get(key)
        return self._units.get(unit_id) if unit_id else None

    def resolve_published_label(self, published_label: Optional[str]) -> AcademicUnitResolution:
        """Resolve governed labels with bounded, deterministic contamination cleanup."""
        original = " ".join(str(published_label or "").split())
        emeritus = bool(_EMERITUS.search(original))
        eligible = not emeritus
        exclusion = "explicit_emeritus_or_emerita" if emeritus else None
        if not original:
            return AcademicUnitResolution(
                original, original, None, "unresolved", "genuinely_unresolved",
                eligible, exclusion,
            )
        role_match = _GOVERNED_ROLE_PREFIX.fullmatch(original)
        if role_match:
            role_title = " ".join(role_match.group(1).split())
            program_label = " ".join(role_match.group(2).split())
            program = self._resolve_program_label(program_label)
            if program:
                return AcademicUnitResolution(
                    original, program_label, program, "governed_role_prefix",
                    "excluded_emeritus" if emeritus else
                    "administrative_role_with_governed_program",
                    eligible, exclusion, False, (), role_title,
                )
            return AcademicUnitResolution(
                original, program_label, None, "unresolved_role_prefix",
                "excluded_emeritus" if emeritus else "genuinely_unresolved",
                eligible, exclusion, False, (), role_title,
            )
        key = _normalize_label(original)
        if key in self._canonical:
            unit = self._units[self._canonical[key]]
            return AcademicUnitResolution(
                original, original, unit, "canonical_exact",
                "excluded_emeritus" if emeritus else (
                    "historical_unit" if unit.deprecated else "canonical_exact"
                ),
                eligible, exclusion,
            )
        if key in self._aliases:
            unit = self._units[self._aliases[key]]
            return AcademicUnitResolution(
                original, original, unit, "governed_alias",
                "excluded_emeritus" if emeritus else (
                    "historical_unit" if unit.deprecated else "governed_alias"
                ),
                eligible, exclusion,
            )
        cleaned, contaminated = _clean_published_unit_label(original)
        cleaned_key = _normalize_label(cleaned)
        if cleaned_key in self._canonical:
            unit = self._units[self._canonical[cleaned_key]]
            return AcademicUnitResolution(
                original, cleaned, unit, "cleaned_canonical",
                "excluded_emeritus" if emeritus else (
                    "historical_unit" if unit.deprecated else
                    "parser_contamination" if contaminated else "status_qualified"
                ), eligible, exclusion, contaminated,
            )
        if cleaned_key in self._aliases:
            unit = self._units[self._aliases[cleaned_key]]
            return AcademicUnitResolution(
                original, cleaned, unit, "cleaned_governed_alias",
                "excluded_emeritus" if emeritus else (
                    "historical_unit" if unit.deprecated else
                    "parser_contamination" if contaminated else "status_qualified"
                ), eligible, exclusion, contaminated,
            )
        candidates = self._embedded_candidates(cleaned_key)
        if len(candidates) == 1:
            unit = self._units[candidates[0]]
            return AcademicUnitResolution(
                original, cleaned, unit, "embedded_governed_unit",
                "excluded_emeritus" if emeritus else (
                    "historical_unit" if unit.deprecated else
                    "parser_contamination" if contaminated else "embedded_governed_unit"
                ), eligible, exclusion, contaminated,
            )
        if len(candidates) > 1:
            return AcademicUnitResolution(
                original, cleaned, None, "ambiguous",
                "excluded_emeritus" if emeritus else "ambiguous",
                eligible, exclusion, contaminated, tuple(candidates),
            )
        return AcademicUnitResolution(
            original, cleaned, None, "unresolved",
            "excluded_emeritus" if emeritus else "genuinely_unresolved",
            eligible, exclusion, contaminated,
        )

    def _resolve_program_label(self, label: str) -> AcademicUnitDefinition | None:
        key = _normalize_label(label)
        candidates = {
            unit.unit_id
            for unit in self._units.values()
            if unit.formal_unit_type in {"academic_program", "interdisciplinary_program"}
            and key in {
                _normalize_label(unit.published_name),
                *(_normalize_label(alias) for alias in unit.aliases),
            }
        }
        if len(candidates) != 1:
            return None
        return self._units[next(iter(candidates))]

    def _embedded_candidates(self, normalized_label: str) -> list[str]:
        matches: list[tuple[int, str]] = []
        for phrase, unit_id in {**self._aliases, **self._canonical}.items():
            tokens = phrase.split()
            if len(tokens) < 2:
                continue
            if re.search(rf"(?:^| ){re.escape(phrase)}(?: |$)", normalized_label):
                matches.append((len(tokens), unit_id))
        if not matches:
            return []
        unit_ids = {unit_id for _, unit_id in matches}
        if len(unit_ids) > 1:
            return sorted(unit_ids)
        longest = max(length for length, _ in matches)
        return sorted({unit_id for length, unit_id in matches if length == longest})

    def _validate_acyclic(self) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(unit_id: str) -> None:
            if unit_id in visiting:
                raise ValueError(f"Academic-unit hierarchy contains a cycle at {unit_id}")
            if unit_id in visited:
                return
            visiting.add(unit_id)
            parent = self._units[unit_id].parent_unit_id
            if parent:
                visit(parent)
            visiting.remove(unit_id)
            visited.add(unit_id)

        for unit_id in self._units:
            visit(unit_id)

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
        deprecated = value.deprecated
    elif isinstance(value, Mapping):
        entity_type = str(value.get("entity_type") or "")
        metadata = value.get("metadata") or {}
        formal_type = value.get("formal_unit_type") or metadata.get("formal_unit_type")
        roles = tuple(value.get("operational_roles") or metadata.get("operational_roles") or ())
        deprecated = bool(value.get("deprecated") or metadata.get("deprecated"))
    else:
        entity_type = str(getattr(value, "entity_type", "") or "")
        formal_type = getattr(value, "formal_unit_type", None)
        metadata = getattr(value, "metadata", {}) or {}
        roles = tuple(getattr(value, "operational_roles", ()) or metadata.get("operational_roles") or ())
        deprecated = bool(getattr(value, "deprecated", False) or metadata.get("deprecated"))
    return not deprecated and (
        entity_type == "department"
        or formal_type == "department"
        or "department_equivalent" in roles
    )


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
        successor_unit_ids=tuple(map(str, value.get("successor_unit_ids") or ())),
        active_current_unit=bool(value.get("active_current_unit", not value.get("deprecated", False))),
        valid_curriculum_ownership_unit=bool(value.get(
            "valid_curriculum_ownership_unit",
            value.get("formal_unit_type") in {"department", "academic_program", "interdisciplinary_program"},
        )),
        valid_faculty_home_unit=bool(value.get(
            "valid_faculty_home_unit",
            "faculty_home_unit" in (value.get("operational_roles") or ()),
        )),
        valid_conventional_denominator_unit=bool(value.get(
            "valid_conventional_denominator_unit",
            not value.get("deprecated", False) and (
                value.get("formal_unit_type") == "department"
                or "department_equivalent" in (value.get("operational_roles") or ())
            ),
        )),
        valid_analytical_rollup_unit=bool(value.get(
            "valid_analytical_rollup_unit",
            "college_equivalent" in (value.get("operational_roles") or ()),
        )),
    )


def _clean_published_unit_label(value: str) -> tuple[str, bool]:
    cleaned = _EMERITUS.sub("", value)
    cleaned = re.sub(r"\s*,\s*(?=$)", "", cleaned).strip(" ,")
    contaminated = False
    for match in re.finditer(r"[.;]", cleaned):
        suffix = cleaned[match.end():]
        if _CONTAMINATION.search(suffix) or ";" in cleaned[match.start():]:
            cleaned = cleaned[:match.start()].strip(" ,.;")
            contaminated = True
            break
    return " ".join(cleaned.split()), contaminated


__all__ = [
    "AcademicUnitDefinition",
    "AcademicUnitResolution",
    "AcademicUnitRegistry",
    "FacultyWorkforceEligibility",
    "VALID_FORMAL_UNIT_TYPES",
    "VALID_OPERATIONAL_ROLES",
    "assess_faculty_workforce_eligibility",
    "is_department_workforce_entity",
]
