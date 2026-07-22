"""Derive schedule-subject mappings from ownership and unit registries."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from app.institutional_units import AcademicUnitRegistry
from app.subject_ownership import SubjectOwnershipRegistry


class AcademicUnitMappingStatus(str, Enum):
    MAPPED = "mapped"
    AMBIGUOUS = "ambiguous"
    UNMAPPED = "unmapped"
    INTENTIONALLY_GROUPED = "intentionally_grouped_department_equivalent"
    INTERDISCIPLINARY = "interdisciplinary"
    SERVICE_SUBJECT = "service_subject"
    NON_WORKFORCE_UNIT = "non_workforce_unit"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class AcademicUnitMappingResult:
    subject_code: str
    status: str
    subject_display_name: str | None
    owning_academic_unit_id: str | None
    owning_academic_unit_name: str | None
    analytical_academic_unit_id: str | None
    analytical_academic_unit_name: str | None
    formal_unit_type: str | None
    operational_roles: tuple[str, ...]
    relationship_type: str | None
    mapping_source: str | None
    authoritative_source_type: str | None
    mapping_method: str | None
    mapping_rule: str | None
    confidence: float | None
    rationale: str
    review_status: str | None
    evidence: tuple[dict[str, Any], ...] = ()
    effective_start_term: str | None = None
    effective_end_term: str | None = None
    notes: str | None = None
    candidate_unit_ids: tuple[str, ...] = ()
    canonical_subject_code: str | None = None
    catalog_visible_subject_code: str | None = None

    @property
    def academic_unit_id(self) -> str | None:
        """Backward-compatible alias for the analytical unit."""
        return self.analytical_academic_unit_id

    @property
    def academic_unit_name(self) -> str | None:
        return self.analytical_academic_unit_name

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["operational_roles"] = list(self.operational_roles)
        value["candidate_unit_ids"] = list(self.candidate_unit_ids)
        value["evidence"] = list(self.evidence)
        value["academic_unit_id"] = self.academic_unit_id
        value["academic_unit_name"] = self.academic_unit_name
        return value


class AcademicUnitMappingService:
    """Apply governed ownership facts; never infer from course or instructor text."""

    def __init__(
        self,
        unit_registry: AcademicUnitRegistry | None = None,
        subject_registry: SubjectOwnershipRegistry | None = None,
    ):
        self.unit_registry = unit_registry or AcademicUnitRegistry.load()
        self.subject_registry = subject_registry or SubjectOwnershipRegistry.load()
        self.registry = self.unit_registry  # compatibility for unit-oriented callers

    def map_subject(
        self, subject_code: str | None, academic_term: str | None = None
    ) -> AcademicUnitMappingResult:
        subject = str(subject_code or "").strip().upper()
        if not subject:
            return _empty(subject, AcademicUnitMappingStatus.UNSUPPORTED.value,
                          "A usable published subject code is required.")
        records = self.subject_registry.records_for_subject(subject, academic_term)
        if not records:
            return _empty(subject, AcademicUnitMappingStatus.UNMAPPED.value,
                          "No governed subject-ownership assertion is registered.")
        signatures = {
            (item.owning_academic_unit_id, item.analytical_academic_unit_id,
             item.mapping_status, item.review_status)
            for item in records
        }
        candidates = tuple(sorted({
            unit_id for item in records
            for unit_id in (item.owning_academic_unit_id, item.analytical_academic_unit_id)
            if unit_id
        }))
        if len(records) != 1 or len(signatures) != 1:
            result = _empty(
                subject, AcademicUnitMappingStatus.AMBIGUOUS.value,
                "Multiple governed ownership assertions compete for this subject.",
                review_status="requires_review",
            )
            return AcademicUnitMappingResult(
                **{**asdict(result), "candidate_unit_ids": candidates}
            )
        record = records[0]
        units = {item.unit_id: item for item in self.unit_registry.units}
        owning = units.get(record.owning_academic_unit_id or "")
        analytical = units.get(record.analytical_academic_unit_id or "")
        if owning is None or analytical is None:
            return AcademicUnitMappingResult(
                subject, AcademicUnitMappingStatus.UNSUPPORTED.value, record.display_name,
                record.owning_academic_unit_id, owning.published_name if owning else None,
                record.analytical_academic_unit_id,
                analytical.published_name if analytical else None,
                analytical.formal_unit_type if analytical else None,
                analytical.operational_roles if analytical else (), record.relationship_type,
                _primary_source(record), _primary_source_type(record), record.mapping_method,
                record.record_id, record.confidence,
                "A referenced institutional unit is not registered.", record.review_status,
                tuple(asdict(item) for item in record.evidence), record.effective_start_term,
                record.effective_end_term, record.notes, candidates,
            )
        return AcademicUnitMappingResult(
            subject, record.mapping_status, record.display_name,
            owning.unit_id, owning.published_name, analytical.unit_id,
            analytical.published_name, analytical.formal_unit_type,
            analytical.operational_roles, record.relationship_type,
            _primary_source(record), _primary_source_type(record), record.mapping_method,
            record.record_id, record.confidence, record.rationale, record.review_status,
            tuple(asdict(item) for item in record.evidence), record.effective_start_term,
            record.effective_end_term, record.notes, (analytical.unit_id,),
            record.canonical_subject_code, record.catalog_visible_subject_code,
        )


def _empty(subject: str, status: str, rationale: str, review_status=None):
    return AcademicUnitMappingResult(
        subject, status, None, None, None, None, None, None, (), None, None, None,
        None, None, None, rationale, review_status,
    )


def _primary_source(record) -> str | None:
    return record.evidence[0].source if record.evidence else None


def _primary_source_type(record) -> str | None:
    return record.evidence[0].source_type if record.evidence else None


__all__ = ["AcademicUnitMappingResult", "AcademicUnitMappingService", "AcademicUnitMappingStatus"]
