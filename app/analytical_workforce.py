"""Governed, deterministic analytical workforce reasoning.

The resulting population is a policy-defined scenario input, not an HR roster
or legally authoritative employment assertion.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import yaml

from app.academic_terms import academic_term_sort_key
from app.faculty_appointments import FacultyAppointmentObservationService
from app.faculty_identity import FacultyIdentityService
from app.institutional_units import AcademicUnitRegistry


DEFAULT_POLICY = Path(__file__).resolve().parents[1] / "config/analytical_workforce_policy.yaml"
DEFAULT_OVERRIDES = Path(__file__).resolve().parents[1] / "config/analytical_workforce_overrides.yaml"
ALGORITHM = "iso_analytical_workforce_builder"
ALGORITHM_VERSION = "1.1"
WORKFORCE_DISPOSITIONS = {"include", "exclude", "review_required"}
DEPARTMENT_DISPOSITIONS = {"resolved", "review_required", "not_applicable"}


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AnalyticalWorkforcePolicy:
    policy_id: str
    version: str
    recent_teaching_academic_years: int
    target_reference_population: int
    instructional_ranks: tuple[str, ...]
    exclude_statuses: tuple[str, ...]
    exclude_categories: tuple[str, ...]
    review_administrative_roles: tuple[str, ...]
    instructional_administrative_roles: tuple[str, ...]
    administrative_only_roles: tuple[str, ...]
    visiting_treatment: str
    missing_recent_teaching_treatment: str
    missing_safe_unit_treatment: str
    staff_title_patterns: tuple[str, ...]

    @classmethod
    def load(cls, path: Path = DEFAULT_POLICY):
        value = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        policy = cls(**{
            field: tuple(value[field]) if field in {
                "instructional_ranks", "exclude_statuses", "exclude_categories",
                "review_administrative_roles", "instructional_administrative_roles",
                "administrative_only_roles", "staff_title_patterns",
            } else value[field]
            for field in cls.__dataclass_fields__
        })
        if policy.visiting_treatment not in WORKFORCE_DISPOSITIONS:
            raise ValueError("Invalid visiting policy")
        if policy.missing_safe_unit_treatment != "department_review_required":
            raise ValueError("Missing safe units must be handled as department review")
        return policy

    @property
    def fingerprint(self):
        return _fingerprint(asdict(self))


@dataclass(frozen=True)
class AnalyticalWorkforceOverride:
    faculty_identity_id: str
    decision: str
    analytical_academic_unit_id: str | None
    reason: str
    source: str
    source_type: str
    reviewer: str
    review_date: str
    notes: str | None = None


def load_overrides(path: Path = DEFAULT_OVERRIDES) -> tuple[AnalyticalWorkforceOverride, ...]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    values = tuple(AnalyticalWorkforceOverride(**item) for item in payload.get("overrides") or ())
    ids = [item.faculty_identity_id for item in values]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate analytical workforce override")
    if any(item.decision not in WORKFORCE_DISPOSITIONS for item in values):
        raise ValueError("Invalid analytical workforce override decision")
    return values


@dataclass(frozen=True)
class AnalyticalWorkforceDecision:
    decision_id: str
    faculty_identity_id: str
    display_name: str
    workforce_disposition: str
    policy_id: str
    policy_version: str
    workforce_primary_reason_code: str
    workforce_reason_codes: tuple[str, ...]
    department_assignment_disposition: str
    department_assignment_primary_reason_code: str
    department_assignment_reason_codes: tuple[str, ...]
    evidence_references: tuple[str, ...]
    current_directory_observation_references: tuple[str, ...]
    faculty_appointment_observation_references: tuple[str, ...]
    administrative_appointment_observation_references: tuple[str, ...]
    employment_status_observation_references: tuple[str, ...]
    teaching_assignment_summary: Mapping[str, Any]
    published_academic_units: tuple[str, ...]
    analytical_academic_unit_id: str | None
    analytical_academic_unit_candidates: tuple[str, ...]
    analytical_unit_method: str | None
    evidence_fitness: tuple[str, ...]
    limitations: tuple[str, ...]
    governed_override: Mapping[str, Any] | None
    deterministic_fingerprint: str

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class AnalyticalWorkforcePopulation:
    population_id: str
    as_of_date: str
    policy_id: str
    policy_version: str
    starting_population_count: int
    workforce_included_count: int
    workforce_excluded_count: int
    workforce_review_required_count: int
    minimum_plausible_workforce_population: int
    maximum_plausible_workforce_population: int
    central_working_population: int | None
    included_identity_ids: tuple[str, ...]
    excluded_identity_ids: tuple[str, ...]
    workforce_review_identity_ids: tuple[str, ...]
    counts_by_workforce_reason: Mapping[str, int]
    department_assignment_resolved_count: int
    department_assignment_review_required_count: int
    department_assignment_not_applicable_count: int
    department_assignment_review_identity_ids: tuple[str, ...]
    counts_by_department_assignment_reason: Mapping[str, int]
    counts_by_academic_unit: Mapping[str, int]
    evidence_coverage: Mapping[str, Any]
    policy_sensitivity: Mapping[str, int]
    deterministic_fingerprint: str

    def to_dict(self):
        return asdict(self)


class AnalyticalWorkforceBuilder:
    def __init__(self, policy=None, overrides=()):
        self.policy = policy or AnalyticalWorkforcePolicy.load()
        self.overrides = {item.faculty_identity_id: item for item in overrides}
        self.unit_registry = AcademicUnitRegistry.load()

    def build(self, objects: Iterable[Mapping[str, Any]]):
        objects = tuple(objects)
        identities = FacultyIdentityService().audit(objects)
        appointments = FacultyAppointmentObservationService().audit(objects)
        by_object = {str(item.get("id")): item for item in objects}
        directory_dates = sorted({
            str(item.get("snapshot_date")) for item in objects
            if item.get("object_type") == "faculty_observation" and item.get("snapshot_date")
        })
        if not directory_dates:
            raise ValueError("No faculty-directory snapshot is available")
        as_of = directory_dates[-1]
        current_refs = {
            str(item.get("id")) for item in objects
            if item.get("object_type") == "faculty_observation"
            and str(item.get("snapshot_date")) == as_of
        }
        starting = tuple(identity for identity in identities.identities if any(
            source.observation_reference in current_refs
            for source in identity.source_observations
        ))
        faculty_by_id = _group(appointments.faculty_appointments)
        admin_by_id = _group(appointments.administrative_appointments)
        status_by_id = _group(appointments.employment_statuses)
        decisions = tuple(sorted((
            self._decide(identity, as_of, current_refs, by_object,
                         faculty_by_id.get(identity.identity_id, ()),
                         admin_by_id.get(identity.identity_id, ()),
                         status_by_id.get(identity.identity_id, ()))
            for identity in starting
        ), key=lambda item: item.faculty_identity_id))
        if len(decisions) != len(starting):
            raise ValueError("Every starting identity must receive one decision")
        ids = [item.decision_id for item in decisions]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate analytical workforce decision ID")
        return decisions, self._population(decisions, as_of)

    def _decide(self, identity, as_of, current_refs, objects, faculty, admin, statuses):
        directory_refs = tuple(sorted(
            source.observation_reference for source in identity.source_observations
            if source.observation_reference in current_refs
        ))
        current_faculty = tuple(item for item in faculty if item.source_system == "faculty_directory" and item.temporal_label == as_of)
        current_admin = tuple(item for item in admin if item.source_system == "faculty_directory" and item.temporal_label == as_of)
        explicit_statuses = {item.normalized_status for item in statuses}
        current_statuses = {
            item.normalized_status for item in statuses
            if item.source_system == "faculty_directory" and item.temporal_label == as_of
        }
        ranks = {rank for item in current_faculty for rank in item.normalized_ranks}
        roles = {item.normalized_administrative_role for item in current_admin}
        published_units = tuple(sorted({
            item.published_academic_unit_label for item in current_faculty
            if item.published_academic_unit_label
        }))
        unit_ids = tuple(sorted({
            item.academic_unit_id for item in current_faculty
            if item.academic_unit_id
            and self.unit_registry.get(item.academic_unit_id).valid_faculty_home_unit
        }))
        teaching = _teaching_summary(identity, objects, as_of, self.policy.recent_teaching_academic_years)
        workforce_reasons, fitness, limitations = [], {"current_directory_evidence", "current_status_proxy", "authoritative_status_unavailable"}, []
        workforce_disposition = "review_required"
        if current_statuses.intersection(self.policy.exclude_statuses):
            workforce_disposition = "exclude"
            status = sorted(current_statuses.intersection(self.policy.exclude_statuses))[0]
            workforce_reasons.append(f"explicit_{status}")
            fitness.add(f"explicit_{status}_status")
        elif "adjunct" in current_statuses or "adjunct" in ranks:
            workforce_disposition, workforce_reasons = "exclude", ["explicit_adjunct_only"]
            fitness.add("explicit_adjunct_status")
        elif explicit_statuses.intersection(self.policy.exclude_statuses):
            workforce_disposition, workforce_reasons = "review_required", ["conflicting_status_evidence"]
            limitations.append("historical_exclusion_status_with_current_directory_presence")
            fitness.add("review_required_due_to_policy_uncertainty")
        elif any(_staff_title(item.published_titles, self.policy.staff_title_patterns) for item in current_faculty):
            workforce_disposition, workforce_reasons = "exclude", ["non_faculty_staff_record"]
        elif roles.intersection(self.policy.review_administrative_roles):
            workforce_disposition, workforce_reasons = "review_required", ["senior_administrator_with_faculty_rank"]
            fitness.update(("administrative_role_present", "senior_administrator_review", "review_required_due_to_policy_uncertainty"))
        elif roles.intersection(self.policy.administrative_only_roles) and not ranks.intersection(self.policy.instructional_ranks):
            workforce_disposition, workforce_reasons = "exclude", ["governed_administrative_only"]
            fitness.add("administrative_role_present")
        elif "visiting" in ranks or "visiting" in current_statuses:
            workforce_disposition, workforce_reasons = self.policy.visiting_treatment, ["visiting_policy_uncertain"]
            fitness.add("review_required_due_to_policy_uncertainty")
        elif ranks.intersection(self.policy.instructional_ranks):
            workforce_disposition, workforce_reasons = "include", ["current_directory_instructional_title"]
            fitness.add("current_published_instructional_title")
            if teaching["recent_assignment_count"]:
                workforce_reasons.append("current_directory_and_recent_teaching")
        else:
            workforce_disposition, workforce_reasons = "review_required", ["current_directory_without_instructional_title"]
            limitations.append("unusual_or_missing_title")
            fitness.add("review_required_due_to_policy_uncertainty")
        unit_id = unit_ids[0] if len(unit_ids) == 1 else None
        unit_method = "current_directory_academic_unit" if unit_id else None
        if workforce_disposition == "exclude":
            department_disposition = "not_applicable"
            department_reasons = ["workforce_excluded"]
            unit_id, unit_method = None, None
        elif len(unit_ids) == 1:
            department_disposition = "resolved"
            department_reasons = ["current_directory_academic_unit"]
            fitness.add("analytical_unit_resolved")
        elif len(unit_ids) > 1:
            department_disposition = "review_required"
            department_reasons = ["multiple_current_unit_candidates"]
            fitness.add("analytical_unit_unresolved")
            limitations.append("multiple_current_unit_candidates")
        else:
            department_disposition = "review_required"
            department_reasons = ["no_safe_analytical_unit"]
            fitness.add("analytical_unit_unresolved")
            limitations.append("no_safe_analytical_unit")
        if teaching["recent_assignment_count"]:
            fitness.add("recent_teaching_support")
        elif teaching["total_assignment_count"]:
            fitness.add("historical_teaching_only")
            limitations.append("no_recent_teaching_observed")
        else:
            limitations.append("no_teaching_observed_not_exclusionary")
        override = self.overrides.get(identity.identity_id)
        override_value = None
        if override:
            workforce_disposition = override.decision
            unit_id = override.analytical_academic_unit_id or unit_id
            workforce_reasons.insert(0, "governed_override")
            if workforce_disposition == "exclude":
                department_disposition = "not_applicable"
                department_reasons = ["workforce_excluded"]
                unit_id, unit_method = None, None
            elif override.analytical_academic_unit_id:
                department_disposition = "resolved"
                department_reasons = ["governed_override"]
                unit_method = "governed_override"
            fitness.add("governed_override_applied")
            override_value = asdict(override)
        workforce_reasons = tuple(dict.fromkeys(workforce_reasons))
        department_reasons = tuple(dict.fromkeys(department_reasons))
        evidence_refs = tuple(sorted({
            *directory_refs,
            *(item.source_observation_reference for item in faculty),
            *(item.source_observation_reference for item in admin),
            *(item.source_observation_reference for item in statuses),
            *teaching["source_observation_references"],
        }))
        semantic = {
            "faculty_identity_id": identity.identity_id, "display_name": identity.display_name,
            "workforce_disposition": workforce_disposition, "policy_id": self.policy.policy_id,
            "policy_version": self.policy.version,
            "workforce_primary_reason_code": workforce_reasons[0],
            "workforce_reason_codes": workforce_reasons,
            "department_assignment_disposition": department_disposition,
            "department_assignment_primary_reason_code": department_reasons[0],
            "department_assignment_reason_codes": department_reasons,
            "evidence_references": evidence_refs,
            "current_directory_observation_references": directory_refs,
            "faculty_appointment_observation_references": sorted(item.observation_id for item in faculty),
            "administrative_appointment_observation_references": sorted(item.observation_id for item in admin),
            "employment_status_observation_references": sorted(item.observation_id for item in statuses),
            "teaching_assignment_summary": teaching, "published_academic_units": published_units,
            "analytical_academic_unit_id": unit_id,
            "analytical_academic_unit_candidates": unit_ids,
            "analytical_unit_method": unit_method,
            "evidence_fitness": sorted(fitness), "limitations": sorted(set(limitations)),
            "governed_override": override_value,
        }
        digest = _fingerprint(semantic)
        return AnalyticalWorkforceDecision(
            decision_id=f"analytical_workforce_decision:{digest}",
            deterministic_fingerprint=digest, **semantic,
        )

    def _population(self, decisions, as_of):
        workforce = {name: tuple(sorted(item.faculty_identity_id for item in decisions if item.workforce_disposition == name)) for name in WORKFORCE_DISPOSITIONS}
        departments = {name: tuple(sorted(item.faculty_identity_id for item in decisions if item.department_assignment_disposition == name)) for name in DEPARTMENT_DISPOSITIONS}
        workforce_reasons = Counter(item.workforce_primary_reason_code for item in decisions)
        department_reasons = Counter(item.department_assignment_primary_reason_code for item in decisions)
        units = Counter(item.analytical_academic_unit_id or "unresolved" for item in decisions if item.workforce_disposition != "exclude")
        sensitivity = {
            "visiting_review_count": sum("visiting_policy_uncertain" in item.workforce_reason_codes for item in decisions),
            "senior_administrator_review_count": sum("senior_administrator_with_faculty_rank" in item.workforce_reason_codes for item in decisions),
            "administrative_only_excluded_count": sum("governed_administrative_only" in item.workforce_reason_codes for item in decisions),
            "included_without_recent_teaching_count": sum(item.workforce_disposition == "include" and not item.teaching_assignment_summary["recent_assignment_count"] for item in decisions),
        }
        coverage = {
            "analytical_unit_resolved_count": len(departments["resolved"]),
            "analytical_unit_resolution_percent": round(100 * len(departments["resolved"]) / len(decisions), 6) if decisions else 0.0,
            "unit_resolution_percent_among_workforce_included": _percent(sum(item.workforce_disposition == "include" and item.department_assignment_disposition == "resolved" for item in decisions), len(workforce["include"])),
            "unit_resolution_percent_among_non_excluded": _percent(sum(item.workforce_disposition != "exclude" and item.department_assignment_disposition == "resolved" for item in decisions), len(decisions) - len(workforce["exclude"])),
            "recent_teaching_support_count": sum(bool(item.teaching_assignment_summary["recent_assignment_count"]) for item in decisions),
            "authoritative_status_available": False,
        }
        semantic = {
            "as_of_date": as_of, "policy_id": self.policy.policy_id,
            "policy_version": self.policy.version, "starting_population_count": len(decisions),
            "workforce_included_count": len(workforce["include"]),
            "workforce_excluded_count": len(workforce["exclude"]),
            "workforce_review_required_count": len(workforce["review_required"]),
            "minimum_plausible_workforce_population": len(workforce["include"]),
            "maximum_plausible_workforce_population": len(workforce["include"]) + len(workforce["review_required"]),
            "central_working_population": None, "included_identity_ids": workforce["include"],
            "excluded_identity_ids": workforce["exclude"], "workforce_review_identity_ids": workforce["review_required"],
            "counts_by_workforce_reason": dict(sorted(workforce_reasons.items())),
            "department_assignment_resolved_count": len(departments["resolved"]),
            "department_assignment_review_required_count": len(departments["review_required"]),
            "department_assignment_not_applicable_count": len(departments["not_applicable"]),
            "department_assignment_review_identity_ids": departments["review_required"],
            "counts_by_department_assignment_reason": dict(sorted(department_reasons.items())),
            "counts_by_academic_unit": dict(sorted(units.items())),
            "evidence_coverage": coverage, "policy_sensitivity": sensitivity,
        }
        if semantic["workforce_included_count"] + semantic["workforce_excluded_count"] + semantic["workforce_review_required_count"] != len(decisions):
            raise ValueError("Analytical workforce population does not reconcile")
        if semantic["department_assignment_resolved_count"] + semantic["department_assignment_review_required_count"] + semantic["department_assignment_not_applicable_count"] != len(decisions):
            raise ValueError("Department assignments do not reconcile")
        digest = _fingerprint(semantic)
        return AnalyticalWorkforcePopulation(
            population_id=f"analytical_workforce_population:{digest}",
            deterministic_fingerprint=digest, **semantic,
        )


def _group(values):
    result = defaultdict(list)
    for item in values:
        if item.faculty_identity_id:
            result[item.faculty_identity_id].append(item)
    return {key: tuple(value) for key, value in result.items()}


def _percent(numerator, denominator):
    return round(100 * numerator / denominator, 6) if denominator else 0.0


def _staff_title(titles, patterns):
    text = " ".join(titles).casefold()
    return any(re.search(rf"\b{re.escape(pattern.casefold())}\b", text) for pattern in patterns)


def _teaching_summary(identity, objects, as_of, years):
    assignments = []
    for source in identity.source_observations:
        if source.source_system != "schedule":
            continue
        value = objects.get(source.knowledge_object_id, {})
        assignments.append((source, value))
    terms = sorted({str(value.get("academic_term") or "") for _, value in assignments if value.get("academic_term")}, key=academic_term_sort_key)
    cutoff = int(as_of[:4]) - years
    recent = [(source, value) for source, value in assignments if _term_year(str(value.get("academic_term") or "")) >= cutoff]
    return {
        "total_assignment_count": len(assignments),
        "recent_assignment_count": len(recent),
        "most_recent_term": terms[-1] if terms else None,
        "terms": terms,
        "subject_prefixes": sorted({str(value.get("subject") or value.get("course_code") or "").split()[0] for _, value in assignments if value.get("subject") or value.get("course_code")}),
        "source_observation_references": sorted(source.observation_reference for source, _ in assignments),
        "recent_window_academic_years": years,
    }


def _term_year(term):
    match = re.search(r"(20\d{2})", term)
    return int(match.group(1)) if match else -1


__all__ = [
    "AnalyticalWorkforceBuilder", "AnalyticalWorkforceDecision",
    "AnalyticalWorkforceOverride", "AnalyticalWorkforcePolicy",
    "AnalyticalWorkforcePopulation", "load_overrides",
]
