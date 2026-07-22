"""Deterministic validation of governed subject ownership."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from app.academic_terms import academic_term_order, academic_term_sort_key
from app.institutional_units import (
    DEFAULT_REGISTRY, AcademicUnitRegistry, VALID_FORMAL_UNIT_TYPES,
    VALID_OPERATIONAL_ROLES,
)
from app.subject_ownership import (
    SubjectOwnershipRegistry, VALID_EVIDENCE_TYPES, VALID_MAPPING_STATUSES,
    VALID_RELATIONSHIP_TYPES, VALID_REVIEW_STATUSES,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SEC_SUBJECTS = ("PHYS", "CPSC", "CYBR", "IS", "CPEN", "EENG", "PCSE")


@dataclass(frozen=True)
class CrosswalkAuditFinding:
    severity: str
    code: str
    subject_code: str | None
    rule_ids: tuple[str, ...]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubjectCrosswalkAuditReport:
    registry_version: str
    registry_fingerprint: str
    governed_subjects: tuple[str, ...]
    provisional_subjects: tuple[str, ...]
    subjects_requiring_review: tuple[str, ...]
    units_without_subject_mappings: tuple[str, ...]
    findings: tuple[CrosswalkAuditFinding, ...]

    @property
    def valid(self) -> bool:
        return not any(item.severity == "error" for item in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "registry_version": self.registry_version,
            "registry_fingerprint": self.registry_fingerprint,
            "valid": self.valid,
            "governed_subjects": list(self.governed_subjects),
            "provisional_subjects": list(self.provisional_subjects),
            "subjects_requiring_review": list(self.subjects_requiring_review),
            "units_without_subject_mappings": list(self.units_without_subject_mappings),
            "findings": [item.to_dict() for item in self.findings],
        }

    def raise_for_errors(self) -> None:
        errors = [item for item in self.findings if item.severity == "error"]
        if errors:
            raise ValueError("Subject crosswalk audit failed: " + ", ".join(
                sorted({item.code for item in errors})
            ))


class SubjectCrosswalkAuditService:
    def audit(
        self,
        subject_registry: SubjectOwnershipRegistry | None = None,
        unit_registry: AcademicUnitRegistry | None = None,
        institutional_registry_path: Path = DEFAULT_REGISTRY,
    ) -> SubjectCrosswalkAuditReport:
        subjects = subject_registry or SubjectOwnershipRegistry.load()
        units_registry = unit_registry or AcademicUnitRegistry.load(institutional_registry_path)
        units = {item.unit_id: item for item in units_registry.units}
        findings: list[CrosswalkAuditFinding] = []
        by_subject: dict[str, list[Any]] = {}

        for unit in units_registry.units:
            if unit.formal_unit_type not in VALID_FORMAL_UNIT_TYPES:
                findings.append(_finding("error", "invalid_formal_unit_type", None, (), unit.unit_id))
            if set(unit.operational_roles) - VALID_OPERATIONAL_ROLES:
                findings.append(_finding("error", "invalid_operational_role", None, (), unit.unit_id))

        for record in subjects.records:
            by_subject.setdefault(record.subject_code, []).append(record)
            self._audit_record(record, units, findings)

        for subject, records in sorted(by_subject.items()):
            for index, left in enumerate(records):
                for right in records[index + 1:]:
                    if not _ranges_overlap(left, right):
                        continue
                    ids = tuple(sorted((left.record_id, right.record_id)))
                    findings.append(_finding("error", "overlapping_effective_ranges", subject, ids, "Overlapping subject-ownership periods."))
                    signatures = {
                        (left.owning_academic_unit_id, left.analytical_academic_unit_id, left.mapping_status),
                        (right.owning_academic_unit_id, right.analytical_academic_unit_id, right.mapping_status),
                    }
                    code = "duplicate_subject_record" if len(signatures) == 1 else "conflicting_governed_records"
                    findings.append(_finding("error", code, subject, ids, "Competing subject-ownership records."))

        self._audit_sec(subjects, units_registry, findings)
        payload = yaml.safe_load(Path(institutional_registry_path).read_text(encoding="utf-8")) or {}
        if payload.get("subject_mappings"):
            findings.append(_finding("error", "legacy_embedded_subject_mappings", None, (), "institutional_units.yaml still embeds subject ownership."))

        mapped_units = {
            unit_id for record in subjects.records
            for unit_id in (record.owning_academic_unit_id, record.analytical_academic_unit_id)
            if unit_id
        }
        findings.sort(key=lambda item: (item.severity, item.code, item.subject_code or "", item.rule_ids))
        return SubjectCrosswalkAuditReport(
            subjects.schema_version, subjects.fingerprint,
            _subjects_by_review(subjects, "governed"),
            _subjects_by_review(subjects, "provisional"),
            _subjects_by_review(subjects, "requires_review"),
            tuple(sorted(set(units) - mapped_units)), tuple(findings),
        )

    def _audit_record(self, record, units, findings):
        rid = (record.record_id,)
        if record.mapping_status not in VALID_MAPPING_STATUSES:
            findings.append(_finding("error", "invalid_mapping_status", record.subject_code, rid, record.mapping_status))
        if record.relationship_type not in VALID_RELATIONSHIP_TYPES:
            findings.append(_finding("error", "invalid_relationship_type", record.subject_code, rid, record.relationship_type))
        if record.review_status not in VALID_REVIEW_STATUSES:
            findings.append(_finding("error", "invalid_review_status", record.subject_code, rid, record.review_status))
        if not 0.0 <= record.confidence <= 1.0:
            findings.append(_finding("error", "invalid_confidence", record.subject_code, rid, str(record.confidence)))
        for field, unit_id in (("owning", record.owning_academic_unit_id), ("analytical", record.analytical_academic_unit_id)):
            if not unit_id:
                findings.append(_finding("error", f"missing_{field}_unit", record.subject_code, rid, "Unit is required."))
            elif unit_id not in units:
                findings.append(_finding("error", f"unknown_{field}_unit", record.subject_code, rid, unit_id))
            elif units[unit_id].deprecated:
                findings.append(_finding("error", "deprecated_academic_unit", record.subject_code, rid, unit_id))
        if not record.evidence:
            findings.append(_finding("error", "missing_evidence", record.subject_code, rid, "Evidence is required."))
        for evidence in record.evidence:
            if evidence.source_type not in VALID_EVIDENCE_TYPES:
                findings.append(_finding("error", "invalid_evidence_type", record.subject_code, rid, evidence.source_type))
            if not evidence.source or not evidence.assertion:
                findings.append(_finding("error", "incomplete_evidence", record.subject_code, rid, "Source and assertion are required."))
            if evidence.source_type == "institutional_expert" and not evidence.reviewer:
                findings.append(_finding("error", "institutional_expert_missing_reviewer", record.subject_code, rid, "Reviewer is required."))
            if evidence.source_type in {"governed_registry", "official_catalog", "registrar_record", "institutional_document", "historical_record"}:
                if Path(evidence.source).is_absolute() or urlparse(evidence.source).scheme:
                    findings.append(_finding("error", "non_repository_relative_source", record.subject_code, rid, evidence.source))
                elif not (REPOSITORY_ROOT / evidence.source).exists():
                    findings.append(_finding("error", "evidence_source_not_found", record.subject_code, rid, evidence.source))
        if not record.rationale.strip():
            findings.append(_finding("error", "missing_rationale", record.subject_code, rid, "Rationale is required."))
        for term in (record.effective_start_term, record.effective_end_term):
            if term and not academic_term_order(term).supported:
                findings.append(_finding("error", "invalid_effective_term", record.subject_code, rid, term))
        if record.review_status == "governed" and record.mapping_status in {"unmapped", "ambiguous", "unsupported"}:
            findings.append(_finding("error", "governed_unresolved_target", record.subject_code, rid, record.mapping_status))

    def _audit_sec(self, subjects, units, findings):
        sec = units.get("academic_unit:sec")
        if not sec or sec.formal_unit_type != "dependent_school" or "department_equivalent" not in sec.operational_roles:
            findings.append(_finding("error", "invalid_sec_ontology", None, (), "SEC ontology is incomplete."))
        for code in SEC_SUBJECTS:
            records = subjects.records_for_subject(code)
            if len(records) != 1:
                findings.append(_finding("error", "missing_required_sec_subject", code, (), "Exactly one SEC record is required."))
                continue
            item = records[0]
            if (item.owning_academic_unit_id != "academic_unit:sec" or
                    item.analytical_academic_unit_id != "academic_unit:sec"):
                findings.append(_finding("error", "invalid_sec_target", code, (item.record_id,), "SEC target required."))
            if item.mapping_status != "intentionally_grouped_department_equivalent" or item.review_status != "governed":
                findings.append(_finding("error", "invalid_sec_governance", code, (item.record_id,), "Governed grouping required."))
        forbidden = {"physics", "computer science", "cybersecurity", "information science", "computer engineering", "electrical engineering", "physics and computer science"}
        for unit in units.units:
            label = unit.published_name.casefold().removeprefix("department of ")
            if unit.formal_unit_type == "department" and label in forbidden:
                findings.append(_finding("error", "fictional_sec_department", None, (), unit.unit_id))


def _finding(severity, code, subject, records, message):
    return CrosswalkAuditFinding(severity, code, subject, tuple(records), message)


def _subjects_by_review(registry, status):
    return tuple(sorted({item.subject_code for item in registry.records if item.review_status == status}))


def _ranges_overlap(left, right):
    ll = academic_term_sort_key(left.effective_start_term) if left.effective_start_term else None
    lh = academic_term_sort_key(left.effective_end_term) if left.effective_end_term else None
    rl = academic_term_sort_key(right.effective_start_term) if right.effective_start_term else None
    rh = academic_term_sort_key(right.effective_end_term) if right.effective_end_term else None
    return not (lh is not None and rl is not None and lh < rl or rh is not None and ll is not None and rh < ll)


__all__ = ["CrosswalkAuditFinding", "SEC_SUBJECTS", "SubjectCrosswalkAuditReport", "SubjectCrosswalkAuditService"]
