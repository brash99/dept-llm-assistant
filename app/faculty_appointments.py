"""Source-scoped faculty appointment, administration, and status observations.

The extractor preserves explicit published facts. It never derives current
employment, faculty home, FTE, tenure, denominator eligibility, or workload.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from app.faculty_identity import FacultyIdentityService, normalize_person_name
from app.institutional_units import AcademicUnitRegistry


ALGORITHM = "iso_faculty_appointment_observation"
ALGORITHM_VERSION = "1.1"
APPOINTMENT_SOURCE_TYPES = {
    "faculty_observation", "catalog_faculty_observation",
    "department_faculty_roster_observation",
}
SCHEDULE_OBJECT_TYPE = "course_offering_observation"

RANK_RULES = (
    ("adjunct", re.compile(r"\badjunct(?:\s+professor)?\b", re.I)),
    ("visiting", re.compile(r"\bvisiting(?:\s+(?:assistant|associate))?\s+professor\b", re.I)),
    ("associate_professor", re.compile(r"\bassociate\s+professor\b", re.I)),
    ("assistant_professor", re.compile(r"\bassistant\s+professor\b", re.I)),
    ("professor", re.compile(r"\b(?:distinguished\s+)?professor\b", re.I)),
    ("instructor", re.compile(r"\binstructor\b", re.I)),
    ("lecturer", re.compile(r"\b(?:senior\s+)?lecturer\b", re.I)),
)
ADMINISTRATIVE_ROLE_RULES = (
    ("graduate_program_director", re.compile(r"\bgraduate\s+program\s+director\b", re.I)),
    ("vice_provost", re.compile(r"\bvice\s+provost\b", re.I)),
    ("provost", re.compile(r"(?<!vice\s)\bprovost\b", re.I)),
    ("dean", re.compile(r"\b(?:associate\s+|assistant\s+)?dean\b", re.I)),
    ("department_chair", re.compile(r"\b(?:department\s+)?chair\b", re.I)),
    ("program_director", re.compile(r"\b(?:program\s+director|director\s+of\s+honors)\b", re.I)),
    ("office_director", re.compile(r"\bdirector\b", re.I)),
)
STATUS_RULES = (
    ("emerita", re.compile(r"\bemerita\b", re.I)),
    ("emeritus", re.compile(r"\b(?:emeritus|emeriti)\b", re.I)),
    ("retired", re.compile(r"\bretired\b", re.I)),
    ("former", re.compile(r"\bformer\b", re.I)),
    ("full_time", re.compile(r"\bfull[ -]time\b", re.I)),
    ("part_time", re.compile(r"\bpart[ -]time\b", re.I)),
    ("adjunct", re.compile(r"\badjunct\b", re.I)),
    ("visiting", re.compile(r"\bvisiting\b", re.I)),
    ("temporary", re.compile(r"\btemporary\b", re.I)),
    ("inactive", re.compile(r"\binactive\b", re.I)),
    ("active", re.compile(r"(?<!in)\bactive\b", re.I)),
    ("current", re.compile(r"\bcurrent\b", re.I)),
)


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FacultyAppointmentObservation:
    observation_id: str
    faculty_identity_id: str | None
    source_observation_reference: str
    observed_person_name: str
    published_titles: tuple[str, ...]
    normalized_ranks: tuple[str, ...]
    published_academic_unit_label: str | None
    academic_unit_id: str | None
    appointment_category_published: str | None
    published_identifiers: tuple[str, ...]
    source_system: str
    source_path: str | None
    source_date: str | None
    temporal_label: str | None
    appointment_year_published: str | None
    current_status_claim: str | None
    evidence_fitness: tuple[str, ...]
    evidence_limitations: tuple[str, ...]
    provenance: Mapping[str, Any]
    deterministic_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {"object_type": "faculty_appointment_observation", **asdict(self)}


@dataclass(frozen=True)
class AdministrativeAppointmentObservation:
    observation_id: str
    faculty_identity_id: str | None
    source_observation_reference: str
    observed_person_name: str
    published_administrative_title: str
    normalized_administrative_role: str
    published_unit_label: str | None
    administrative_unit_id: str | None
    source_system: str
    source_path: str | None
    source_date: str | None
    temporal_label: str | None
    evidence_fitness: tuple[str, ...]
    evidence_limitations: tuple[str, ...]
    provenance: Mapping[str, Any]
    deterministic_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {"object_type": "administrative_appointment_observation", **asdict(self)}


@dataclass(frozen=True)
class EmploymentStatusObservation:
    observation_id: str
    faculty_identity_id: str | None
    source_observation_reference: str
    observed_person_name: str
    published_status_text: str
    normalized_status: str
    source_system: str
    source_path: str | None
    source_date: str | None
    temporal_label: str | None
    evidence_fitness: tuple[str, ...]
    evidence_limitations: tuple[str, ...]
    provenance: Mapping[str, Any]
    deterministic_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {"object_type": "employment_status_observation", **asdict(self)}


@dataclass(frozen=True)
class FacultyAppointmentAuditResult:
    faculty_appointments: tuple[FacultyAppointmentObservation, ...]
    administrative_appointments: tuple[AdministrativeAppointmentObservation, ...]
    employment_statuses: tuple[EmploymentStatusObservation, ...]
    summary: Mapping[str, Any]
    evidence_inventory: Mapping[str, Any]
    denominator_readiness: Mapping[str, Any]
    identity_review_queue: tuple[Mapping[str, Any], ...]
    deterministic_fingerprint: str

    def summary_dict(self) -> dict[str, Any]:
        return {
            "summary": dict(self.summary),
            "evidence_inventory": dict(self.evidence_inventory),
            "denominator_readiness": dict(self.denominator_readiness),
            "identity_review_queue": [dict(item) for item in self.identity_review_queue],
            "deterministic_fingerprint": self.deterministic_fingerprint,
        }


class FacultyAppointmentObservationService:
    def __init__(
        self,
        identity_service: FacultyIdentityService | None = None,
        unit_registry: AcademicUnitRegistry | None = None,
    ) -> None:
        self.identity_service = identity_service or FacultyIdentityService()
        self.unit_registry = unit_registry or AcademicUnitRegistry.load()

    def audit(self, objects: Iterable[Mapping[str, Any]]) -> FacultyAppointmentAuditResult:
        values = tuple(objects)
        identity_audit = self.identity_service.audit(values)
        identity_links = {
            source.observation_reference: (
                None if identity.ambiguous else identity.identity_id
            )
            for identity in identity_audit.identities
            for source in identity.source_observations
        }
        faculty: list[FacultyAppointmentObservation] = []
        administrative: list[AdministrativeAppointmentObservation] = []
        statuses: list[EmploymentStatusObservation] = []
        candidate_counts = Counter()
        schedule_assignments = 0
        ambiguous_records = []
        identity_review_queue = []

        for obj in sorted(values, key=lambda item: str(item.get("id") or "")):
            object_type = str(obj.get("object_type") or "")
            if object_type == SCHEDULE_OBJECT_TYPE:
                if obj.get("instructor_raw") or obj.get("instructor_name"):
                    schedule_assignments += 1
                continue
            if object_type not in APPOINTMENT_SOURCE_TYPES:
                continue
            candidate_counts[object_type] += 1
            for source in _source_people(obj):
                if not normalize_person_name(source["name"]):
                    continue
                reference = source["reference"]
                identity_id = identity_links.get(reference)
                if identity_id is None:
                    unresolved = {
                        "source_observation_reference": reference,
                        "observed_person_name": source["name"],
                        "source_system": source["source_system"],
                        "reason": "identity_unresolved_or_ambiguous",
                    }
                    ambiguous_records.append(unresolved)
                    identity_review_queue.append({
                        **unresolved,
                        "deterministic_candidates": list(
                            self.identity_service.review_candidates(
                                source["name"], identity_audit.identities
                            )
                        ),
                    })
                faculty_observation = self._faculty_observation(
                    obj, source, identity_id
                )
                if faculty_observation:
                    faculty.append(faculty_observation)
                administrative.extend(
                    self._administrative_observations(obj, source, identity_id)
                )
                statuses.extend(self._status_observations(obj, source, identity_id))

        faculty.sort(key=lambda item: item.observation_id)
        administrative.sort(key=lambda item: item.observation_id)
        statuses.sort(key=lambda item: item.observation_id)
        all_ids = [
            *(item.observation_id for item in faculty),
            *(item.observation_id for item in administrative),
            *(item.observation_id for item in statuses),
        ]
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("Duplicate appointment observation ID")
        linked = sum(
            item.faculty_identity_id is not None
            for item in (*faculty, *administrative, *statuses)
        )
        total = len(faculty) + len(administrative) + len(statuses)
        unit_resolved = sum(item.academic_unit_id is not None for item in faculty)
        temporal_missing = sum(
            item.temporal_label is None
            for item in (*faculty, *administrative, *statuses)
        )
        source_counts = Counter(
            item.source_system for item in (*faculty, *administrative, *statuses)
        )
        temporal_counts = Counter(
            item.temporal_label or "missing"
            for item in (*faculty, *administrative, *statuses)
        )
        ranks = Counter(rank for item in faculty for rank in item.normalized_ranks)
        roles = Counter(item.normalized_administrative_role for item in administrative)
        status_counts = Counter(item.normalized_status for item in statuses)
        fitness = Counter(
            category
            for item in (*faculty, *administrative, *statuses)
            for category in item.evidence_fitness
        )
        fitness["teaching_assignment_not_appointment"] += schedule_assignments
        summary = {
            "candidate_source_object_count": sum(candidate_counts.values()),
            "candidate_source_objects_by_type": dict(sorted(candidate_counts.items())),
            "faculty_appointment_observation_count": len(faculty),
            "administrative_appointment_observation_count": len(administrative),
            "employment_status_observation_count": len(statuses),
            "teaching_assignment_not_appointment_count": schedule_assignments,
            "total_appointment_related_observation_count": total,
            "identity_linked_observation_count": linked,
            "identity_unlinked_observation_count": total - linked,
            "identity_link_coverage_percent": _percent(linked, total),
            "unit_resolved_faculty_appointment_count": unit_resolved,
            "unit_resolution_coverage_percent": _percent(unit_resolved, len(faculty)),
            "normalized_rank_counts": dict(sorted(ranks.items())),
            "normalized_administrative_role_counts": dict(sorted(roles.items())),
            "explicit_status_counts": dict(sorted(status_counts.items())),
            "current_status_explicitly_observed_count": sum(
                item.normalized_status in {"current", "active"} for item in statuses
            ),
            "historical_or_catalog_edition_claim_count": fitness["catalog_edition_claim"] + fitness["department_roster_claim"],
            "observations_by_source_system": dict(sorted(source_counts.items())),
            "observations_by_temporal_label": dict(sorted(temporal_counts.items())),
            "evidence_fitness_counts": dict(sorted(fitness.items())),
            "ambiguous_or_unlinked_record_count": len(ambiguous_records),
            "identity_review_queue_count": len(identity_review_queue),
            "identity_review_queue_with_candidates_count": sum(
                bool(item["deterministic_candidates"])
                for item in identity_review_queue
            ),
            "ambiguous_or_unlinked_examples": sorted(
                ambiguous_records,
                key=lambda item: (item["observed_person_name"].casefold(), item["source_observation_reference"]),
            )[:20],
            "records_with_no_temporal_label_count": temporal_missing,
            "duplicate_observation_id_count": len(all_ids) - len(set(all_ids)),
        }
        inventory = _evidence_inventory(candidate_counts, schedule_assignments)
        readiness = _denominator_readiness()
        semantic = {
            "algorithm": ALGORITHM,
            "algorithm_version": ALGORITHM_VERSION,
            "identity_audit_fingerprint": identity_audit.deterministic_fingerprint,
            "faculty_appointments": [item.to_dict() for item in faculty],
            "administrative_appointments": [item.to_dict() for item in administrative],
            "employment_statuses": [item.to_dict() for item in statuses],
            "summary": summary,
            "evidence_inventory": inventory,
            "denominator_readiness": readiness,
            "identity_review_queue": sorted(
                identity_review_queue,
                key=lambda item: item["source_observation_reference"],
            ),
        }
        return FacultyAppointmentAuditResult(
            tuple(faculty), tuple(administrative), tuple(statuses), summary,
            inventory, readiness,
            tuple(semantic["identity_review_queue"]), _fingerprint(semantic),
        )

    def _faculty_observation(self, obj, source, identity_id):
        titles = source["titles"]
        unit_label = source["unit_label"]
        if not titles and not unit_label and not source["category"]:
            return None
        rank_texts = (*titles, source["category"] or "")
        ranks = tuple(sorted(filter(None, (
            _normalized_rank(title) for title in rank_texts
        ))))
        unit = self.unit_registry.resolve_published_label(unit_label).unit if unit_label else None
        fitness = {_fitness_for_source(source["source_system"])}
        limitations = {
            "no_appointment_fte_inference", "no_tenure_inference",
            "published_unit_is_not_faculty_home_assertion",
        }
        if not identity_id:
            fitness.add("identity_unresolved")
        if not source["temporal_label"]:
            fitness.add("temporal_scope_missing")
        if titles and not ranks:
            limitations.add("combined_or_unknown_title_not_normalized_as_rank")
        if source["appointment_year"]:
            limitations.add("published_appointment_year_is_not_verified_start_date")
        current = _explicit_current_status((*titles, source["category"] or ""))
        if current and source["source_system"] == "faculty_directory":
            fitness.add("explicit_current_directory_claim")
        semantic = {
            "kind": "faculty_appointment_observation",
            "faculty_identity_id": identity_id,
            "source_observation_reference": source["reference"],
            "observed_person_name": source["name"],
            "published_titles": list(titles),
            "normalized_ranks": list(ranks),
            "published_academic_unit_label": unit_label,
            "academic_unit_id": unit.unit_id if unit else None,
            "appointment_category_published": source["category"],
            "published_identifiers": list(source["identifiers"]),
            "source_system": source["source_system"],
            "source_path": source["source_path"],
            "source_date": source["source_date"],
            "temporal_label": source["temporal_label"],
            "appointment_year_published": source["appointment_year"],
            "current_status_claim": current,
            "evidence_fitness": sorted(fitness),
            "evidence_limitations": sorted(limitations),
        }
        fingerprint = _fingerprint(semantic)
        return FacultyAppointmentObservation(
            observation_id=f"faculty_appointment_observation:{fingerprint}",
            provenance=_provenance(source), deterministic_fingerprint=fingerprint,
            **{key: tuple(value) if key in {
                "published_titles", "normalized_ranks", "published_identifiers",
                "evidence_fitness", "evidence_limitations",
            } else value for key, value in semantic.items() if key != "kind"},
        )

    def _administrative_observations(self, obj, source, identity_id):
        values = []
        for title in filter(None, (*source["titles"], source["category"] or "")):
            roles = _administrative_roles(title)
            for role in roles:
                unit = _administrative_unit(
                    self.unit_registry, title, source["unit_label"]
                )
                fitness = {"administrative_title_claim", _fitness_for_source(source["source_system"])}
                limitations = {
                    "administrative_title_is_not_faculty_home_assertion",
                    "no_release_time_or_percentage_effort_inference",
                    "no_denominator_exclusion_inference",
                }
                if not identity_id:
                    fitness.add("identity_unresolved")
                if not source["temporal_label"]:
                    fitness.add("temporal_scope_missing")
                semantic = {
                    "kind": "administrative_appointment_observation",
                    "faculty_identity_id": identity_id,
                    "source_observation_reference": source["reference"],
                    "observed_person_name": source["name"],
                    "published_administrative_title": title,
                    "normalized_administrative_role": role,
                    "published_unit_label": source["unit_label"],
                    "administrative_unit_id": unit.unit_id if unit else None,
                    "source_system": source["source_system"],
                    "source_path": source["source_path"],
                    "source_date": source["source_date"],
                    "temporal_label": source["temporal_label"],
                    "evidence_fitness": sorted(fitness),
                    "evidence_limitations": sorted(limitations),
                }
                fingerprint = _fingerprint(semantic)
                values.append(AdministrativeAppointmentObservation(
                    observation_id=f"administrative_appointment_observation:{fingerprint}",
                    provenance=_provenance(source), deterministic_fingerprint=fingerprint,
                    **{key: tuple(value) if key in {"evidence_fitness", "evidence_limitations"}
                       else value for key, value in semantic.items() if key != "kind"},
                ))
        return values

    def _status_observations(self, obj, source, identity_id):
        values = []
        published = tuple(dict.fromkeys((*source["titles"], source["category"] or "")))
        for text in filter(None, published):
            for status, pattern in STATUS_RULES:
                if not pattern.search(text):
                    continue
                fitness = {"explicit_status_claim", _fitness_for_source(source["source_system"])}
                if (
                    source["source_system"] == "faculty_directory"
                    and status in {"current", "active"}
                ):
                    fitness.add("explicit_current_directory_claim")
                limitations = {"status_is_source_and_time_scoped", "no_fte_inference"}
                if not identity_id:
                    fitness.add("identity_unresolved")
                if not source["temporal_label"]:
                    fitness.add("temporal_scope_missing")
                semantic = {
                    "kind": "employment_status_observation",
                    "faculty_identity_id": identity_id,
                    "source_observation_reference": source["reference"],
                    "observed_person_name": source["name"],
                    "published_status_text": text,
                    "normalized_status": status,
                    "source_system": source["source_system"],
                    "source_path": source["source_path"],
                    "source_date": source["source_date"],
                    "temporal_label": source["temporal_label"],
                    "evidence_fitness": sorted(fitness),
                    "evidence_limitations": sorted(limitations),
                }
                fingerprint = _fingerprint(semantic)
                values.append(EmploymentStatusObservation(
                    observation_id=f"employment_status_observation:{fingerprint}",
                    provenance=_provenance(source), deterministic_fingerprint=fingerprint,
                    **{key: tuple(value) if key in {"evidence_fitness", "evidence_limitations"}
                       else value for key, value in semantic.items() if key != "kind"},
                ))
        return values


def _source_people(obj: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    object_type = str(obj.get("object_type") or "")
    base = _source_base(obj, object_type)
    if object_type == "department_faculty_roster_observation":
        return tuple({
            **base,
            "reference": f"{obj.get('id')}#entry:{index}",
            "name": str(entry.get("published_name") or "").strip(),
            "titles": (),
            "category": str(entry.get("published_category") or "").strip() or None,
            "unit_label": str(obj.get("academic_unit") or "").strip() or None,
            "identifiers": (),
            "appointment_year": None,
        } for index, entry in enumerate(obj.get("entries") or ()))
    if object_type == "faculty_observation":
        titles = tuple(map(str, obj.get("published_titles") or ()))
        identifiers = tuple(sorted({
            f"{field}:{str(obj[field]).strip().casefold()}"
            for field in ("person_id", "employee_id", "email") if obj.get(field)
        }))
        return ({
            **base,
            "reference": str(obj.get("id") or ""),
            "name": str(obj.get("display_name") or "").strip(),
            "titles": titles,
            "category": None,
            "unit_label": str(obj.get("published_department") or obj.get("published_college") or "").strip() or None,
            "identifiers": identifiers,
            "appointment_year": None,
        },)
    return ({
        **base,
        "reference": str(obj.get("id") or ""),
        "name": str(obj.get("published_name") or "").strip(),
        "titles": (str(obj.get("published_title")),) if obj.get("published_title") else (),
        "category": None,
        "unit_label": str(obj.get("academic_unit") or "").strip() or None,
        "identifiers": (),
        "appointment_year": str(obj.get("appointment_year")) if obj.get("appointment_year") else None,
    },)


def _source_base(obj: Mapping[str, Any], object_type: str) -> dict[str, Any]:
    source_system = {
        "faculty_observation": "faculty_directory",
        "catalog_faculty_observation": "catalog_faculty",
        "department_faculty_roster_observation": "department_roster",
    }[object_type]
    temporal = obj.get("snapshot_date") or obj.get("catalog_year")
    source_date = obj.get("snapshot_date") or obj.get("publication_date")
    provenance = obj.get("provenance") or {}
    source_path = (
        obj.get("relative_source_path") or obj.get("source_file")
        or obj.get("source_filename") or provenance.get("source_path")
        or provenance.get("source_file") or provenance.get("source")
    )
    return {
        "source_system": source_system,
        "source_path": _repository_relative(source_path),
        "source_date": str(source_date) if source_date else None,
        "temporal_label": str(temporal) if temporal else None,
    }


def _administrative_roles(title: str) -> tuple[str, ...]:
    roles = []
    for role, pattern in ADMINISTRATIVE_ROLE_RULES:
        if pattern.search(title):
            roles.append(role)
            if role in {"graduate_program_director", "vice_provost", "program_director"}:
                break
    return tuple(roles[:1])


def _normalized_rank(title: str) -> str | None:
    for rank, pattern in RANK_RULES:
        if pattern.search(title):
            return rank
    return None


def _administrative_unit(
    registry: AcademicUnitRegistry, title: str, unit_label: str | None
):
    bounded_title_units = (
        (re.compile(r"\bdirector\s+of\s+honors\b", re.I), "Honors Program"),
        (re.compile(r"\bdirector\s+of\s+orca\b", re.I), "ORCA"),
        (re.compile(r"\bvice\s+provost\b", re.I), "Office of the Provost"),
    )
    role_resolution = registry.resolve_published_label(title)
    if role_resolution.unit and role_resolution.resolution_method == "governed_role_prefix":
        return role_resolution.unit
    for pattern, label in bounded_title_units:
        if pattern.search(title):
            return registry.resolve(label)
    return registry.resolve_published_label(unit_label).unit if unit_label else None


def _explicit_current_status(values: Iterable[str]) -> str | None:
    for value in values:
        for status in ("current", "active"):
            if dict(STATUS_RULES)[status].search(value):
                return status
    return None


def _fitness_for_source(source_system: str) -> str:
    return {
        "faculty_directory": "directory_snapshot_claim",
        "catalog_faculty": "catalog_edition_claim",
        "department_roster": "department_roster_claim",
    }[source_system]


def _provenance(source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "algorithm": ALGORITHM,
        "algorithm_version": ALGORITHM_VERSION,
        "source_observation_reference": source["reference"],
        "source_system": source["source_system"],
        "source_path": source["source_path"],
    }


def _repository_relative(value: Any) -> str | None:
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute():
        return path.as_posix()
    root = Path(__file__).resolve().parents[1]
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _percent(numerator: int, denominator: int) -> float:
    return round((100 * numerator / denominator), 6) if denominator else 0.0


def _evidence_inventory(candidate_counts, schedule_assignments) -> dict[str, Any]:
    return {
        "faculty_directory": {
            "candidate_objects": candidate_counts["faculty_observation"],
            "faculty_title": "explicitly_observed_when_published",
            "faculty_rank": "deterministically_normalized_when_unambiguous",
            "academic_unit": "explicit_published_label_resolvable_without_home_inference",
            "administrative_title": "explicitly_observed_when_published",
            "employment_category": "explicit_status_phrases_only",
            "full_time_part_time": "absent_unless_explicit_in_title",
            "instructional_status": "unsafe_to_infer",
            "tenure_status": "absent",
            "appointment_fte": "absent",
            "start_end_dates": "absent",
            "retirement_emeritus": "explicit_status_phrases_only",
            "current_historical": "snapshot_date_observed_current_employment_not_inferred",
            "source_date": "snapshot_date",
            "effective_date": "absent",
        },
        "catalog_faculty": {
            "candidate_objects": candidate_counts["catalog_faculty_observation"],
            "faculty_title": "explicitly_observed",
            "faculty_rank": "deterministically_normalized_when_unambiguous",
            "academic_unit": "explicitly_observed",
            "administrative_title": "explicitly_observed_when_published",
            "employment_category": "explicit_status_phrases_only",
            "full_time_part_time": "absent_unless_explicit",
            "instructional_status": "unsafe_to_infer",
            "tenure_status": "absent",
            "appointment_fte": "absent",
            "start_end_dates": "appointment_year_parseable_not_verified_start_date",
            "retirement_emeritus": "explicit_status_phrases_only",
            "current_historical": "catalog_edition_claim_not_current_employment",
            "source_date": "catalog_year",
            "effective_date": "catalog_edition_only",
        },
        "department_roster": {
            "candidate_objects": candidate_counts["department_faculty_roster_observation"],
            "faculty_title": "published_roster_category_only",
            "faculty_rank": "parseable_only_when_category_explicitly_contains_rank",
            "academic_unit": "explicitly_observed",
            "administrative_title": "explicit_only_if_roster_category_states_role",
            "employment_category": "published_roster_category_preserved",
            "full_time_part_time": "absent_unless_explicit",
            "instructional_status": "unsafe_to_infer",
            "tenure_status": "absent",
            "appointment_fte": "absent",
            "start_end_dates": "absent",
            "retirement_emeritus": "explicit_status_phrases_only",
            "current_historical": "catalog_edition_claim_not_current_employment",
            "source_date": "catalog_year",
            "effective_date": "catalog_edition_only",
        },
        "schedule": {
            "teaching_assignment_observations": schedule_assignments,
            "faculty_appointment": "unsafe_to_infer",
            "employment_status": "section_scoped_instructor_type_not_employment",
            "temporal_scope": "academic_term",
        },
    }


def _denominator_readiness() -> dict[str, Any]:
    return {
        "full_time_faculty": {
            "status": "blocked_by_missing_evidence",
            "reason": "No effective-dated authoritative employment category; schedule Instructor Type is section-scoped.",
        },
        "instructional_faculty": {
            "status": "partially_supported",
            "reason": "Teaching assignments are observed, but appointment population and instructional appointment status are not governed.",
        },
        "tenure_line_faculty": {
            "status": "unsafe_to_infer",
            "reason": "Published rank is not tenure-line status.",
        },
        "faculty_fte": {
            "status": "blocked_by_missing_evidence",
            "reason": "No appointment or teaching FTE source is observed.",
        },
        "active_faculty": {
            "status": "unsafe_to_infer",
            "reason": "Catalog and roster presence are edition-scoped; directory snapshots do not explicitly prove effective employment.",
        },
        "current_faculty_by_unit": {
            "status": "unsafe_to_infer",
            "reason": "Published unit association is not an effective-dated faculty-home appointment.",
        },
    }


__all__ = [
    "AdministrativeAppointmentObservation", "EmploymentStatusObservation",
    "FacultyAppointmentAuditResult", "FacultyAppointmentObservation",
    "FacultyAppointmentObservationService",
]
