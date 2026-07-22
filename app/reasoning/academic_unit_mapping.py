"""Governed schedule-subject mapping to academic workforce units."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from app.institutional_units import AcademicUnitRegistry


class AcademicUnitMappingStatus(str, Enum):
    MAPPED = "mapped"
    AMBIGUOUS = "ambiguous"
    UNMAPPED = "unmapped"
    INTENTIONALLY_GROUPED = "intentionally_grouped_department_equivalent"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class AcademicUnitMappingResult:
    subject_code: str
    status: str
    academic_unit_id: str | None
    academic_unit_name: str | None
    formal_unit_type: str | None
    operational_roles: tuple[str, ...]
    mapping_source: str | None
    mapping_rule: str | None
    confidence: float | None
    rationale: str
    candidate_unit_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["operational_roles"] = list(self.operational_roles)
        value["candidate_unit_ids"] = list(self.candidate_unit_ids)
        return value


class AcademicUnitMappingService:
    """Apply only registered subject mappings; never infer from course text."""

    def __init__(self, registry: AcademicUnitRegistry | None = None):
        self.registry = registry or AcademicUnitRegistry.load()

    def map_subject(self, subject_code: str | None) -> AcademicUnitMappingResult:
        subject = str(subject_code or "").strip().upper()
        if not subject:
            return AcademicUnitMappingResult(
                subject, AcademicUnitMappingStatus.UNSUPPORTED.value,
                None, None, None, (), None, None, None,
                "A usable published subject code is required.",
            )
        rules = self.registry.rules_for_subject(subject)
        if not rules:
            return AcademicUnitMappingResult(
                subject, AcademicUnitMappingStatus.UNMAPPED.value,
                None, None, None, (), None, None, None,
                "No reviewed subject-to-academic-unit rule is registered.",
            )
        unit_ids = tuple(sorted({rule.unit_id for rule in rules}))
        if len(unit_ids) != 1 or len(rules) != 1:
            return AcademicUnitMappingResult(
                subject, AcademicUnitMappingStatus.AMBIGUOUS.value,
                None, None, None, (), None, None, None,
                "Multiple registered mapping rules compete for this subject.",
                unit_ids,
            )
        rule = rules[0]
        unit = self.registry.get(rule.unit_id)
        status = (
            AcademicUnitMappingStatus.INTENTIONALLY_GROUPED
            if rule.intentionally_grouped
            else AcademicUnitMappingStatus.MAPPED
        )
        return AcademicUnitMappingResult(
            subject_code=subject,
            status=status.value,
            academic_unit_id=unit.unit_id,
            academic_unit_name=unit.published_name,
            formal_unit_type=unit.formal_unit_type,
            operational_roles=unit.operational_roles,
            mapping_source=rule.mapping_source,
            mapping_rule=rule.rule_id,
            confidence=rule.confidence,
            rationale=rule.rationale,
            candidate_unit_ids=(unit.unit_id,),
        )


__all__ = [
    "AcademicUnitMappingResult",
    "AcademicUnitMappingService",
    "AcademicUnitMappingStatus",
]
