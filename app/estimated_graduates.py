"""Estimated graduates derived from governed capstones and schedule enrollment."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from app.academic_terms import academic_term_order
from app.institutional_units import AcademicUnitRegistry
from app.undergraduate_major_capstones import (
    MajorCapstoneRequirement,
    UndergraduateMajorCapstoneRegistry,
)
from app.undergraduate_majors import UndergraduateMajorRegistry


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def _course_key(value: str) -> tuple[str, str] | None:
    parts = str(value).upper().split()
    if len(parts) < 2:
        return None
    match = re.fullmatch(r"(\d+)[A-Z]*", parts[-1])
    return (parts[0], match.group(1)) if match else None


def _academic_year(term: str) -> str | None:
    order = academic_term_order(term)
    if not order.supported:
        return None
    start = order.year if order.period == "fall" else order.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


@dataclass(frozen=True)
class EstimationPlan:
    major_id: str
    status: str
    course_keys: tuple[tuple[str, str], ...]
    method: str
    confidence: str
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class EstimatedGraduatesResult:
    major_rows: tuple[Mapping[str, Any], ...]
    department_rows: tuple[Mapping[str, Any], ...]
    summary: Mapping[str, Any]
    deterministic_fingerprint: str


class EstimatedGraduatesBuilder:
    """Build a conservative capstone-enrollment proxy without student records."""

    def build(
        self,
        objects: Iterable[Mapping[str, Any]],
        major_registry: UndergraduateMajorRegistry,
        capstone_registry: UndergraduateMajorCapstoneRegistry,
        unit_registry: AcademicUnitRegistry,
    ) -> EstimatedGraduatesResult:
        current_majors = {
            item.major_id: item
            for item in major_registry.majors
            if item.status == "current"
        }
        plans = self._plans(capstone_registry)
        sections = self._sections(objects)
        years = tuple(sorted({
            year for item in sections
            if (year := _academic_year(str(item["academic_term"])))
        }))
        units = {item.unit_id: item for item in unit_registry.units}
        major_rows = []
        for year in years:
            for major_id in sorted(current_majors):
                major = current_majors[major_id]
                plan = plans[major_id]
                owner = units.get(major.owning_academic_unit_id or "")
                matched = tuple(
                    item for item in sections
                    if _academic_year(str(item["academic_term"])) == year
                    and (item["subject"], item["course_number"]) in plan.course_keys
                )
                row = self._major_row(
                    year, major, owner, plan, matched,
                )
                major_rows.append(row)
        department_rows = self._department_rows(
            tuple(major_rows), current_majors, units, years,
        )
        summary = {
            "schema_version": 1,
            "observable_id": "iso.estimated_graduates_by_major.capstone_enrollment.v1",
            "academic_year_definition": (
                "Fall starts the academic year; spring, Maymester, and summer "
                "belong to the preceding fall year."
            ),
            "academic_years": list(years),
            "current_major_count": len(current_majors),
            "schedule_section_count": len(sections),
            "estimable_major_count": sum(
                plan.status == "estimable" for plan in plans.values()
            ),
            "excluded_major_count": sum(
                plan.status != "estimable" for plan in plans.values()
            ),
            "plan_status_counts": dict(sorted(Counter(
                plan.status for plan in plans.values()
            ).items())),
            "method_counts": dict(sorted(Counter(
                plan.method for plan in plans.values()
            ).items())),
            "unsupported_assumptions": [
                "Schedule enrollment contains no student-major identifier.",
                "Shared capstone enrollment cannot be allocated among majors.",
                "Capstone enrollment is not proof that every enrollee graduates "
                "in the same academic year.",
                "Absence of an observed capstone section is not treated as zero "
                "graduates.",
                "Course withdrawals, failures, repeated capstones, and delayed "
                "graduation are not observable.",
            ],
        }
        semantic = {
            "summary": summary,
            "major_rows": major_rows,
            "department_rows": department_rows,
        }
        return EstimatedGraduatesResult(
            major_rows=tuple(major_rows),
            department_rows=tuple(department_rows),
            summary=summary,
            deterministic_fingerprint=_fingerprint(semantic),
        )

    def _plans(
        self, registry: UndergraduateMajorCapstoneRegistry
    ) -> dict[str, EstimationPlan]:
        candidates = {
            item.major_id: self._candidate_keys(item)
            for item in registry.requirements
        }
        course_users: dict[tuple[str, str], set[str]] = defaultdict(set)
        for major_id, keys in candidates.items():
            for key in keys:
                course_users[key].add(major_id)
        return {
            item.major_id: self._plan(item, candidates[item.major_id], course_users)
            for item in registry.requirements
        }

    @staticmethod
    def _candidate_keys(
        item: MajorCapstoneRequirement,
    ) -> tuple[tuple[str, str], ...]:
        keys = []
        for pathway in item.pathways:
            values = [
                key for value in pathway.course_ids
                if (key := _course_key(value))
            ]
            if pathway.requirement_type == "required_capstone_sequence" and values:
                keys.append(values[-1])
            else:
                keys.extend(values)
        return tuple(sorted(set(keys)))

    @staticmethod
    def _plan(
        item: MajorCapstoneRequirement,
        candidates: tuple[tuple[str, str], ...],
        course_users: Mapping[tuple[str, str], set[str]],
    ) -> EstimationPlan:
        if item.requirement_type == "no_identifiable_capstone":
            return EstimationPlan(
                item.major_id, "excluded_no_identifiable_capstone", (),
                "excluded", "unavailable",
                ("The governed registry identifies no required capstone.",),
            )
        if item.requirement_type == "unresolved" or any(
            pathway.requirement_type in {
                "unresolved", "no_identifiable_capstone",
            }
            for pathway in item.pathways
        ):
            return EstimationPlan(
                item.major_id, "excluded_unresolved_pathway", (),
                "excluded", "unavailable",
                ("At least one governed pathway lacks an estimable capstone.",),
            )
        unique = tuple(
            key for key in candidates if len(course_users[key]) == 1
        )
        shared = tuple(
            key for key in candidates if len(course_users[key]) > 1
        )
        if item.requirement_type == "multiple_required_capstones":
            if len(unique) == 1:
                return EstimationPlan(
                    item.major_id, "estimable", unique,
                    "unique_major_specific_required_capstone", "medium",
                    (
                        "Uses the one required capstone unique to this major "
                        "and does not add the shared degree capstone.",
                    ),
                )
            return EstimationPlan(
                item.major_id, "excluded_shared_capstone", (),
                "excluded", "unavailable",
                ("No required capstone uniquely identifies this major.",),
            )
        if shared:
            return EstimationPlan(
                item.major_id, "excluded_shared_capstone", (),
                "excluded", "unavailable",
                (
                    "One or more capstone courses are shared with another "
                    "governed major and schedule enrollment has no major field.",
                ),
            )
        if not candidates:
            return EstimationPlan(
                item.major_id, "excluded_unresolved_pathway", (),
                "excluded", "unavailable",
                ("No schedule-matchable capstone course is governed.",),
            )
        if item.requirement_type == "required_capstone_sequence":
            method = "terminal_course_in_required_sequence"
        elif item.requirement_type in {
            "alternative_capstone_choices", "thesis_or_seminar_options",
        }:
            method = "sum_governed_mutually_exclusive_alternatives"
        else:
            method = "required_capstone_enrollment"
        confidence = min(
            (
                pathway.evidence.evidence_confidence
                for pathway in item.pathways
            ),
            key={"low": 0, "medium": 1, "high": 2}.get,
        )
        limitations = (
            "Enrollment is a proxy for graduates, not a degree-conferral fact.",
        )
        return EstimationPlan(
            item.major_id, "estimable", candidates, method, confidence,
            limitations,
        )

    @staticmethod
    def _sections(
        objects: Iterable[Mapping[str, Any]],
    ) -> tuple[dict[str, Any], ...]:
        grouped: dict[tuple[str, ...], list[Mapping[str, Any]]] = defaultdict(list)
        for item in objects:
            if item.get("object_type") != "course_offering_observation":
                continue
            subject = str(
                item.get("subject")
                or str(item.get("course_code") or "").split()[0]
            ).strip().upper()
            number = str(item.get("course_number") or "").strip().upper()
            match = re.fullmatch(r"(\d+)[A-Z]*", number)
            if not subject or not match:
                continue
            key = tuple(str(item.get(field) or "") for field in (
                "academic_term", "crn", "subject", "course_code", "section",
            ))
            grouped[key].append(item)
        rows = []
        for key in sorted(grouped):
            values = grouped[key]
            enrollments = {
                item.get("enrollment") for item in values
                if isinstance(item.get("enrollment"), int)
                and not isinstance(item.get("enrollment"), bool)
                and item.get("enrollment") >= 0
            }
            first = values[0]
            rows.append({
                "section_key": "|".join(key),
                "academic_term": str(first.get("academic_term") or ""),
                "subject": str(
                    first.get("subject")
                    or str(first.get("course_code") or "").split()[0]
                ).strip().upper(),
                "course_number": re.match(
                    r"(\d+)", str(first.get("course_number") or "")
                ).group(1),
                "enrollment": (
                    next(iter(enrollments)) if len(enrollments) == 1 else None
                ),
                "enrollment_conflict": len(enrollments) > 1,
            })
        return tuple(rows)

    @staticmethod
    def _major_row(year, major, owner, plan, matched):
        enrollments = [item["enrollment"] for item in matched]
        if plan.status != "estimable":
            status = plan.status
            estimate = None
        elif not matched:
            status = "not_observed"
            estimate = None
        elif any(value is None for value in enrollments):
            status = "incomplete_enrollment"
            estimate = None
        else:
            status = "estimated"
            estimate = sum(enrollments)
        return {
            "academic_year": year,
            "major_id": major.major_id,
            "major": major.display_name,
            "owning_academic_unit_id": major.owning_academic_unit_id,
            "owning_academic_unit_name": (
                owner.published_name if owner else None
            ),
            "department_aggregation_eligible": bool(
                owner and owner.is_department_workforce_unit
            ),
            "estimation_status": status,
            "estimated_graduates": estimate,
            "capstone_section_count": len(matched),
            "capstone_enrollment_observed": (
                sum(value for value in enrollments if value is not None)
                if matched else None
            ),
            "estimation_course_ids": [
                f"{subject} {number}" for subject, number in plan.course_keys
            ],
            "estimation_method": plan.method,
            "confidence": plan.confidence,
            "limitations": list(plan.limitations),
        }

    @staticmethod
    def _department_rows(major_rows, majors, units, years):
        result = []
        department_ids = sorted({
            major.owning_academic_unit_id
            for major in majors.values()
            if major.owning_academic_unit_id
            and units.get(major.owning_academic_unit_id)
            and units[major.owning_academic_unit_id].is_department_workforce_unit
        })
        for year in years:
            for unit_id in department_ids:
                rows = tuple(
                    item for item in major_rows
                    if item["academic_year"] == year
                    and item["owning_academic_unit_id"] == unit_id
                )
                estimated = tuple(
                    item for item in rows
                    if item["estimation_status"] == "estimated"
                )
                result.append({
                    "academic_year": year,
                    "academic_unit_id": unit_id,
                    "department": units[unit_id].published_name,
                    "governed_major_count": len(rows),
                    "estimated_major_count": len(estimated),
                    "excluded_or_unobserved_major_count": (
                        len(rows) - len(estimated)
                    ),
                    "estimated_graduates": (
                        sum(item["estimated_graduates"] for item in estimated)
                        if estimated else None
                    ),
                    "estimate_complete_for_department": (
                        bool(rows) and len(estimated) == len(rows)
                    ),
                    "included_major_ids": [
                        item["major_id"] for item in estimated
                    ],
                    "excluded_or_unobserved_major_ids": [
                        item["major_id"] for item in rows
                        if item["estimation_status"] != "estimated"
                    ],
                })
        return tuple(result)


__all__ = [
    "EstimatedGraduatesBuilder",
    "EstimatedGraduatesResult",
    "EstimationPlan",
]
