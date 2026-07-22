"""Governed facts about instructional-subject ownership.

Organizational definitions remain authoritative in ``institutional_units.yaml``.
This registry records only reviewed subject-prefix ownership assertions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from app.academic_terms import academic_term_sort_key


DEFAULT_SUBJECT_OWNERSHIP_REGISTRY = (
    Path(__file__).resolve().parents[1] / "config" / "subject_ownership.yaml"
)

VALID_MAPPING_STATUSES = {
    "mapped", "intentionally_grouped_department_equivalent", "interdisciplinary",
    "service_subject", "non_workforce_unit", "ambiguous", "unmapped", "unsupported",
}
VALID_RELATIONSHIP_TYPES = {
    "owns_instructional_subject", "analytically_assigned_to",
    "interdisciplinary_coordination", "service_subject_provision",
    "non_workforce_subject", "centrally_administered_subject",
    "interdisciplinary_subject", "service_subject", "cross_unit_subject",
    "operational_schedule_alias", "unresolved",
}
VALID_REVIEW_STATUSES = {"governed", "provisional", "requires_review"}
VALID_EVIDENCE_TYPES = {
    "governed_registry", "official_catalog", "registrar_record",
    "administrative_review", "institutional_expert", "institutional_document",
    "historical_record",
}


@dataclass(frozen=True)
class SubjectOwnershipEvidence:
    source: str
    source_type: str
    assertion: str
    reviewer: str | None = None
    review_date: str | None = None


@dataclass(frozen=True)
class SubjectOwnershipRecord:
    record_id: str
    subject_code: str
    display_name: str
    owning_academic_unit_id: str | None
    analytical_academic_unit_id: str | None
    relationship_type: str
    mapping_status: str
    mapping_method: str
    confidence: float
    review_status: str
    evidence: tuple[SubjectOwnershipEvidence, ...]
    rationale: str
    effective_start_term: str | None = None
    effective_end_term: str | None = None
    notes: str | None = None
    canonical_subject_code: str | None = None
    catalog_visible_subject_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence"] = [asdict(item) for item in self.evidence]
        return value


class SubjectOwnershipRegistry:
    def __init__(
        self,
        records: Iterable[SubjectOwnershipRecord],
        schema_version: str = "1",
        registry_id: str = "cnu.subject_ownership",
        description: str = "",
        source_path: Path | None = None,
    ):
        self.schema_version = str(schema_version)
        self.registry_id = registry_id
        self.description = description
        self.source_path = source_path
        self._records = tuple(records)

    @classmethod
    def load(
        cls, path: Path = DEFAULT_SUBJECT_OWNERSHIP_REGISTRY, *, validate: bool = True
    ) -> "SubjectOwnershipRegistry":
        source = Path(path)
        payload = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
        records = tuple(_record_from_dict(item) for item in payload.get("subjects") or ())
        registry = cls(
            records,
            schema_version=str(payload.get("schema_version", "1")),
            registry_id=str(payload.get("registry_id", "cnu.subject_ownership")),
            description=str(payload.get("description") or ""),
            source_path=source,
        )
        if validate:
            registry.validate()
        return registry

    @property
    def records(self) -> tuple[SubjectOwnershipRecord, ...]:
        return self._records

    def records_for_subject(
        self, subject_code: str, academic_term: str | None = None
    ) -> tuple[SubjectOwnershipRecord, ...]:
        subject = str(subject_code or "").strip().upper()
        return tuple(
            item for item in self._records
            if item.subject_code == subject and _applies(item, academic_term)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "registry_id": self.registry_id,
            "description": self.description,
            "subjects": [item.to_dict() for item in sorted(self._records, key=_record_key)],
        }

    def validate(self) -> None:
        """Reject structurally inconsistent governed configuration on load."""
        from app.institutional_units import AcademicUnitRegistry

        units = {item.unit_id for item in AcademicUnitRegistry.load().units}
        by_subject: dict[str, list[SubjectOwnershipRecord]] = {}
        for record in self._records:
            by_subject.setdefault(record.subject_code, []).append(record)
            if not record.subject_code or not record.record_id:
                raise ValueError("Subject ownership requires stable record and subject IDs")
            if record.owning_academic_unit_id not in units:
                raise ValueError(f"Unknown owning academic unit in {record.record_id}")
            if record.analytical_academic_unit_id not in units:
                raise ValueError(f"Unknown analytical academic unit in {record.record_id}")
            if not 0.0 <= record.confidence <= 1.0:
                raise ValueError(f"Invalid confidence in {record.record_id}")
            if record.mapping_status not in VALID_MAPPING_STATUSES:
                raise ValueError(f"Invalid mapping status in {record.record_id}")
            if record.relationship_type not in VALID_RELATIONSHIP_TYPES:
                raise ValueError(f"Invalid relationship type in {record.record_id}")
            if record.review_status not in VALID_REVIEW_STATUSES:
                raise ValueError(f"Invalid review status in {record.record_id}")
            if not record.evidence or not record.rationale.strip():
                raise ValueError(f"Evidence and rationale are required in {record.record_id}")
        for records in by_subject.values():
            for index, left in enumerate(records):
                for right in records[index + 1:]:
                    if _periods_overlap(left, right):
                        raise ValueError(
                            f"Overlapping subject ownership records: {left.record_id}, {right.record_id}"
                        )

    @property
    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _record_from_dict(value: Mapping[str, Any]) -> SubjectOwnershipRecord:
    return SubjectOwnershipRecord(
        record_id=str(value["record_id"]),
        subject_code=str(value["subject_code"]).strip().upper(),
        display_name=str(value.get("display_name") or value["subject_code"]),
        owning_academic_unit_id=value.get("owning_academic_unit_id"),
        analytical_academic_unit_id=value.get("analytical_academic_unit_id"),
        relationship_type=str(value.get("relationship_type") or ""),
        mapping_status=str(value.get("mapping_status") or ""),
        mapping_method=str(value.get("mapping_method") or ""),
        confidence=float(value.get("confidence", 0.0)),
        review_status=str(value.get("review_status") or ""),
        evidence=tuple(
            SubjectOwnershipEvidence(
                source=str(item.get("source") or ""),
                source_type=str(item.get("source_type") or ""),
                assertion=str(item.get("assertion") or ""),
                reviewer=str(item["reviewer"]) if item.get("reviewer") else None,
                review_date=str(item["review_date"]) if item.get("review_date") else None,
            )
            for item in value.get("evidence") or ()
        ),
        rationale=str(value.get("rationale") or ""),
        effective_start_term=value.get("effective_start_term"),
        effective_end_term=value.get("effective_end_term"),
        notes=value.get("notes"),
        canonical_subject_code=(
            str(value["canonical_subject_code"]).strip().upper()
            if value.get("canonical_subject_code") else None
        ),
        catalog_visible_subject_code=(
            str(value["catalog_visible_subject_code"]).strip().upper()
            if value.get("catalog_visible_subject_code") else None
        ),
    )


def _applies(record: SubjectOwnershipRecord, academic_term: str | None) -> bool:
    if not academic_term:
        return True
    key = academic_term_sort_key(academic_term)
    if record.effective_start_term and key < academic_term_sort_key(record.effective_start_term):
        return False
    if record.effective_end_term and key > academic_term_sort_key(record.effective_end_term):
        return False
    return True


def _record_key(record: SubjectOwnershipRecord) -> tuple[str, str, str, str]:
    return (
        record.subject_code, record.effective_start_term or "",
        record.effective_end_term or "", record.record_id,
    )


def _periods_overlap(left: SubjectOwnershipRecord, right: SubjectOwnershipRecord) -> bool:
    left_start = academic_term_sort_key(left.effective_start_term) if left.effective_start_term else None
    left_end = academic_term_sort_key(left.effective_end_term) if left.effective_end_term else None
    right_start = academic_term_sort_key(right.effective_start_term) if right.effective_start_term else None
    right_end = academic_term_sort_key(right.effective_end_term) if right.effective_end_term else None
    return not (
        left_end is not None and right_start is not None and left_end < right_start
        or right_end is not None and left_start is not None and right_end < left_start
    )


__all__ = [
    "DEFAULT_SUBJECT_OWNERSHIP_REGISTRY", "SubjectOwnershipEvidence",
    "SubjectOwnershipRecord", "SubjectOwnershipRegistry", "VALID_EVIDENCE_TYPES",
    "VALID_MAPPING_STATUSES", "VALID_RELATIONSHIP_TYPES", "VALID_REVIEW_STATUSES",
]
