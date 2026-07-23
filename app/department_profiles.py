"""Deterministic department profiles derived from governed workforce and evidence."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping

from app.academic_terms import academic_term_order, academic_term_sort_key
from app.faculty_appointments import FacultyAppointmentObservationService
from app.faculty_identity import FacultyIdentityService
from app.institutional_units import AcademicUnitRegistry
from app.reasoning.academic_unit_mapping import AcademicUnitMappingService
from app.subject_ownership import SubjectOwnershipRegistry


ALGORITHM = "iso_department_profile_builder"
ALGORITHM_VERSION = "1.0"


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DepartmentProfile:
    department_profile_id: str
    academic_unit_id: str
    department_name: str
    parent_academic_unit_id: str | None
    parent_academic_unit_name: str | None
    as_of_date: str
    workforce_policy_id: str
    analytical_workforce_fingerprint: str
    analytical_workforce_count: int
    faculty_identity_ids: tuple[str, ...]
    faculty_members: tuple[Mapping[str, Any], ...]
    counts_by_published_rank: Mapping[str, int]
    faculty_with_administrative_roles_count: int
    faculty_with_recent_teaching_count: int
    faculty_without_recent_teaching_count: int
    teaching_assignment_count: int
    distinct_instructors_observed: int
    distinct_terms: tuple[str, ...]
    earliest_observed_term: str | None
    latest_observed_term: str | None
    governed_subject_prefixes: tuple[str, ...]
    courses_taught: tuple[str, ...]
    section_count: int
    enrollment_total: int | None
    student_credit_hours: float | None
    home_faculty_instruction: Mapping[str, Any]
    department_owned_instruction: Mapping[str, Any]
    cross_unit_instruction: Mapping[str, Any]
    recent_academic_year_summary: Mapping[str, Any] | None
    term_summaries: tuple[Mapping[str, Any], ...]
    evidence_summary: Mapping[str, Any]
    evidence_fitness: tuple[str, ...]
    known_limitations: tuple[str, ...]
    deterministic_fingerprint: str

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class DepartmentProfileResult:
    profiles: tuple[DepartmentProfile, ...]
    summary: Mapping[str, Any]
    deterministic_fingerprint: str


class DepartmentProfileBuilder:
    def __init__(self, units=None, subjects=None):
        self.units = units or AcademicUnitRegistry.load()
        self.subjects = subjects or SubjectOwnershipRegistry.load()
        self.mapper = AcademicUnitMappingService(self.units, self.subjects)

    def build(self, objects: Iterable[Mapping[str, Any]], decisions, population):
        objects = tuple(objects)
        included = tuple(item for item in decisions if item["workforce_disposition"] == "include")
        if population["workforce_review_required_count"] or population["department_assignment_review_required_count"]:
            raise ValueError("Department profiles require completed workforce and department review")
        home = {item["faculty_identity_id"]: item["analytical_academic_unit_id"] for item in included}
        if any(not unit_id for unit_id in home.values()):
            raise ValueError("Every included workforce identity requires an analytical unit")
        if len(home) != len(included):
            raise ValueError("Duplicate included workforce identity")

        identities = {item.identity_id: item for item in FacultyIdentityService().audit(objects).identities}
        appointment_audit = FacultyAppointmentObservationService().audit(objects)
        faculty = _group(appointment_audit.faculty_appointments)
        admin = _group(appointment_audit.administrative_appointments)
        schedule_identity = {
            source.knowledge_object_id: identity.identity_id
            for identity in identities.values()
            for source in identity.source_observations if source.source_system == "schedule"
        }
        schedules = tuple(item for item in objects if item.get("object_type") == "course_offering_observation")
        schedule_rows = tuple(_schedule_row(item, schedule_identity, home, self.mapper) for item in schedules)
        represented_units = set(home.values())
        represented_units.update(
            row["owned_unit_id"] for row in schedule_rows
            if row["owned_unit_id"] and self.units.get(row["owned_unit_id"]).is_department_workforce_unit
        )
        departments = {}
        for unit_id in represented_units:
            unit = self.units.get(unit_id)
            if not unit.is_department_workforce_unit:
                raise ValueError(f"Non-department unit entered department profiles: {unit_id}")
            departments[unit_id] = unit
        complete_year = _most_recent_complete_academic_year(schedule_rows)
        profiles = tuple(sorted((
            self._profile(unit, included, identities, faculty, admin, schedule_rows,
                          population, complete_year)
            for unit in departments.values()
        ), key=lambda item: item.academic_unit_id))
        profile_members = [identity_id for profile in profiles for identity_id in profile.faculty_identity_ids]
        if len(profile_members) != len(set(profile_members)):
            raise ValueError("An included identity appears in multiple department profiles")
        if set(profile_members) != set(home):
            raise ValueError("Department profiles do not contain every included identity exactly once")
        total = sum(item.analytical_workforce_count for item in profiles)
        if total != population["workforce_included_count"]:
            raise ValueError("Department workforce totals do not reconcile")
        summary = {
            "algorithm": ALGORITHM, "algorithm_version": ALGORITHM_VERSION,
            "as_of_date": population["as_of_date"],
            "analytical_workforce_fingerprint": population["deterministic_fingerprint"],
            "department_profile_count": len(profiles),
            "analytical_workforce_count": population["workforce_included_count"],
            "department_workforce_total": total,
            "workforce_reconciled": True,
            "analytical_workforce_denominator_ready": True,
            "authoritative_hr_denominator_ready": False,
            "teaching_assignment_count": sum(item.teaching_assignment_count for item in profiles),
            "departments_with_enrollment": sum(item.enrollment_total is not None for item in profiles),
            "departments_with_sch": sum(item.student_credit_hours is not None for item in profiles),
            "most_recent_complete_academic_year": complete_year,
            "most_recent_observed_term": _latest_term(schedule_rows),
        }
        digest = _fingerprint({"summary": summary, "profiles": [item.to_dict() for item in profiles]})
        return DepartmentProfileResult(profiles, summary, digest)

    def _profile(self, unit, included, identities, faculty, admin, rows, population, complete_year):
        members = tuple(sorted((item for item in included if item["analytical_academic_unit_id"] == unit.unit_id), key=lambda item: item["faculty_identity_id"]))
        member_ids = {item["faculty_identity_id"] for item in members}
        home_rows = tuple(row for row in rows if row["instructor_identity_id"] in member_ids)
        owned_rows = tuple(row for row in rows if row["owned_unit_id"] == unit.unit_id)
        home_outside = tuple(row for row in home_rows if row["owned_unit_id"] != unit.unit_id)
        outside_owned = tuple(row for row in owned_rows if row["instructor_identity_id"] not in member_ids)
        parent = self.units.parent_of(unit)
        faculty_members, rank_counts, admin_count, recent_count = [], Counter(), 0, 0
        for item in members:
            identity_id = item["faculty_identity_id"]
            current_faculty = tuple(obs for obs in faculty.get(identity_id, ()) if obs.source_system == "faculty_directory" and obs.temporal_label == population["as_of_date"])
            current_admin = tuple(obs for obs in admin.get(identity_id, ()) if obs.source_system == "faculty_directory" and obs.temporal_label == population["as_of_date"])
            ranks = sorted({rank for obs in current_faculty for rank in obs.normalized_ranks})
            titles = sorted({title for obs in current_faculty for title in obs.published_titles})
            roles = sorted({obs.normalized_administrative_role for obs in current_admin})
            rank_counts.update(ranks or ("published_title_unclassified",))
            admin_count += bool(roles)
            recent = bool(item["teaching_assignment_summary"]["recent_assignment_count"])
            recent_count += recent
            faculty_members.append({
                "faculty_identity_id": identity_id,
                "display_name": identities[identity_id].display_name,
                "published_titles": titles, "normalized_ranks": ranks,
                "administrative_roles": roles, "recent_teaching_observed": recent,
            })
        subjects = tuple(sorted({record.subject_code for record in self.subjects.records if record.analytical_academic_unit_id == unit.unit_id and record.review_status == "governed"}))
        owned_sections = _unique_sections(owned_rows)
        term_summaries = tuple(_summarize_rows(term, tuple(row for row in owned_sections if row["term"] == term)) for term in sorted({row["term"] for row in owned_sections}, key=academic_term_sort_key))
        recent_summary = _summarize_rows(complete_year, tuple(row for row in owned_sections if _academic_year(row["term"]) == complete_year)) if complete_year else None
        enrollment = _explicit_total(owned_sections, "enrollment")
        sch = _sch_total(owned_sections)
        fitness = {
            "governed_workforce_membership_complete", "governed_department_assignment_complete",
            "current_directory_supported", "public_evidence_analytical_baseline",
            "not_authoritative_hr_roster", "subject_ownership_governed",
        }
        limitations = {"analytical baseline is not an authoritative HR roster", "teaching assignments do not represent faculty effort or workload"}
        if owned_rows:
            fitness.add("teaching_history_available")
        if recent_count:
            fitness.add("recent_teaching_observed")
        if len(members) - recent_count:
            fitness.add("no_recent_teaching_observed")
        if admin_count:
            fitness.add("administrative_role_observed")
        if enrollment is None:
            fitness.add("enrollment_incomplete")
            limitations.add("some or all department-owned sections lack explicit enrollment")
        else:
            fitness.add("enrollment_available")
        if sch is not None:
            fitness.add("sch_derived_from_explicit_credits_and_enrollment")
        else:
            limitations.add("SCH is unavailable where credits or enrollment are missing")
        semantic = {
            "academic_unit_id": unit.unit_id, "department_name": unit.published_name,
            "parent_academic_unit_id": parent.unit_id if parent else None,
            "parent_academic_unit_name": parent.published_name if parent else None,
            "as_of_date": population["as_of_date"], "workforce_policy_id": population["policy_id"],
            "analytical_workforce_fingerprint": population["deterministic_fingerprint"],
            "analytical_workforce_count": len(members),
            "faculty_identity_ids": tuple(sorted(member_ids)), "faculty_members": tuple(faculty_members),
            "counts_by_published_rank": dict(sorted(rank_counts.items())),
            "faculty_with_administrative_roles_count": admin_count,
            "faculty_with_recent_teaching_count": recent_count,
            "faculty_without_recent_teaching_count": len(members) - recent_count,
            "teaching_assignment_count": len(owned_rows),
            "distinct_instructors_observed": len({row["instructor_identity_id"] or row["instructor_raw"] for row in owned_rows if row["instructor_identity_id"] or row["instructor_raw"]}),
            "distinct_terms": tuple(sorted({row["term"] for row in owned_rows}, key=academic_term_sort_key)),
            "earliest_observed_term": _earliest_term(owned_rows), "latest_observed_term": _latest_term(owned_rows),
            "governed_subject_prefixes": subjects,
            "courses_taught": tuple(sorted({row["course_code"] for row in owned_rows if row["course_code"]})),
            "section_count": len(owned_sections), "enrollment_total": enrollment,
            "student_credit_hours": sch,
            "home_faculty_instruction": _activity_summary(home_rows),
            "department_owned_instruction": _activity_summary(owned_rows),
            "cross_unit_instruction": {
                "home_faculty_outside_department": _activity_summary(home_outside),
                "department_subjects_taught_by_outside_faculty": _activity_summary(outside_owned),
            },
            "recent_academic_year_summary": recent_summary, "term_summaries": term_summaries,
            "evidence_summary": {
                "faculty_identity_count": len(members), "appointment_observation_count": sum(len(faculty.get(identity_id, ())) for identity_id in member_ids),
                "administrative_observation_count": sum(len(admin.get(identity_id, ())) for identity_id in member_ids),
                "schedule_observation_count": len({row["observation_id"] for row in (*home_rows, *owned_rows)}),
                "subject_registry_fingerprint": self.subjects.fingerprint,
            },
            "evidence_fitness": tuple(sorted(fitness)), "known_limitations": tuple(sorted(limitations)),
        }
        digest = _fingerprint(semantic)
        return DepartmentProfile(
            department_profile_id=f"department_profile:{unit.unit_id.split(':', 1)[-1]}:{digest[:16]}",
            deterministic_fingerprint=digest, **semantic,
        )


def _group(values):
    result = defaultdict(list)
    for item in values:
        if item.faculty_identity_id:
            result[item.faculty_identity_id].append(item)
    return {key: tuple(value) for key, value in result.items()}


def _schedule_row(item, schedule_identity, home, mapper):
    subject = str(item.get("subject") or str(item.get("course_code") or "").split()[0]).upper()
    term = str(item.get("academic_term") or "")
    identity_id = schedule_identity.get(str(item.get("id") or ""))
    mapping = mapper.map_subject(subject, term)
    owned = mapping.analytical_academic_unit_id if mapping.review_status == "governed" else None
    return {
        "observation_id": str(item.get("id") or item.get("observation_id") or ""),
        "section_key": _section_key(item), "term": term, "subject": subject,
        "course_code": str(item.get("course_code") or ""),
        "instructor_identity_id": identity_id, "instructor_raw": item.get("instructor_raw") or item.get("instructor_name"),
        "home_unit_id": home.get(identity_id), "owned_unit_id": owned,
        "credits": item.get("credits"), "enrollment": item.get("enrollment"),
    }


def _section_key(item):
    return "|".join(str(item.get(key) or "") for key in ("academic_term", "crn", "subject", "course_code", "section"))


def _unique_sections(rows):
    values = {}
    for row in sorted(rows, key=lambda item: (item["section_key"], item["observation_id"])):
        values.setdefault(row["section_key"], row)
    return tuple(values.values())


def _activity_summary(rows):
    sections = _unique_sections(rows)
    return {
        "teaching_assignment_count": len(rows), "section_count": len(sections),
        "distinct_instructor_count": len({row["instructor_identity_id"] or row["instructor_raw"] for row in rows if row["instructor_identity_id"] or row["instructor_raw"]}),
        "subject_prefixes": sorted({row["subject"] for row in rows if row["subject"]}),
        "enrollment_total": _explicit_total(sections, "enrollment"),
        "student_credit_hours": _sch_total(sections),
    }


def _explicit_total(rows, field):
    if not rows or any(
        not isinstance(row[field], (int, float)) or isinstance(row[field], bool)
        or row[field] < 0 for row in rows
    ):
        return None
    return sum(row[field] for row in rows)


def _sch_total(rows):
    if not rows or any(
        not isinstance(row["credits"], (int, float))
        or isinstance(row["credits"], bool) or row["credits"] < 0
        or not isinstance(row["enrollment"], int)
        or isinstance(row["enrollment"], bool) or row["enrollment"] < 0
        for row in rows
    ):
        return None
    return sum(float(row["credits"]) * int(row["enrollment"]) for row in rows)


def _summarize_rows(label, rows):
    return {"period": label, **_activity_summary(rows)}


def _academic_year(term):
    order = academic_term_order(term)
    if not order.supported:
        return None
    start = order.year if order.period == "fall" else order.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def _most_recent_complete_academic_year(rows):
    periods = defaultdict(set)
    for row in rows:
        order = academic_term_order(row["term"])
        year = _academic_year(row["term"])
        if order.supported and year:
            periods[year].add(order.period)
    complete = [year for year, values in periods.items() if {"fall", "spring"}.issubset(values)]
    return sorted(complete)[-1] if complete else None


def _earliest_term(rows):
    values = sorted({row["term"] for row in rows if row["term"]}, key=academic_term_sort_key)
    return values[0] if values else None


def _latest_term(rows):
    values = sorted({row["term"] for row in rows if row["term"]}, key=academic_term_sort_key)
    return values[-1] if values else None


__all__ = ["DepartmentProfile", "DepartmentProfileBuilder", "DepartmentProfileResult"]
