"""Deterministic evidence-readiness audit for institutional workload metrics.

The audit inspects governed registries and normalized factual observations.  It
does not calculate SCH, infer employment status, or select a preferred faculty
denominator.
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

from app.institutional_units import (
    AcademicUnitRegistry,
    assess_faculty_workforce_eligibility,
)
from app.reasoning.academic_unit_mapping import AcademicUnitMappingService
from app.subject_ownership import SubjectOwnershipRegistry


AUDIT_ALGORITHM = "iso_metric_readiness_audit"
AUDIT_VERSION = "1.2"


FACULTY_CAPABILITIES: Mapping[str, Mapping[str, str]] = {
    "institutional_faculty_directory": {
        "faculty_identifier": "partially_implemented_snapshot_observation_id_not_person_id",
        "name": "implemented",
        "department": "implemented_published_label",
        "school": "partially_implemented_when_published",
        "home_academic_unit": "partially_implemented_exact_registry_resolution",
        "secondary_unit": "partially_implemented_published_affiliations_not_governed_membership",
        "rank": "partially_implemented_published_titles_not_normalized_rank",
        "appointment_type": "missing",
        "employment_category": "missing",
        "full_time_part_time": "missing",
        "instructional_status": "missing",
        "tenure_status": "missing",
        "administrative_assignment": "partially_implemented_only_when_published_as_title",
        "appointment_fte": "missing",
        "start_date": "missing",
        "end_date": "missing",
        "historical_affiliation": "partially_implemented_snapshot_scoped_only",
        "teaching_assignment": "missing_profile_interests_are_not_section_assignments",
        "source_provenance": "implemented",
        "effective_dates": "partially_implemented_snapshot_date",
        "confidence_evidence_fitness": "missing_field_level_fitness",
    },
    "academic_catalog_faculty": {
        "faculty_identifier": "partially_implemented_catalog_observation_id_not_person_id",
        "name": "implemented",
        "department": "implemented_published_academic_unit",
        "school": "partially_implemented_through_governed_unit_hierarchy",
        "home_academic_unit": "partially_implemented_catalog_listing_not_employment_home",
        "secondary_unit": "missing",
        "rank": "partially_implemented_published_title_not_normalized_rank",
        "appointment_type": "missing",
        "employment_category": "missing",
        "full_time_part_time": "missing",
        "instructional_status": "missing",
        "tenure_status": "missing",
        "administrative_assignment": "partially_implemented_published_title_only",
        "appointment_fte": "missing",
        "start_date": "partially_implemented_published_appointment_year",
        "end_date": "missing",
        "historical_affiliation": "partially_implemented_catalog_edition_scoped",
        "teaching_assignment": "missing",
        "source_provenance": "implemented",
        "effective_dates": "partially_implemented_catalog_year",
        "confidence_evidence_fitness": "missing_field_level_fitness",
    },
    "academic_catalog_roster": {
        "faculty_identifier": "missing",
        "name": "implemented",
        "department": "implemented_published_academic_unit",
        "school": "partially_implemented_through_governed_unit_hierarchy",
        "home_academic_unit": "partially_implemented_roster_membership_not_employment_home",
        "secondary_unit": "missing",
        "rank": "partially_implemented_published_category",
        "appointment_type": "missing",
        "employment_category": "missing",
        "full_time_part_time": "missing",
        "instructional_status": "missing",
        "tenure_status": "missing",
        "administrative_assignment": "missing",
        "appointment_fte": "missing",
        "start_date": "missing",
        "end_date": "missing",
        "historical_affiliation": "partially_implemented_catalog_edition_scoped",
        "teaching_assignment": "missing",
        "source_provenance": "implemented",
        "effective_dates": "partially_implemented_catalog_year",
        "confidence_evidence_fitness": "missing_field_level_fitness",
    },
    "institutional_schedule": {
        "faculty_identifier": "missing_published_name_only",
        "name": "implemented_published_instructor_string",
        "department": "missing_instructor_home_unit",
        "school": "missing_instructor_home_unit",
        "home_academic_unit": "missing_course_owner_is_not_instructor_home",
        "secondary_unit": "missing",
        "rank": "missing",
        "appointment_type": "missing",
        "employment_category": "missing_section_scoped_instructor_type_is_not_employment",
        "full_time_part_time": "partially_implemented_section_scoped_source_assertion_only",
        "instructional_status": "partially_implemented_assignment_proves_scheduled_instruction_only",
        "tenure_status": "missing",
        "administrative_assignment": "missing",
        "appointment_fte": "missing",
        "start_date": "missing",
        "end_date": "missing",
        "historical_affiliation": "missing",
        "teaching_assignment": "implemented_section_and_term_scoped",
        "source_provenance": "implemented",
        "effective_dates": "implemented_academic_term",
        "confidence_evidence_fitness": "partially_implemented_repair_provenance",
    },
}


@dataclass(frozen=True)
class MetricReadinessAuditReport:
    institutional_units: Mapping[str, Any]
    faculty_observation: Mapping[str, Any]
    sch_readiness: Mapping[str, Any]
    denominator_readiness: Mapping[str, Any]
    backlog: Mapping[str, tuple[str, ...]]
    provenance: Mapping[str, Any]
    deterministic_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["backlog"] = {key: list(items) for key, items in self.backlog.items()}
        return value


class MetricReadinessAuditService:
    """Inspect evidence contracts and supplied normalized objects without deriving metrics."""

    def __init__(
        self,
        unit_registry: AcademicUnitRegistry | None = None,
        subject_registry: SubjectOwnershipRegistry | None = None,
    ) -> None:
        self.unit_registry = unit_registry or AcademicUnitRegistry.load()
        self.subject_registry = subject_registry or SubjectOwnershipRegistry.load()
        self.mapping_service = AcademicUnitMappingService(
            self.unit_registry, self.subject_registry
        )

    def audit(
        self,
        normalized_objects: Iterable[Mapping[str, Any]] = (),
        *,
        normalized_root: str | Path | None = None,
    ) -> MetricReadinessAuditReport:
        objects = tuple(normalized_objects)
        units = self._unit_audit(objects)
        faculty = self._faculty_audit(objects)
        sch = self._sch_audit(objects)
        denominators = _denominator_readiness()
        backlog = _backlog()
        provenance = {
            "algorithm": AUDIT_ALGORITHM,
            "algorithm_version": AUDIT_VERSION,
            "normalized_root": _repository_relative(normalized_root),
            "normalized_object_count": len(objects),
            "academic_unit_registry_version": self.unit_registry.version,
            "subject_registry_id": self.subject_registry.registry_id,
            "subject_registry_fingerprint": self.subject_registry.fingerprint,
            "source_object_ids_fingerprint": _fingerprint(
                sorted(str(item.get("id") or "") for item in objects)
            ),
        }
        semantic = {
            "institutional_units": units,
            "faculty_observation": faculty,
            "sch_readiness": sch,
            "denominator_readiness": denominators,
            "backlog": backlog,
            "provenance": provenance,
        }
        return MetricReadinessAuditReport(
            units, faculty, sch, denominators, backlog, provenance,
            _fingerprint_payload(semantic),
        )

    def _unit_audit(self, objects: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
        units = {unit.unit_id: unit for unit in self.unit_registry.units}
        references: dict[str, set[str]] = defaultdict(set)
        unresolved_labels: Counter[str] = Counter()
        label_occurrences: list[dict[str, Any]] = []
        for unit in units.values():
            if unit.parent_unit_id:
                references[unit.parent_unit_id].add("institutional_unit.parent")
            for child in unit.subordinate_unit_ids:
                references[child].add("institutional_unit.subordinate")
        for record in self.subject_registry.records:
            for unit_id in (
                record.owning_academic_unit_id,
                record.analytical_academic_unit_id,
            ):
                if unit_id:
                    references[unit_id].add("subject_ownership")
        program_path = Path(__file__).resolve().parents[1] / "config" / "institutional_programs.yaml"
        program_payload = yaml.safe_load(program_path.read_text(encoding="utf-8")) or {}
        for program in program_payload.get("programs") or ():
            school = str(program.get("school") or "").strip()
            if not school:
                continue
            resolved = self.unit_registry.resolve(school)
            if resolved:
                references[resolved.unit_id].add("institutional_programs.school")
            else:
                unresolved_labels[school] += 1
        scope_path = Path(__file__).resolve().parents[1] / "config" / "semantic_scopes.yaml"
        scope_payload = yaml.safe_load(scope_path.read_text(encoding="utf-8")) or {}
        for scope in scope_payload.get("scopes") or ():
            if str(scope.get("kind") or "") != "department":
                continue
            label = str(scope.get("label") or "").strip()
            if not label:
                continue
            resolved = self.unit_registry.resolve(label)
            if resolved:
                references[resolved.unit_id].add("semantic_scopes.department")
            else:
                unresolved_labels[label] += 1
        for obj in objects:
            object_type = str(obj.get("object_type") or "unknown")
            identity = _semantic_identity(obj)
            for entity in identity.get("institutional_entities") or ():
                unit_id = str(entity.get("entity_id") or "")
                if unit_id.startswith("academic_unit:"):
                    references[unit_id].add(f"normalized:{object_type}:entity")
            for relationship in identity.get("organizational_relationships") or ():
                for field in ("source", "target"):
                    unit_id = str(relationship.get(field) or "")
                    if unit_id.startswith("academic_unit:"):
                        references[unit_id].add(f"normalized:{object_type}:relationship")
            published_labels = [
                (field, obj.get(field))
                for field in ("academic_unit", "published_department", "published_college")
            ]
            if object_type == "academic_unit_observation":
                published_labels.extend((
                    ("published_name", obj.get("published_name")),
                    ("published_parent_unit", obj.get("published_parent_unit")),
                ))
            if object_type == "faculty_observation":
                published_labels.extend(
                    ("organizational_affiliations.label", affiliation.get("label"))
                    for affiliation in obj.get("organizational_affiliations") or ()
                    if isinstance(affiliation, Mapping)
                )
            for field, raw_label in published_labels:
                label = str(raw_label or "").strip()
                if label:
                    exact = self.unit_registry.resolve(label)
                    resolution = self.unit_registry.resolve_published_label(label)
                    label_occurrences.append({
                        "published_label": label,
                        "object_type": object_type,
                        "field": field,
                        "source_path": _object_source_path(obj),
                        "exact_unit_id": exact.unit_id if exact else None,
                        "resolved_unit_id": resolution.unit_id,
                        "resolution_method": resolution.resolution_method,
                        "classification": resolution.classification,
                        "active_workforce_eligible": resolution.active_workforce_eligible,
                        "cleaned_label": resolution.cleaned_label,
                        "parser_contamination_detected": resolution.parser_contamination_detected,
                        "competing_unit_ids": list(resolution.competing_unit_ids),
                        "role_title": resolution.role_title,
                    })
                    if resolution.unit:
                        references[resolution.unit.unit_id].add(f"normalized:{object_type}:{field}")
                    elif resolution.classification != "excluded_emeritus":
                        unresolved_labels[label] += 1
        governed = []
        for unit in sorted(units.values(), key=lambda item: item.unit_id):
            governed.append({
                "unit_id": unit.unit_id,
                "published_name": unit.published_name,
                "formal_unit_type": unit.formal_unit_type,
                "parent_unit_id": unit.parent_unit_id,
                "subordinate_unit_ids": list(unit.subordinate_unit_ids),
                "aliases": list(unit.aliases),
                "abbreviation": unit.abbreviation,
                "operational_roles": list(unit.operational_roles),
                "deprecated": unit.deprecated,
                "successor_unit_ids": list(unit.successor_unit_ids),
                "active_current_unit": unit.active_current_unit,
                "valid_curriculum_ownership_unit": unit.valid_curriculum_ownership_unit,
                "valid_faculty_home_unit": unit.valid_faculty_home_unit,
                "valid_conventional_denominator_unit": unit.valid_conventional_denominator_unit,
                "valid_analytical_rollup_unit": unit.valid_analytical_rollup_unit,
                "effective_start": None,
                "effective_end": None,
            })
        unknown_ids = sorted(unit_id for unit_id in references if unit_id not in units)
        used = {unit_id for unit_id in references if unit_id in units}
        formal_types = Counter(unit.formal_unit_type for unit in units.values())
        roles = Counter(role for unit in units.values() for role in unit.operational_roles)
        methods = Counter(item["resolution_method"] for item in label_occurrences)
        classifications = Counter(item["classification"] for item in label_occurrences)
        exact_workforce = sum(
            bool(item["active_workforce_eligible"] and item["exact_unit_id"] and units[item["exact_unit_id"]].is_department_workforce_unit)
            for item in label_occurrences
        )
        resolved_workforce = sum(
            bool(item["active_workforce_eligible"] and item["resolved_unit_id"] and units[item["resolved_unit_id"]].is_department_workforce_unit)
            for item in label_occurrences
        )
        unresolved_details: dict[str, dict[str, Any]] = {}
        for item in label_occurrences:
            if item["resolution_method"] not in {"unresolved", "ambiguous"}:
                continue
            if item["classification"] == "excluded_emeritus":
                continue
            detail = unresolved_details.setdefault(item["published_label"], {
                "published_label": item["published_label"], "observation_count": 0,
                "object_types": set(), "source_paths": set(),
                "classification": item["classification"],
                "competing_unit_ids": set(),
            })
            detail["observation_count"] += 1
            detail["object_types"].add(item["object_type"])
            if item["source_path"]:
                detail["source_paths"].add(item["source_path"])
            detail["competing_unit_ids"].update(item["competing_unit_ids"])
        unresolved_inventory = [
            {
                **detail,
                "object_types": sorted(detail["object_types"]),
                "source_paths": sorted(detail["source_paths"])[:5],
                "competing_unit_ids": sorted(detail["competing_unit_ids"]),
            }
            for _, detail in sorted(unresolved_details.items())
        ]
        total_labels = len(label_occurrences)
        active_workforce_labels = sum(
            item["active_workforce_eligible"] for item in label_occurrences
        )
        emeritus_occurrences = [
            item for item in label_occurrences
            if item["classification"] == "excluded_emeritus"
        ]
        historical_units = [unit for unit in units.values() if unit.deprecated]
        program_units = [
            unit for unit in units.values()
            if unit.formal_unit_type in {"academic_program", "interdisciplinary_program"}
        ]
        college_level = [
            unit for unit in units.values()
            if unit.active_current_unit and (
                unit.formal_unit_type == "college"
                or "college_equivalent" in unit.operational_roles
            )
        ]
        return {
            "governed_academic_units": governed,
            "governed_unit_count": len(governed),
            "governed_counts_by_formal_type": dict(sorted(formal_types.items())),
            "governed_counts_by_operational_role": dict(sorted(roles.items())),
            "unit_semantic_categories": {
                "current_college_level_units": sorted(unit.unit_id for unit in college_level),
                "current_departments": sorted(
                    unit.unit_id for unit in units.values()
                    if unit.formal_unit_type == "department" and unit.active_current_unit
                ),
                "historical_departments": sorted(
                    unit.unit_id for unit in historical_units
                    if unit.formal_unit_type == "department"
                ),
                "program_level_units": sorted(unit.unit_id for unit in program_units),
                "university_wide_programs": sorted(
                    unit.unit_id for unit in program_units
                    if "university_wide_program" in unit.operational_roles
                ),
                "administrative_coordination_units": sorted(
                    unit.unit_id for unit in units.values()
                    if "academic_coordination" in unit.operational_roles
                ),
            },
            "unit_eligibility_counts": {
                "active_current_unit": sum(unit.active_current_unit for unit in units.values()),
                "valid_curriculum_ownership_unit": sum(unit.valid_curriculum_ownership_unit for unit in units.values()),
                "valid_faculty_home_unit": sum(unit.valid_faculty_home_unit for unit in units.values()),
                "valid_conventional_denominator_unit": sum(unit.valid_conventional_denominator_unit for unit in units.values()),
                "valid_analytical_rollup_unit": sum(unit.valid_analytical_rollup_unit for unit in units.values()),
            },
            "reference_sources_by_unit": {
                unit_id: sorted(sources) for unit_id, sources in sorted(references.items())
            },
            "referenced_unit_count": len(references),
            "referenced_but_not_governed": unknown_ids,
            "governed_but_currently_unused": sorted(set(units) - used),
            "unresolved_published_unit_labels": unresolved_inventory,
            "configuration_unresolved_labels": [
                {"published_label": label, "reference_count": count}
                for label, count in sorted(unresolved_labels.items())
                if label not in unresolved_details
            ],
            "published_label_resolution": {
                "total_published_unit_label_observations": total_labels,
                "resolution_method_counts": dict(sorted(methods.items())),
                "classification_counts": dict(sorted(classifications.items())),
                "canonical_exact_resolutions": methods["canonical_exact"],
                "governed_alias_resolutions": methods["governed_alias"],
                "cleaned_resolutions": methods["cleaned_canonical"] + methods["cleaned_governed_alias"],
                "embedded_resolutions": methods["embedded_governed_unit"],
                "role_prefix_resolutions": methods["governed_role_prefix"],
                "historical_unit_resolutions": classifications["historical_unit"],
                "emeritus_emerita_exclusions": classifications["excluded_emeritus"],
                "excluded_emeritus_with_resolved_underlying_unit": sum(
                    item["resolved_unit_id"] is not None for item in emeritus_occurrences
                ),
                "excluded_emeritus_with_unresolved_underlying_unit": sum(
                    item["resolved_unit_id"] is None for item in emeritus_occurrences
                ),
                "parser_contamination_cleaned": sum(
                    item["parser_contamination_detected"] and item["resolved_unit_id"] is not None
                    for item in label_occurrences
                ),
                "genuinely_unresolved_unique_labels": sum(
                    detail["classification"] == "genuinely_unresolved"
                    for detail in unresolved_inventory
                ),
                "genuinely_unresolved_observation_count": sum(
                    detail["observation_count"]
                    for detail in unresolved_inventory
                    if detail["classification"] == "genuinely_unresolved"
                ),
                "ambiguous_match_count": methods["ambiguous"],
                "workforce_unit_mapped_before_cleaning": exact_workforce,
                "workforce_unit_mapped_after_cleaning": resolved_workforce,
                "active_workforce_label_observation_count": active_workforce_labels,
                "workforce_mapping_coverage_before_percent": _percent(exact_workforce, active_workforce_labels),
                "workforce_mapping_coverage_after_percent": _percent(resolved_workforce, active_workforce_labels),
            },
            "alias_relationships": [
                {"alias": alias, "unit_id": unit.unit_id}
                for unit in sorted(units.values(), key=lambda item: item.unit_id)
                for alias in sorted(filter(None, (*unit.aliases, unit.abbreviation)))
            ],
            "potential_historical_ambiguities": [
                {
                    "unit_id": unit.unit_id,
                    "reason": "deprecated_unit_without_effective_dates",
                }
                for unit in sorted(units.values(), key=lambda item: item.unit_id)
                if unit.deprecated
            ],
            "temporal_model_limitations": [
                "Institutional-unit definitions do not currently carry effective start or end dates.",
                "Successor references preserve reviewed lineage but do not supply missing effective dates.",
            ],
            "reference_consumer_inventory": {
                "schedule_mapping": [
                    "app/reasoning/academic_unit_mapping.py",
                    "app/reasoning/schedule_analysis.py",
                    "config/subject_ownership.yaml",
                ],
                "catalog_mapping": [
                    "app/catalog_subject_ownership.py",
                    "app/classification/classifiers.py",
                ],
                "faculty_observation": [
                    "app/adapters/faculty_adapter.py",
                    "app/classification/classifiers.py",
                ],
                "decision_support": [
                    "app/observatory/topology/bootstrap.py",
                    "app/observatory/decision_readiness/evaluators/academic_workforce.py",
                    "config/semantic_scopes.yaml",
                ],
                "scenario_modeling": [
                    "app/reasoning/router.py (routing contract only; no unit metric service)",
                ],
                "retrieval": [
                    "app/chunk.py (Semantic Identity metadata propagation)",
                ],
            },
        }

    def _faculty_audit(self, objects: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
        object_types = Counter(str(item.get("object_type") or "unknown") for item in objects)
        fields = {
            "faculty_observation": (
                "display_name", "published_department", "published_college",
                "organizational_affiliations", "published_titles", "snapshot_date",
                "courses_or_areas_taught", "provenance",
            ),
            "catalog_faculty_observation": (
                "published_name", "published_title", "academic_unit", "appointment_year",
                "catalog_year", "provenance",
            ),
            "department_faculty_roster_observation": (
                "academic_unit", "entries", "catalog_year", "provenance",
            ),
            "course_offering_observation": (
                "instructor_raw", "instructor_type", "academic_term", "provenance",
            ),
        }
        coverage = {}
        for object_type, names in fields.items():
            matching = [item for item in objects if item.get("object_type") == object_type]
            coverage[object_type] = {
                "object_count": len(matching),
                "field_nonempty_counts": {
                    name: sum(_present(item.get(name)) for item in matching) for name in names
                },
            }
        eligibility_records = []
        for item in objects:
            object_type = str(item.get("object_type") or "")
            if object_type in {"faculty_observation", "catalog_faculty_observation"}:
                eligibility_records.append((object_type, assess_faculty_workforce_eligibility(item)))
            elif object_type == "department_faculty_roster_observation":
                for entry in item.get("entries") or ():
                    combined = dict(entry)
                    combined["academic_unit"] = item.get("academic_unit")
                    eligibility_records.append((object_type, assess_faculty_workforce_eligibility(combined)))
        excluded = [value for _, value in eligibility_records if not value.active_workforce_eligible]
        ambiguous_emerit = 0
        for item in objects:
            if item.get("object_type") not in {
                "faculty_observation", "catalog_faculty_observation",
                "department_faculty_roster_observation",
            }:
                continue
            encoded = json.dumps(item, ensure_ascii=False)
            if re.search(r"\bemerit\w*\b", encoded, re.IGNORECASE) and not re.search(
                r"\bemerit(?:us|a)\b", encoded, re.IGNORECASE
            ):
                ambiguous_emerit += 1
        return {
            "evidence_sources": {
                "institutional_faculty_directory": {
                    "object_type": "faculty_observation",
                    "capabilities": dict(FACULTY_CAPABILITIES["institutional_faculty_directory"]),
                },
                "academic_catalog_faculty": {
                    "object_type": "catalog_faculty_observation",
                    "capabilities": dict(FACULTY_CAPABILITIES["academic_catalog_faculty"]),
                },
                "academic_catalog_roster": {
                    "object_type": "department_faculty_roster_observation",
                    "capabilities": dict(FACULTY_CAPABILITIES["academic_catalog_roster"]),
                },
                "institutional_schedule": {
                    "object_type": "course_offering_observation",
                    "capabilities": dict(FACULTY_CAPABILITIES["institutional_schedule"]),
                },
            },
            "observed_object_type_counts": dict(sorted(object_types.items())),
            "observed_field_coverage": coverage,
            "active_workforce_eligibility": {
                "faculty_records_evaluated": len(eligibility_records),
                "active_workforce_eligible": len(eligibility_records) - len(excluded),
                "emeritus_emerita_observations_detected": len(excluded),
                "emeritus_emerita_observations_excluded": len(excluded),
                "ambiguous_emerit_status_records_not_excluded": ambiguous_emerit,
                "exclusion_reason_counts": {
                    "explicit_emeritus_or_emerita": len(excluded),
                },
            },
            "identity_limitations": [
                "No governed cross-source faculty-person identifier links directory, catalog, roster, and schedule names.",
                "Schedule Instructor Type is section-scoped and cannot establish timeless employment status.",
            ],
        }

    def _sch_audit(self, objects: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
        schedules = tuple(
            item for item in objects if item.get("object_type") == "course_offering_observation"
        )
        counts = Counter()
        statuses = Counter()
        mapped_units = Counter()
        terms = set()
        for item in schedules:
            credits = item.get("credits")
            enrollment = item.get("enrollment")
            subject = str(item.get("subject") or "").strip().upper()
            term = str(item.get("academic_term") or "").strip()
            if credits is not None:
                counts["credits_present"] += 1
            if enrollment is not None:
                counts["enrollment_present"] += 1
            if credits is not None and enrollment is not None:
                counts["credits_and_enrollment_present"] += 1
            if item.get("status") not in (None, ""):
                counts["status_present"] += 1
                statuses[str(item.get("status"))] += 1
            if item.get("instructor_raw") or item.get("instructor_name"):
                counts["instructor_present"] += 1
            if term:
                terms.add(term)
            mapping = self.mapping_service.map_subject(subject, term or None)
            if mapping.academic_unit_id and mapping.review_status == "governed" and mapping.status in {
                "mapped", "intentionally_grouped_department_equivalent"
            }:
                counts["workforce_unit_mapped"] += 1
                mapped_units[mapping.academic_unit_id] += 1
                if credits is not None and enrollment is not None:
                    counts["sch_inputs_and_workforce_unit_mapped"] += 1
        total = len(schedules)
        return {
            "readiness_status": "partially_implemented_not_metric_ready",
            "schedule_observation_count": total,
            "input_coverage_counts": {
                key: counts[key] for key in (
                    "credits_present", "enrollment_present",
                    "credits_and_enrollment_present", "status_present",
                    "instructor_present", "workforce_unit_mapped",
                    "sch_inputs_and_workforce_unit_mapped",
                )
            },
            "mapping_coverage_before_and_after_label_cleaning": {
                "workforce_unit_mapped_before": counts["workforce_unit_mapped"],
                "workforce_unit_mapped_after": counts["workforce_unit_mapped"],
                "sch_inputs_and_workforce_unit_mapped_before": counts["sch_inputs_and_workforce_unit_mapped"],
                "sch_inputs_and_workforce_unit_mapped_after": counts["sch_inputs_and_workforce_unit_mapped"],
                "explanation": "Schedule workforce mapping uses governed subject ownership, not published faculty/catalog unit labels; label cleanup therefore does not alter SCH mapping counts.",
            },
            "status_value_counts": dict(sorted(statuses.items())),
            "mapped_observation_counts_by_unit": dict(sorted(mapped_units.items())),
            "term_coverage": sorted(terms),
            "field_origins": {
                "credit_hours": "CourseOfferingObservation.credits from repaired published Hours values.",
                "enrollment": "CourseOfferingObservation.enrollment from the schedule export's Enrolled value.",
                "instructor_assignment": "CourseOfferingObservation.instructor_raw for one section and academic term.",
                "academic_unit": "AcademicUnitMappingService over governed subject ownership and institutional units.",
            },
            "special_case_readiness": {
                "cross_listed_courses": "missing_structured_cross_list_identifier_and_counting_policy",
                "labs": "observed_as_sections_but_no_governed_sch_treatment_policy",
                "variable_credit": "published_variants_preserved_but_actual_registered_credits_may_be_unavailable",
                "cancelled_sections": "status_observed_but_no_governed_inclusion_policy",
                "team_taught_sections": "missing_structured_multi_instructor_assignment",
                "independent_studies": "sections_observed_but_no_registered_credit_or_counting_policy",
                "future_terms": "scheduled_enrollment_is_not_validated_as_completed_delivery",
            },
            "blocking_requirements": [
                "Govern the reporting-period definition (calendar year, academic year, or fiscal year).",
                "Govern inclusion rules for cancelled, future, cross-listed, laboratory, variable-credit, and independent-study sections.",
                "Measure production coverage of credits, enrollment, status, and governed subject-to-unit mappings.",
                "Implement and test an SCH analytical service only after the evidence policies are approved.",
            ],
            "sec_2022_assessment": "conditionally_auditable_on_production_but_not_yet_governed_or_implemented",
        }


def load_normalized_objects(root: str | Path) -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
    values = []
    failures = []
    paths = sorted(Path(root).rglob("*.json"))
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("top-level JSON value is not an object")
            values.append(payload)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            failures.append({"path": _repository_relative(path), "error": str(exc)})
    return tuple(values), {
        "json_file_count": len(paths), "valid_object_count": len(values),
        "invalid_json_count": len(failures), "failures": failures,
    }


def _denominator_readiness() -> dict[str, Any]:
    return {
        "sch_per_faculty": {
            "status": "blocked_by_absent_governed_person_identity_and_population_definition",
            "available_evidence": "Directory and catalog observations provide names and unit listings.",
            "missing_evidence": ["Cross-source person identity", "governed active population", "effective appointments"],
        },
        "sch_per_instructional_faculty": {
            "status": "blocked_by_absent_instructional_appointment_observer",
            "available_evidence": "Schedules show section assignments by published instructor name.",
            "missing_evidence": ["Governed instructional status", "cross-source person identity"],
        },
        "sch_per_full_time_faculty": {
            "status": "blocked_by_absent_employment_status_observer",
            "available_evidence": "Section-scoped Instructor Type exists but is not an employment assertion.",
            "missing_evidence": ["Effective-dated employee category", "cross-source person identity"],
        },
        "sch_per_teaching_fte": {
            "status": "blocked_by_absent_appointment_and_teaching_fte",
            "available_evidence": "No governed FTE evidence stream is implemented.",
            "missing_evidence": ["Appointment FTE", "teaching allocation FTE", "effective dates"],
        },
        "sch_per_tenure_line_faculty": {
            "status": "blocked_by_absent_tenure_line_observer",
            "available_evidence": "Published titles are not governed tenure-line status.",
            "missing_evidence": ["Tenure-line category", "effective dates", "cross-source person identity"],
        },
        "sch_per_active_instructor": {
            "status": "partially_implemented_name_based_proxy_only",
            "available_evidence": "Schedules support term-scoped distinct published instructor-name counts.",
            "missing_evidence": ["Governed person resolution", "team-teaching structure", "missing/ambiguous instructor policy"],
        },
    }


def _backlog() -> dict[str, tuple[str, ...]]:
    return {
        "immediate_blockers": (
            "Approve deterministic SCH inclusion and reporting-period policies.",
            "Run production evidence-coverage audit for credits, enrollment, status, and academic-unit mapping.",
            "Add structured handling or explicit exclusions for cross-listing, variable credit, cancellation, labs, independent studies, and team teaching.",
        ),
        "needed_before_quentin_milestone": (
            "Implement the governed SCH aggregation service after policy approval.",
            "Acquire an effective-dated faculty appointment roster with stable person ID, home unit, employment category, instructional status, and appointment FTE.",
            "Implement governed cross-source faculty identity resolution and Evidence Fitness reporting.",
        ),
        "useful_later": (
            "Add tenure-line and administrative-assignment history when authorized.",
            "Model historical institutional-unit names and effective reorganization dates.",
        ),
        "architectural_debt": (
            "Institutional-unit registry lacks effective dates and typed historical aliases.",
            "Faculty directory, catalog, roster, and schedule observations lack a shared governed person identity.",
        ),
        "nice_to_have": (
            "Add compact coverage dashboards after metric contracts stabilize.",
        ),
    }


def _semantic_identity(value: Mapping[str, Any]) -> Mapping[str, Any]:
    identity = value.get("semantic_identity")
    if isinstance(identity, Mapping):
        return identity
    metadata = value.get("metadata") or {}
    identity = metadata.get("semantic_identity") if isinstance(metadata, Mapping) else None
    return identity if isinstance(identity, Mapping) else {}


def _present(value: Any) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, (Mapping, tuple, list, set, frozenset)):
        return int(bool(value))
    return 1


def _repository_relative(path: str | Path | None) -> str | None:
    if path is None:
        return None
    value = Path(path)
    try:
        return value.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return value.as_posix()


def _object_source_path(value: Mapping[str, Any]) -> str | None:
    provenance = value.get("provenance")
    source = value.get("source")
    provenance = provenance if isinstance(provenance, Mapping) else {}
    source = source if isinstance(source, Mapping) else {}
    for candidate in (
        value.get("relative_source_path"), value.get("source_file"),
        provenance.get("source_path"), source.get("path"),
    ):
        if candidate:
            return _repository_relative(str(candidate))
    return None


def _percent(numerator: int, denominator: int) -> float:
    return round(100.0 * numerator / denominator, 6) if denominator else 0.0


def _fingerprint(values: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.encode("utf-8")); digest.update(b"\0")
    return digest.hexdigest()


def _fingerprint_payload(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "AUDIT_ALGORITHM", "AUDIT_VERSION", "FACULTY_CAPABILITIES",
    "MetricReadinessAuditReport", "MetricReadinessAuditService",
    "load_normalized_objects",
]
