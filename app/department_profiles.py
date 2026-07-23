"""Deterministic department profiles derived from governed workforce and evidence."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from app.academic_terms import academic_term_order, academic_term_sort_key
from app.faculty_appointments import FacultyAppointmentObservationService
from app.faculty_identity import FacultyIdentityService
from app.institutional_units import AcademicUnitRegistry
from app.reasoning.academic_unit_mapping import AcademicUnitMappingService
from app.subject_ownership import SubjectOwnershipRegistry


ALGORITHM = "iso_department_profile_builder"
ALGORITHM_VERSION = "1.2"


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
    sections_with_enrollment: int
    sections_with_explicit_credits: int
    sch_ready_section_count: int
    sch_ready_section_percent: float
    enrollment_total: int | None
    student_credit_hours: float | None
    enrollment_complete: bool
    sch_complete: bool
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
        raw_schedule_rows = tuple(_schedule_row(item, schedule_identity, home, self.mapper) for item in schedules)
        schedule_rows, sch_repairs = _repair_sch_rows(raw_schedule_rows)
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
            "total_discovered_teaching_assignments": len(schedule_rows),
            "teaching_assignments_mapped_through_subject_ownership": sum(bool(row["owned_unit_id"]) for row in schedule_rows),
            "teaching_assignments_linked_through_home_faculty": sum(bool(row["home_unit_id"]) for row in schedule_rows),
            "unmapped_teaching_assignments": sum(not row["owned_unit_id"] for row in schedule_rows),
            "subject_prefix_count": len({row["subject"] for row in schedule_rows if row["subject"]}),
            "governed_subject_prefix_count": len({row["subject"] for row in schedule_rows if row["owned_unit_id"]}),
            "unmapped_subject_prefixes": sorted({
                row["subject"] for row in schedule_rows
                if row["subject"] and not row["owned_unit_id"]
            }),
            "subject_ownership_complete": not any(
                row["subject"] and not row["owned_unit_id"] for row in schedule_rows
            ),
            "departments_with_teaching_history": sum(bool(item.teaching_assignment_count) for item in profiles),
            "departments_with_enrollment": sum(item.sections_with_enrollment > 0 for item in profiles),
            "departments_with_complete_enrollment": sum(item.enrollment_complete for item in profiles),
            "departments_with_sch": sum(item.sch_ready_section_count > 0 for item in profiles),
            "departments_with_complete_sch": sum(item.sch_complete for item in profiles),
            "most_recent_complete_academic_year": complete_year,
            "most_recent_observed_term": _latest_term(schedule_rows),
            "sch_repair_count": len(sch_repairs),
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
        # Department-level instructional totals are ownership totals. Home
        # faculty activity is a separate descriptive axis and must never be
        # used as a fallback for absent subject governance.
        activity_rows = owned_rows
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
        activity_sections = _unique_sections(activity_rows)
        coverage = _section_coverage(activity_sections)
        term_summaries = tuple(_summarize_rows(term, tuple(row for row in activity_sections if row["term"] == term)) for term in sorted({row["term"] for row in activity_sections}, key=academic_term_sort_key))
        recent_summary = _summarize_rows(complete_year, tuple(row for row in activity_sections if _academic_year(row["term"]) == complete_year)) if complete_year else None
        fitness = {
            "governed_workforce_membership_complete", "governed_department_assignment_complete",
            "current_directory_supported", "public_evidence_analytical_baseline",
            "not_authoritative_hr_roster",
        }
        limitations = {"analytical baseline is not an authoritative HR roster", "teaching assignments do not represent faculty effort or workload"}
        if activity_rows:
            fitness.add("teaching_history_available")
        if subjects:
            fitness.add("subject_ownership_governed")
        else:
            limitations.add("no governed instructional subject is assigned to this department")
        if recent_count:
            fitness.add("recent_teaching_observed")
        if len(members) - recent_count:
            fitness.add("no_recent_teaching_observed")
        if admin_count:
            fitness.add("administrative_role_observed")
        if not coverage["enrollment_complete"]:
            fitness.add("enrollment_incomplete")
            limitations.add("some department activity sections lack explicit enrollment")
        else:
            fitness.add("enrollment_available")
        if coverage["sch_ready_section_count"]:
            fitness.add("sch_derived_from_explicit_credits_and_enrollment")
        if not coverage["sch_complete"]:
            limitations.add("known SCH is partial where credits or enrollment are missing")
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
            "teaching_assignment_count": len(activity_rows),
            "distinct_instructors_observed": len({row["instructor_identity_id"] or row["instructor_raw"] for row in activity_rows if row["instructor_identity_id"] or row["instructor_raw"]}),
            "distinct_terms": tuple(sorted({row["term"] for row in activity_rows}, key=academic_term_sort_key)),
            "earliest_observed_term": _earliest_term(activity_rows), "latest_observed_term": _latest_term(activity_rows),
            "governed_subject_prefixes": subjects,
            "courses_taught": tuple(sorted({row["course_code"] for row in activity_rows if row["course_code"]})),
            "section_count": coverage["section_count"],
            "sections_with_enrollment": coverage["sections_with_enrollment"],
            "sections_with_explicit_credits": coverage["sections_with_explicit_credits"],
            "sch_ready_section_count": coverage["sch_ready_section_count"],
            "sch_ready_section_percent": coverage["sch_ready_section_percent"],
            "enrollment_total": coverage["known_enrollment"],
            "student_credit_hours": coverage["known_sch"],
            "enrollment_complete": coverage["enrollment_complete"],
            "sch_complete": coverage["sch_complete"],
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
    subject = str(item.get("subject") or str(item.get("course_code") or "").split()[0]).strip().upper()
    term = str(item.get("academic_term") or "")
    identity_id = schedule_identity.get(str(item.get("id") or ""))
    mapping = mapper.map_subject(subject, term)
    owned = mapping.analytical_academic_unit_id if mapping.review_status == "governed" else None
    return {
        "observation_id": str(item.get("id") or item.get("observation_id") or ""),
        "section_key": _section_key(item), "term": term, "subject": subject,
        "course_code": str(item.get("course_code") or ""),
        "course_number": str(item.get("course_number") or ""),
        "section": str(item.get("section") or ""),
        "course_title": item.get("course_title"),
        "instructional_method": item.get("instructional_method"),
        "status": item.get("status"),
        "notes": item.get("notes"),
        "source_file": item.get("source_file") or (item.get("provenance") or {}).get("source_file"),
        "instructor_identity_id": identity_id, "instructor_raw": item.get("instructor_raw") or item.get("instructor_name"),
        "home_unit_id": home.get(identity_id), "owned_unit_id": owned,
        "original_owner_unit_id": mapping.owning_academic_unit_id,
        "original_owner_name": mapping.owning_academic_unit_name,
        "subject_mapping_status": mapping.status,
        "subject_mapping_review_status": mapping.review_status,
        "credits": item.get("credits"), "enrollment": item.get("enrollment"),
        "credits_raw": item.get("credits_raw"),
        "published_credit_values": tuple(
            (item.get("credits_assertion") or {}).get("published_values") or ()
        ),
        "credit_resolution_method": ((item.get("credits_assertion") or {}).get("resolution") or {}).get("method"),
        "raw_schedule_record": item.get("raw_record"),
        "source_rows": tuple((item.get("provenance") or {}).get("source_rows") or ()),
        "sch_repairs": (),
    }


def _section_key(item):
    return "|".join(str(item.get(key) or "") for key in ("academic_term", "crn", "subject", "course_code", "section"))


def _unique_sections(rows):
    grouped = defaultdict(list)
    for row in sorted(rows, key=lambda item: (item["section_key"], item["observation_id"])):
        grouped[row["section_key"]].append(row)
    return tuple(_merge_section(tuple(grouped[key])) for key in sorted(grouped))


def _merge_section(rows):
    merged = dict(rows[0])
    repairs = set(merged.get("sch_repairs") or ())
    for field in ("enrollment", "credits"):
        values = {row[field] for row in rows if _valid_number(row[field], integer=(field == "enrollment"))}
        if len(values) == 1:
            value = next(iter(values))
            if merged[field] is None:
                merged[field] = value
                repairs.add(f"duplicate_section_{field}")
        elif len(values) > 1:
            merged[field] = None
            repairs.add(f"duplicate_section_{field}_conflict")
    merged["sch_repairs"] = tuple(sorted(repairs))
    merged["duplicate_observation_count"] = len(rows)
    merged["instructors"] = tuple(sorted({str(row["instructor_raw"] or "") for row in rows if row["instructor_raw"]}))
    return merged


def _repair_sch_rows(rows):
    credit_index = defaultdict(set)
    course_history = defaultdict(list)
    for row in rows:
        if _valid_number(row["credits"]):
            course_key = (row["subject"], row["course_number"] or row["course_code"])
            credit_index[(row["term"], *course_key)].add(row["credits"])
            course_history[course_key].append(row)
    repaired, repairs = [], []
    for row in rows:
        value = dict(row)
        key = (row["term"], row["subject"], row["course_number"] or row["course_code"])
        candidates = credit_index[key]
        method = row.get("credit_resolution_method")
        if row["credits"] is None and len(candidates) == 1 and method not in {
            "legitimate_variable_credit", "unresolved_credit_conflict",
        }:
            value["credits"] = next(iter(candidates))
            value["sch_repairs"] = ("course_term_credit_consensus",)
            repairs.append({
                "observation_id": row["observation_id"], "section_key": row["section_key"],
                "field": "credits", "value": value["credits"],
                "method": "course_term_credit_consensus",
                "evidence_key": "|".join(map(str, key)),
            })
        elif row["credits"] is None and method == "unresolved_credit_conflict":
            repair = _historical_credit_revision(row, course_history[
                (row["subject"], row["course_number"] or row["course_code"])
            ])
            if repair is not None:
                value["credits"] = repair["value"]
                value["sch_repairs"] = ("historical_credit_revision_resolution",)
                repairs.append({
                    "observation_id": row["observation_id"],
                    "section_key": row["section_key"],
                    "field": "credits",
                    **repair,
                })
        repaired.append(value)
    return tuple(repaired), tuple(sorted(repairs, key=lambda item: (item["section_key"], item["observation_id"])))


def _published_credit_numbers(row):
    values = row.get("published_credit_values") or ()
    if not values:
        values = re.split(r"\s*\|\s*", str(row.get("credits_raw") or ""))
    parsed = set()
    for raw in values:
        try:
            value = float(str(raw).strip())
        except (TypeError, ValueError):
            continue
        if value > 0:
            parsed.add(value)
    return tuple(sorted(parsed))


def _historical_credit_revision(row, course_history):
    """Resolve a repeated-snapshot conflict around a visible credit revision.

    A repair is allowed only when later, unambiguous observations unanimously
    publish one of exactly two values preserved on the earlier section.  The
    other value is therefore the sole explicit pre-revision assertion; no
    credit value is invented or selected from a course-specific rule.
    """
    published = _published_credit_numbers(row)
    if len(published) != 2:
        return None
    later = tuple(
        item for item in course_history
        if academic_term_sort_key(item["term"]) > academic_term_sort_key(row["term"])
        and _valid_number(item["credits"])
    )
    later_values = {float(item["credits"]) for item in later}
    if len(later_values) != 1:
        return None
    stable_value = next(iter(later_values))
    historical = tuple(value for value in published if value != stable_value)
    if stable_value not in published or len(historical) != 1:
        return None
    support = sorted(later, key=lambda item: (
        academic_term_sort_key(item["term"]), item["observation_id"],
    ))
    return {
        "value": historical[0],
        "method": "historical_credit_revision_resolution",
        "evidence_key": "|".join((
            row["subject"], row["course_number"] or row["course_code"],
            row["term"], support[0]["term"],
        )),
        "published_conflicting_values": list(published),
        "later_stable_credit": stable_value,
        "supporting_term": support[0]["term"],
        "supporting_observation_id": support[0]["observation_id"],
        "notes": (
            "Later unambiguous observations unanimously publish one of two "
            "values preserved on the earlier repeated snapshots; the other "
            "explicit value is retained as the pre-revision credit."
        ),
    }


def _union_rows(*groups):
    values = {}
    for row in (*groups,):
        for item in row:
            key = item["observation_id"] or "|".join((item["section_key"], str(item["instructor_identity_id"] or item["instructor_raw"] or "")))
            values.setdefault(key, item)
    return tuple(values[key] for key in sorted(values))


def _activity_summary(rows):
    sections = _unique_sections(rows)
    coverage = _section_coverage(sections)
    return {
        "teaching_assignment_count": len(rows), "section_count": len(sections),
        "distinct_instructor_count": len({row["instructor_identity_id"] or row["instructor_raw"] for row in rows if row["instructor_identity_id"] or row["instructor_raw"]}),
        "subject_prefixes": sorted({row["subject"] for row in rows if row["subject"]}),
        "sections_with_enrollment": coverage["sections_with_enrollment"],
        "sections_with_explicit_credits": coverage["sections_with_explicit_credits"],
        "sch_ready_section_count": coverage["sch_ready_section_count"],
        "sch_ready_section_percent": coverage["sch_ready_section_percent"],
        "enrollment_total": coverage["known_enrollment"],
        "student_credit_hours": coverage["known_sch"],
        "enrollment_complete": coverage["enrollment_complete"],
        "sch_complete": coverage["sch_complete"],
    }


def _section_coverage(rows):
    enrollment_rows = tuple(row for row in rows if _valid_number(row["enrollment"], integer=True))
    credit_rows = tuple(row for row in rows if _valid_number(row["credits"]))
    ready = tuple(row for row in rows if _valid_number(row["enrollment"], integer=True) and _valid_number(row["credits"]))
    count = len(rows)
    return {
        "section_count": count,
        "sections_with_enrollment": len(enrollment_rows),
        "sections_with_explicit_credits": len(credit_rows),
        "sch_ready_section_count": len(ready),
        "sch_ready_section_percent": round(100 * len(ready) / count, 6) if count else 0.0,
        "known_enrollment": sum(row["enrollment"] for row in enrollment_rows) if enrollment_rows else None,
        "known_sch": sum(float(row["credits"]) * int(row["enrollment"]) for row in ready) if ready else None,
        "enrollment_complete": bool(rows) and len(enrollment_rows) == count,
        "sch_complete": bool(rows) and len(ready) == count,
    }


def _valid_number(value, integer=False):
    expected = int if integer else (int, float)
    return isinstance(value, expected) and not isinstance(value, bool) and value >= 0


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
