"""Production-portable inventory and comparison for schedule subject mappings."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from app.academic_terms import academic_term_order, academic_term_sort_key
from app.reasoning.academic_unit_mapping import AcademicUnitMappingService


WORKFORCE_MAPPING_STATUSES = {
    "mapped", "intentionally_grouped_department_equivalent",
}
CLASSIFIED_NON_WORKFORCE_STATUSES = {
    "interdisciplinary", "service_subject", "non_workforce_unit",
}


@dataclass(frozen=True)
class ScheduleSubjectInventoryRow:
    subject_code: str
    display_name: str | None
    course_offering_count: int
    distinct_instructor_count: int
    term_count: int
    first_supported_term: str | None
    last_supported_term: str | None
    mapping_status: str
    relationship_type: str | None
    owning_academic_unit_id: str | None
    owning_academic_unit_name: str | None
    analytical_academic_unit_id: str | None
    analytical_academic_unit_name: str | None
    academic_unit_id: str | None
    academic_unit_name: str | None
    formal_unit_type: str | None
    operational_roles: tuple[str, ...]
    authoritative_source: str | None
    authoritative_source_type: str | None
    mapping_method: str | None
    mapping_rule: str | None
    confidence: float | None
    review_status: str | None
    rationale: str
    evidence_summary: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["operational_roles"] = list(self.operational_roles)
        value["evidence_summary"] = list(self.evidence_summary)
        return value


@dataclass(frozen=True)
class SubjectMappingCoverage:
    total_schedule_observations: int
    observations_with_usable_subject: int
    mapped_observations: int
    intentionally_grouped_observations: int
    interdisciplinary_observations: int
    service_subject_observations: int
    non_workforce_unit_observations: int
    ambiguous_observations: int
    unmapped_observations: int
    unsupported_observations: int
    provisional_observations: int
    requires_review_observations: int
    governed_classified_observations: int
    observation_level_coverage_percent: float
    total_subject_codes: int
    governed_classified_subject_codes: int
    subject_code_level_coverage_percent: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubjectReviewPriority:
    subject_code: str
    mapping_status: str
    course_offering_count: int
    term_count: int
    distinct_instructor_count: int
    last_supported_term: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScheduleSubjectMappingReport:
    source_object_count: int
    registry_fingerprint: str
    subject_inventory: tuple[ScheduleSubjectInventoryRow, ...]
    coverage: SubjectMappingCoverage
    review_queue: tuple[SubjectReviewPriority, ...]
    deterministic_report_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_object_count": self.source_object_count,
            "registry_fingerprint": self.registry_fingerprint,
            "subject_inventory": [item.to_dict() for item in self.subject_inventory],
            "coverage": self.coverage.to_dict(),
            "review_queue": [item.to_dict() for item in self.review_queue],
            "deterministic_report_fingerprint": self.deterministic_report_fingerprint,
        }


@dataclass(frozen=True)
class SubjectMappingComparison:
    old_registry_fingerprint: str
    new_registry_fingerprint: str
    newly_mapped_subjects: tuple[str, ...]
    changed_unit_subjects: tuple[str, ...]
    changed_status_subjects: tuple[str, ...]
    changed_source_subjects: tuple[str, ...]
    newly_ambiguous_subjects: tuple[str, ...]
    resolved_ambiguities: tuple[str, ...]
    newly_unmapped_subjects: tuple[str, ...]
    observation_coverage_change_percentage_points: float
    subject_coverage_change_percentage_points: float
    semantic_changes: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ScheduleSubjectMappingInventoryService:
    def __init__(self, mapping_service: AcademicUnitMappingService | None = None):
        self.mapping_service = mapping_service or AcademicUnitMappingService()

    def build(self, observations: Iterable[Any]) -> ScheduleSubjectMappingReport:
        values = tuple(observations)
        by_subject: dict[str, list[Any]] = defaultdict(list)
        status_counts: Counter[str] = Counter()
        usable_count = 0
        for observation in values:
            subject = str(_value(observation, "subject") or "").strip().upper()
            term = str(_value(observation, "academic_term") or "").strip()
            mapping = self.mapping_service.map_subject(subject, term)
            if mapping.status in {"unmapped", "ambiguous", "unsupported"}:
                status_counts[mapping.status] += 1
            elif mapping.review_status == "governed":
                status_counts[mapping.status] += 1
            else:
                status_counts[f"review:{mapping.review_status}"] += 1
            if subject:
                usable_count += 1
                by_subject[subject].append(observation)

        rows = tuple(self._row(subject, items) for subject, items in sorted(by_subject.items()))
        governed_subjects = sum(_is_governed_classification(row) for row in rows)
        governed_observations = sum(
            row.course_offering_count for row in rows if _is_governed_classification(row)
        )
        coverage = SubjectMappingCoverage(
            total_schedule_observations=len(values),
            observations_with_usable_subject=usable_count,
            mapped_observations=status_counts["mapped"],
            intentionally_grouped_observations=status_counts["intentionally_grouped_department_equivalent"],
            interdisciplinary_observations=status_counts["interdisciplinary"],
            service_subject_observations=status_counts["service_subject"],
            non_workforce_unit_observations=status_counts["non_workforce_unit"],
            ambiguous_observations=status_counts["ambiguous"],
            unmapped_observations=status_counts["unmapped"],
            unsupported_observations=status_counts["unsupported"],
            provisional_observations=status_counts["review:provisional"],
            requires_review_observations=status_counts["review:requires_review"],
            governed_classified_observations=governed_observations,
            observation_level_coverage_percent=_percent(governed_observations, usable_count),
            total_subject_codes=len(rows),
            governed_classified_subject_codes=governed_subjects,
            subject_code_level_coverage_percent=_percent(governed_subjects, len(rows)),
        )
        queue = tuple(sorted(
            (
                SubjectReviewPriority(
                    row.subject_code, row.mapping_status, row.course_offering_count,
                    row.term_count, row.distinct_instructor_count, row.last_supported_term,
                )
                for row in rows if row.mapping_status in {"unmapped", "ambiguous", "unsupported"}
            ),
            key=_review_priority_key,
        ))
        from app.reasoning.subject_crosswalk_audit import SubjectCrosswalkAuditService
        registry_fingerprint = SubjectCrosswalkAuditService().audit(
            self.mapping_service.subject_registry, self.mapping_service.unit_registry
        ).registry_fingerprint
        payload = {
            "source_object_count": len(values),
            "registry_fingerprint": registry_fingerprint,
            "subject_inventory": [row.to_dict() for row in rows],
            "coverage": coverage.to_dict(),
            "review_queue": [item.to_dict() for item in queue],
        }
        return ScheduleSubjectMappingReport(
            len(values), registry_fingerprint, rows, coverage, queue,
            _fingerprint(payload),
        )

    def _row(self, subject: str, observations: list[Any]) -> ScheduleSubjectInventoryRow:
        instructors = {
            _canonical_instructor(str(_value(item, "instructor_raw") or _value(item, "instructor_name") or ""))
            for item in observations
            if str(_value(item, "instructor_raw") or _value(item, "instructor_name") or "").strip()
        }
        terms = sorted({
            str(_value(item, "academic_term") or "").strip()
            for item in observations
            if academic_term_order(str(_value(item, "academic_term") or "").strip()).supported
        }, key=academic_term_sort_key)
        mappings = [
            self.mapping_service.map_subject(subject, str(_value(item, "academic_term") or ""))
            for item in observations
        ]
        signatures = {
            (item.status, item.academic_unit_id, item.review_status, item.mapping_source)
            for item in mappings
        }
        if len(signatures) == 1:
            mapping = mappings[0]
        else:
            mapping = self.mapping_service.map_subject(subject)
            if mapping.status != "ambiguous":
                mapping = _ambiguous_mapping(subject, mappings)
        return ScheduleSubjectInventoryRow(
            subject_code=subject,
            display_name=mapping.subject_display_name,
            course_offering_count=len(observations),
            distinct_instructor_count=len(instructors),
            term_count=len(terms),
            first_supported_term=terms[0] if terms else None,
            last_supported_term=terms[-1] if terms else None,
            mapping_status=mapping.status,
            relationship_type=mapping.relationship_type,
            owning_academic_unit_id=mapping.owning_academic_unit_id,
            owning_academic_unit_name=mapping.owning_academic_unit_name,
            analytical_academic_unit_id=mapping.analytical_academic_unit_id,
            analytical_academic_unit_name=mapping.analytical_academic_unit_name,
            academic_unit_id=mapping.academic_unit_id,
            academic_unit_name=mapping.academic_unit_name,
            formal_unit_type=mapping.formal_unit_type,
            operational_roles=mapping.operational_roles,
            authoritative_source=mapping.mapping_source,
            authoritative_source_type=mapping.authoritative_source_type,
            mapping_method=mapping.mapping_method,
            mapping_rule=mapping.mapping_rule,
            confidence=mapping.confidence,
            review_status=mapping.review_status,
            rationale=mapping.rationale,
            evidence_summary=mapping.evidence,
        )


def compare_subject_mapping_reports(
    old: Mapping[str, Any], new: Mapping[str, Any]
) -> SubjectMappingComparison:
    old_rows = {item["subject_code"]: item for item in old.get("subject_inventory") or ()}
    new_rows = {item["subject_code"]: item for item in new.get("subject_inventory") or ()}
    old_classified = {code for code, row in old_rows.items() if _dict_workforce(row)}
    new_classified = {code for code, row in new_rows.items() if _dict_workforce(row)}
    shared = set(old_rows) & set(new_rows)
    changed_units = _changed(shared, old_rows, new_rows, "academic_unit_id")
    changed_status = _changed(shared, old_rows, new_rows, "mapping_status")
    changed_source = _changed(shared, old_rows, new_rows, "authoritative_source")
    old_ambiguous = {code for code, row in old_rows.items() if row.get("mapping_status") == "ambiguous"}
    new_ambiguous = {code for code, row in new_rows.items() if row.get("mapping_status") == "ambiguous"}
    newly_unmapped = tuple(sorted(
        code for code in shared
        if old_rows[code].get("mapping_status") != "unmapped"
        and new_rows[code].get("mapping_status") == "unmapped"
    ))
    old_coverage = old.get("coverage") or {}
    new_coverage = new.get("coverage") or {}
    result = SubjectMappingComparison(
        old_registry_fingerprint=str(old.get("registry_fingerprint") or ""),
        new_registry_fingerprint=str(new.get("registry_fingerprint") or ""),
        newly_mapped_subjects=tuple(sorted(new_classified - old_classified)),
        changed_unit_subjects=changed_units,
        changed_status_subjects=changed_status,
        changed_source_subjects=changed_source,
        newly_ambiguous_subjects=tuple(sorted(new_ambiguous - old_ambiguous)),
        resolved_ambiguities=tuple(sorted(old_ambiguous - new_ambiguous)),
        newly_unmapped_subjects=newly_unmapped,
        observation_coverage_change_percentage_points=round(
            float(new_coverage.get("observation_level_coverage_percent") or 0)
            - float(old_coverage.get("observation_level_coverage_percent") or 0), 6
        ),
        subject_coverage_change_percentage_points=round(
            float(new_coverage.get("subject_code_level_coverage_percent") or 0)
            - float(old_coverage.get("subject_code_level_coverage_percent") or 0), 6
        ),
        semantic_changes=False,
    )
    semantic = any((
        result.old_registry_fingerprint != result.new_registry_fingerprint,
        result.newly_mapped_subjects, result.changed_unit_subjects,
        result.changed_status_subjects, result.changed_source_subjects,
        result.newly_ambiguous_subjects, result.resolved_ambiguities,
        result.newly_unmapped_subjects,
        result.observation_coverage_change_percentage_points,
        result.subject_coverage_change_percentage_points,
    ))
    return SubjectMappingComparison(**{**asdict(result), "semantic_changes": semantic})


def _ambiguous_mapping(subject, mappings):
    from app.reasoning.academic_unit_mapping import AcademicUnitMappingResult
    candidates = tuple(sorted({item.academic_unit_id for item in mappings if item.academic_unit_id}))
    return AcademicUnitMappingResult(
        subject_code=subject, status="ambiguous", subject_display_name=None,
        owning_academic_unit_id=None, owning_academic_unit_name=None,
        analytical_academic_unit_id=None, analytical_academic_unit_name=None,
        formal_unit_type=None, operational_roles=(), relationship_type=None,
        mapping_source=None, authoritative_source_type=None, mapping_method=None,
        mapping_rule=None, confidence=None,
        rationale="Mapping varies across effective terms or competing rules.",
        review_status="requires_review", candidate_unit_ids=candidates,
    )


def _value(item, name, default=None):
    return item.get(name, default) if isinstance(item, Mapping) else getattr(item, name, default)


def _canonical_instructor(value):
    text = " ".join(value.casefold().split())
    if "," in text:
        last, first = (" ".join(part.split()) for part in text.split(",", 1))
        if first and last:
            text = f"{first} {last}"
    return re.sub(r"\s+", " ", text).strip()


def _percent(numerator, denominator):
    return round(100.0 * numerator / denominator, 6) if denominator else 0.0


def _is_governed_classification(row):
    return row.review_status == "governed" and row.mapping_status in (
        WORKFORCE_MAPPING_STATUSES | CLASSIFIED_NON_WORKFORCE_STATUSES
    )


def _dict_governed(row):
    return row.get("review_status") == "governed" and row.get("mapping_status") in (
        WORKFORCE_MAPPING_STATUSES | CLASSIFIED_NON_WORKFORCE_STATUSES
    )


def _dict_workforce(row):
    return row.get("review_status") == "governed" and row.get("mapping_status") in WORKFORCE_MAPPING_STATUSES


def _review_priority_key(item):
    recency = academic_term_sort_key(item.last_supported_term) if item.last_supported_term else ()
    inverted_recency = tuple(-value if isinstance(value, int) else value for value in recency)
    return (-item.course_offering_count, -item.term_count, -item.distinct_instructor_count, inverted_recency, item.subject_code)


def _changed(shared, old_rows, new_rows, field):
    return tuple(sorted(code for code in shared if old_rows[code].get(field) != new_rows[code].get(field)))


def _fingerprint(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "CLASSIFIED_NON_WORKFORCE_STATUSES", "ScheduleSubjectInventoryRow",
    "ScheduleSubjectMappingInventoryService", "ScheduleSubjectMappingReport",
    "SubjectMappingComparison", "SubjectMappingCoverage",
    "SubjectReviewPriority", "WORKFORCE_MAPPING_STATUSES",
    "compare_subject_mapping_reports",
]
