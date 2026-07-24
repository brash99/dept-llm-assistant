"""Department specialization of ISO's contribution ontology.

The builder composes existing governed semantic objects.  It does not parse
source evidence, recalculate Department Profiles, evaluate departments, or
produce reports.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping

from app.contribution_ontology import (
    ContributionAssertion,
    ContributionEvidenceBinding,
    ContributionKnowledgeObject,
    ContributionMeasure,
    ContributionPeriod,
    ContributionPredicate,
    ContributionTemporalScope,
)
from app.institutional_units import AcademicUnitRegistry
from app.semantic_identity import InstitutionalEntity
from app.subject_ownership import SubjectOwnershipRegistry
from app.undergraduate_major_capstones import (
    UndergraduateMajorCapstoneRegistry,
)
from app.undergraduate_majors import UndergraduateMajorRegistry


BUILDER_ID = "iso_department_contribution_builder"
BUILDER_VERSION = "1"


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    method = getattr(value, "to_dict", None)
    if callable(method):
        return method()
    raise TypeError("Builder inputs must be mappings or expose to_dict()")


def _course_key(value: str) -> str:
    return " ".join(str(value or "").upper().split())


def _entity(
    entity_type: str, entity_id: str, published_name: str
) -> InstitutionalEntity:
    return InstitutionalEntity(
        entity_type=entity_type,
        entity_id=entity_id,
        published_name=published_name,
    )


def _measure(
    assertion_id: str,
    binding_id: str,
    measure_type: str,
    value: Any,
    unit: str,
    definition: str,
    *,
    qualifiers: Mapping[str, Any] | None = None,
    limitations: Iterable[str] = (),
) -> ContributionMeasure | None:
    if value is None:
        return None
    return ContributionMeasure(
        measure_id=f"{assertion_id}:measure:{measure_type}",
        measure_type=measure_type,
        value=value,
        unit=unit,
        definition=definition,
        qualifiers=dict(qualifiers or {}),
        evidence_binding_ids=(binding_id,),
        limitations=tuple(limitations),
    )


def _present(values: Iterable[ContributionMeasure | None]) -> tuple[ContributionMeasure, ...]:
    return tuple(value for value in values if value is not None)


@dataclass(frozen=True)
class DepartmentContributionKnowledgeObject(
    ContributionKnowledgeObject[InstitutionalEntity]
):
    """Computational model of a department's institutionally evidenced function."""

    def __post_init__(self) -> None:
        super().__post_init__()
        department = (
            self.entity.formal_unit_type == "department"
            or "department_equivalent" in self.entity.operational_roles
        )
        if not department:
            raise ValueError(
                "DepartmentContributionKnowledgeObject requires a governed "
                "department or department-equivalent entity"
            )

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "contribution_object_type": "department_contribution",
            **super().semantic_dict(),
        }

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any]
    ) -> "DepartmentContributionKnowledgeObject":
        object_type = value.get("contribution_object_type")
        if object_type not in (None, "department_contribution"):
            raise ValueError(
                "Serialized object is not a department contribution"
            )
        return super().from_dict(value)


class DepartmentContributionBuilder:
    """Compose department contribution facts from existing semantic products."""

    def __init__(
        self,
        *,
        units: AcademicUnitRegistry | None = None,
        subjects: SubjectOwnershipRegistry | None = None,
        majors: UndergraduateMajorRegistry | None = None,
        capstones: UndergraduateMajorCapstoneRegistry | None = None,
    ):
        self.units = units or AcademicUnitRegistry.load()
        self.subjects = subjects or SubjectOwnershipRegistry.load()
        self.majors = majors or UndergraduateMajorRegistry.load()
        self.capstones = capstones or UndergraduateMajorCapstoneRegistry.load()

    def build(
        self,
        department_profiles: Iterable[Any],
        *,
        temporal_scope: ContributionTemporalScope,
        instructional_attribution: Any | None = None,
        llc_attribution: Any | None = None,
    ) -> tuple[DepartmentContributionKnowledgeObject, ...]:
        """Build one canonical semantic object for each supplied department.

        Department Profiles remain the authoritative aggregate input. Optional
        attribution objects add relationships that cannot be recovered from a
        profile aggregate alone.
        """

        profiles = tuple(
            sorted(
                (_mapping(value) for value in department_profiles),
                key=lambda value: str(value["academic_unit_id"]),
            )
        )
        ids = [str(value["academic_unit_id"]) for value in profiles]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate Department Profile academic unit")

        instructional = (
            _mapping(instructional_attribution)
            if instructional_attribution is not None else None
        )
        llc = _mapping(llc_attribution) if llc_attribution is not None else None
        if llc is not None and not llc.get("llc_only"):
            raise ValueError("LLC contribution input must be an LLC-only attribution")

        results = tuple(
            self._build_department(profile, temporal_scope, instructional, llc)
            for profile in profiles
        )
        object_ids = [item.contribution_object_id for item in results]
        if len(object_ids) != len(set(object_ids)):
            raise ValueError("Duplicate Department Contribution object ID")
        return results

    def _build_department(
        self,
        profile: Mapping[str, Any],
        temporal_scope: ContributionTemporalScope,
        instructional: Mapping[str, Any] | None,
        llc: Mapping[str, Any] | None,
    ) -> DepartmentContributionKnowledgeObject:
        unit_id = str(profile["academic_unit_id"])
        unit = self.units.get(unit_id)
        if not unit.is_department_workforce_unit:
            raise ValueError(f"Department Profile is not governed as a department: {unit_id}")
        subject = unit.to_entity()
        assertions: list[ContributionAssertion] = []

        assertions.extend(
            self._curriculum_assertions(subject, unit_id, temporal_scope)
        )
        instruction = self._instruction_assertion(subject, profile, temporal_scope)
        if instruction:
            assertions.append(instruction)
        assertions.extend(self._program_assertions(subject, unit_id, temporal_scope))
        assertions.extend(
            self._capstone_assertions(subject, unit_id, profile, temporal_scope)
        )
        if instructional:
            assertions.extend(
                self._service_assertions(
                    subject, unit_id, instructional, temporal_scope
                )
            )
        if llc:
            assertions.extend(
                self._llc_assertions(subject, unit_id, llc, temporal_scope)
            )

        return DepartmentContributionKnowledgeObject(
            contribution_object_id=(
                f"department_contribution:{unit_id.split(':', 1)[-1]}:"
                f"{_scope_key(temporal_scope)}:"
                f"{_scope_fingerprint(temporal_scope)[:16]}"
            ),
            entity=subject,
            temporal_scope=temporal_scope,
            assertions=tuple(
                sorted(assertions, key=lambda value: value.assertion_id)
            ),
            ontology_version="1",
            provenance={
                "builder": BUILDER_ID,
                "builder_version": BUILDER_VERSION,
                "department_profile_id": profile["department_profile_id"],
                "department_profile_fingerprint": profile[
                    "deterministic_fingerprint"
                ],
            },
        )

    def _curriculum_assertions(
        self,
        subject: InstitutionalEntity,
        unit_id: str,
        scope: ContributionTemporalScope,
    ) -> tuple[ContributionAssertion, ...]:
        records = tuple(
            sorted(
                (
                    item
                    for item in self.subjects.records
                    if item.owning_academic_unit_id == unit_id
                    and item.review_status == "governed"
                ),
                key=lambda item: (item.subject_code, item.record_id),
            )
        )
        assertions = []
        for record in records:
            assertion_id = (
                f"contribution_assertion:{unit_id}:owns_curriculum:"
                f"{record.subject_code}"
            )
            binding = ContributionEvidenceBinding(
                binding_id=f"{assertion_id}:evidence",
                source_references=(
                    f"{self.subjects.registry_id}:{record.record_id}",
                ),
                provenance={
                    "registry_id": self.subjects.registry_id,
                    "mapping_method": record.mapping_method,
                    "review_status": record.review_status,
                    "evidence": [
                        {
                            "source": item.source,
                            "source_type": item.source_type,
                            "assertion": item.assertion,
                        }
                        for item in record.evidence
                    ],
                },
                builder=BUILDER_ID,
                builder_version=BUILDER_VERSION,
                source_fingerprints={
                    "subject_ownership_registry": self.subjects.fingerprint
                },
                derivation_basis=(
                    "governed subject-prefix ownership assertion"
                ),
            )
            assertions.append(
                ContributionAssertion(
                    assertion_id=assertion_id,
                    subject=subject,
                    predicate=ContributionPredicate.OWNS_CURRICULUM,
                    object=_entity(
                        "instructional_subject",
                        f"instructional_subject:{record.subject_code}",
                        record.display_name,
                    ),
                    qualifiers={
                        "subject_code": record.subject_code,
                        "relationship_type": record.relationship_type,
                        "effective_start_term": record.effective_start_term,
                        "effective_end_term": record.effective_end_term,
                    },
                    temporal_scope=scope,
                    evidence_bindings=(binding,),
                    provenance={"source_semantic_object": "SubjectOwnershipRecord"},
                )
            )
        return tuple(assertions)

    def _instruction_assertion(
        self,
        subject: InstitutionalEntity,
        profile: Mapping[str, Any],
        scope: ContributionTemporalScope,
    ) -> ContributionAssertion | None:
        activity = dict(profile.get("department_owned_instruction") or {})
        if not activity.get("teaching_assignment_count"):
            return None
        unit_id = subject.entity_id
        assertion_id = (
            f"contribution_assertion:{unit_id}:delivers_instruction_for:"
            "governed_curriculum"
        )
        binding_id = f"{assertion_id}:evidence"
        binding = ContributionEvidenceBinding(
            binding_id=binding_id,
            source_references=(str(profile["department_profile_id"]),),
            provenance={
                "source_semantic_object": "DepartmentProfile",
                "evidence_summary": dict(profile.get("evidence_summary") or {}),
                "evidence_fitness": list(
                    profile.get("evidence_fitness") or ()
                ),
                "known_limitations": list(
                    profile.get("known_limitations") or ()
                ),
            },
            builder=BUILDER_ID,
            builder_version=BUILDER_VERSION,
            source_fingerprints={
                "department_profile": str(profile["deterministic_fingerprint"])
            },
            derivation_basis=(
                "existing governed Department Profile department-owned "
                "instruction aggregation"
            ),
        )
        incomplete = (
            ()
            if activity.get("sch_complete")
            else ("SCH is partial where explicit enrollment or credits are absent.",)
        )
        measures = _present(
            (
                _measure(
                    assertion_id,
                    binding_id,
                    "teaching_assignment_count",
                    activity.get("teaching_assignment_count"),
                    "assignments",
                    "Teaching assignments in governed department-owned subjects.",
                ),
                _measure(
                    assertion_id,
                    binding_id,
                    "section_count",
                    activity.get("section_count"),
                    "sections",
                    "Distinct sections in governed department-owned subjects.",
                ),
                _measure(
                    assertion_id,
                    binding_id,
                    "enrollment",
                    activity.get("enrollment_total"),
                    "students",
                    "Known enrollment in department-owned sections.",
                    limitations=(
                        ()
                        if activity.get("enrollment_complete")
                        else ("Enrollment is incomplete.",)
                    ),
                ),
                _measure(
                    assertion_id,
                    binding_id,
                    "student_credit_hours",
                    activity.get("student_credit_hours"),
                    "SCH",
                    "Known SCH from explicit enrollment and credit hours.",
                    limitations=incomplete,
                ),
            )
        )
        return ContributionAssertion(
            assertion_id=assertion_id,
            subject=subject,
            predicate=ContributionPredicate.DELIVERS_INSTRUCTION_FOR,
            object=_entity(
                "curriculum_portfolio",
                f"curriculum_portfolio:{unit_id}",
                f"{subject.published_name} governed curriculum",
            ),
                    qualifiers={
                        "subject_prefixes": list(activity.get("subject_prefixes") or ()),
                        "attribution_dimension": (
                            "governed_analytical_subject_ownership"
                        ),
                        "sch_complete": bool(activity.get("sch_complete")),
                "enrollment_complete": bool(activity.get("enrollment_complete")),
            },
            temporal_scope=_profile_scope(profile, scope),
            evidence_bindings=(binding,),
            provenance={"source_semantic_object": "DepartmentProfile"},
            measures=measures,
        )

    def _program_assertions(
        self,
        subject: InstitutionalEntity,
        unit_id: str,
        scope: ContributionTemporalScope,
    ) -> tuple[ContributionAssertion, ...]:
        majors = tuple(
            sorted(
                (
                    item
                    for item in self.majors.majors
                    if item.status == "current"
                    and item.owning_academic_unit_id == unit_id
                    and item.ownership_status == "resolved"
                ),
                key=lambda item: item.major_id,
            )
        )
        assertions = []
        registry_fingerprint = self.majors.deterministic_fingerprint
        for major in majors:
            assertion_id = (
                f"contribution_assertion:{unit_id}:administers_program:"
                f"{major.major_id}"
            )
            binding = ContributionEvidenceBinding(
                binding_id=f"{assertion_id}:evidence",
                source_references=tuple(
                    sorted(
                        {
                            f"{self.majors.registry_id}:{major.major_id}",
                            *(
                                item.source_locator
                                for item in major.evidence
                                if item.source_locator
                            ),
                        }
                    )
                ),
                provenance={
                    "registry_id": self.majors.registry_id,
                    "ownership_status": major.ownership_status,
                    "owner_assertions": [
                        {
                            "source": item.source,
                            "source_type": item.source_type,
                            "assertion": item.assertion,
                        }
                        for item in major.owner_assertions
                    ],
                },
                builder=BUILDER_ID,
                builder_version=BUILDER_VERSION,
                source_fingerprints={
                    "undergraduate_major_registry": registry_fingerprint
                },
                derivation_basis="resolved current major ownership",
            )
            assertions.append(
                ContributionAssertion(
                    assertion_id=assertion_id,
                    subject=subject,
                    predicate=ContributionPredicate.ADMINISTERS_PROGRAM,
                    object=_entity(
                        "undergraduate_major",
                        major.major_id,
                        major.display_name,
                    ),
                    qualifiers={
                        "degrees": list(major.degrees),
                        "major_status": major.status,
                    },
                    temporal_scope=scope,
                    evidence_bindings=(binding,),
                    provenance={
                        "source_semantic_object": "UndergraduateMajor"
                    },
                )
            )
        return tuple(assertions)

    def _capstone_assertions(
        self,
        subject: InstitutionalEntity,
        unit_id: str,
        profile: Mapping[str, Any],
        scope: ContributionTemporalScope,
    ) -> tuple[ContributionAssertion, ...]:
        observed = {_course_key(value) for value in profile.get("courses_taught") or ()}
        if not observed:
            return ()
        major_ids = {
            item.major_id
            for item in self.majors.majors
            if item.status == "current"
            and item.owning_academic_unit_id == unit_id
            and item.ownership_status == "resolved"
        }
        assertions = []
        for requirement in sorted(
            (
                item
                for item in self.capstones.requirements
                if item.major_id in major_ids
            ),
            key=lambda item: item.major_id,
        ):
            matched = tuple(
                sorted(
                    {
                        course
                        for pathway in requirement.pathways
                        for course in pathway.course_ids
                        if _course_key(course) in observed
                    }
                )
            )
            if not matched:
                continue
            assertion_id = (
                f"contribution_assertion:{unit_id}:"
                f"provides_capstone_instruction_for:{requirement.major_id}"
            )
            binding = ContributionEvidenceBinding(
                binding_id=f"{assertion_id}:evidence",
                source_references=(
                    str(profile["department_profile_id"]),
                    f"{self.capstones.registry_id}:{requirement.major_id}",
                ),
                provenance={
                    "registry_id": self.capstones.registry_id,
                    "catalog_year": self.capstones.catalog_year,
                    "observed_capstone_courses": list(matched),
                },
                builder=BUILDER_ID,
                builder_version=BUILDER_VERSION,
                source_fingerprints={
                    "department_profile": str(
                        profile["deterministic_fingerprint"]
                    ),
                    "major_capstone_registry": (
                        self.capstones.deterministic_fingerprint
                    ),
                },
                derivation_basis=(
                    "governed capstone requirement intersected with courses "
                    "observed in the Department Profile"
                ),
            )
            assertions.append(
                ContributionAssertion(
                    assertion_id=assertion_id,
                    subject=subject,
                    predicate=(
                        ContributionPredicate.PROVIDES_CAPSTONE_INSTRUCTION_FOR
                    ),
                    object=_entity(
                        "undergraduate_major",
                        requirement.major_id,
                        requirement.display_name,
                    ),
                    qualifiers={
                        "requirement_type": requirement.requirement_type,
                        "observed_capstone_courses": list(matched),
                    },
                    temporal_scope=scope,
                    evidence_bindings=(binding,),
                    provenance={
                        "source_semantic_objects": [
                            "DepartmentProfile",
                            "MajorCapstoneRequirement",
                        ]
                    },
                )
            )
        return tuple(assertions)

    def _service_assertions(
        self,
        subject: InstitutionalEntity,
        unit_id: str,
        report: Mapping[str, Any],
        scope: ContributionTemporalScope,
    ) -> tuple[ContributionAssertion, ...]:
        groups: dict[str, list[Mapping[str, Any]]] = {}
        for raw in report.get("section_attributions") or ():
            item = _mapping(raw)
            if (
                item.get("attribution_method") == "instructor_home"
                and item.get("workforce_attributed_unit_id") == unit_id
                and item.get("governed_prefix_owner_unit_id")
                and item.get("governed_prefix_owner_unit_id") != unit_id
            ):
                groups.setdefault(
                    str(item["governed_prefix_owner_unit_id"]), []
                ).append(item)
        divisor = len(report.get("academic_years") or ()) or 1
        assertions = []
        for target_id, rows in sorted(groups.items()):
            target = self.units.get(target_id)
            assertion_id = (
                f"contribution_assertion:{unit_id}:"
                f"provides_service_teaching_for:{target_id}"
            )
            binding_id = f"{assertion_id}:evidence"
            binding = ContributionEvidenceBinding(
                binding_id=binding_id,
                source_references=tuple(
                    sorted(str(item["section_key"]) for item in rows)
                ),
                provenance={
                    "source_semantic_object": "FacultyDeliveredSCHReport",
                    "academic_years": list(report.get("academic_years") or ()),
                    "aggregation": report.get("aggregation"),
                },
                builder=BUILDER_ID,
                builder_version=BUILDER_VERSION,
                source_fingerprints={
                    "instructional_attribution": str(
                        report["deterministic_fingerprint"]
                    )
                },
                derivation_basis=(
                    "existing instructor-home attribution where governed "
                    "curriculum ownership belongs to another department"
                ),
            )
            assertions.append(
                ContributionAssertion(
                    assertion_id=assertion_id,
                    subject=subject,
                    predicate=(
                        ContributionPredicate.PROVIDES_SERVICE_TEACHING_FOR
                    ),
                    object=target.to_entity(),
                    qualifiers={
                        "academic_years": list(
                            report.get("academic_years") or ()
                        ),
                        "aggregation": report.get("aggregation"),
                        "subject_prefixes": sorted(
                            {str(item["subject"]) for item in rows}
                        ),
                    },
                    temporal_scope=_attribution_scope(report, scope),
                    evidence_bindings=(binding,),
                    provenance={
                        "source_semantic_object": "FacultyDeliveredSCHReport"
                    },
                    measures=_present(
                        (
                            _measure(
                                assertion_id,
                                binding_id,
                                "section_count",
                                len(rows),
                                "sections",
                                "Cross-unit sections delivered by department-home faculty.",
                            ),
                            _measure(
                                assertion_id,
                                binding_id,
                                "mean_annual_student_credit_hours",
                                round(
                                    sum(float(item.get("sch") or 0) for item in rows)
                                    / divisor,
                                    6,
                                ),
                                "SCH",
                                "Mean annual SCH delivered for the target department.",
                                qualifiers={
                                    "academic_year_count": divisor,
                                },
                            ),
                        )
                    ),
                )
            )
        return tuple(assertions)

    def _llc_assertions(
        self,
        subject: InstitutionalEntity,
        unit_id: str,
        report: Mapping[str, Any],
        scope: ContributionTemporalScope,
    ) -> tuple[ContributionAssertion, ...]:
        groups: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
        for raw in report.get("section_attributions") or ():
            item = _mapping(raw)
            if item.get("workforce_attributed_unit_id") != unit_id:
                continue
            for match in item.get("llc_matched_designations") or ():
                designation = _mapping(match)
                key = (
                    str(designation["code"]),
                    str(designation["name"]),
                    str(designation["category"]),
                )
                groups.setdefault(key, []).append(item)
        divisor = len(report.get("academic_years") or ()) or 1
        assertions = []
        for (code, name, category), rows in sorted(groups.items()):
            unique_rows = {
                str(item["section_key"]): item for item in rows
            }
            rows = [unique_rows[key] for key in sorted(unique_rows)]
            assertion_id = (
                f"contribution_assertion:{unit_id}:"
                f"contributes_to_llc_requirement:{code}"
            )
            binding_id = f"{assertion_id}:evidence"
            binding = ContributionEvidenceBinding(
                binding_id=binding_id,
                source_references=tuple(
                    sorted(str(item["section_key"]) for item in rows)
                ),
                provenance={
                    "source_semantic_object": "FacultyDeliveredSCHReport",
                    "llc_policy_ids": list(report.get("llc_policy_ids") or ()),
                    "counting_rule": "count_section_once_per_designation",
                },
                builder=BUILDER_ID,
                builder_version=BUILDER_VERSION,
                source_fingerprints={
                    "llc_attribution": str(
                        report["deterministic_fingerprint"]
                    )
                },
                derivation_basis=(
                    "existing LLC-only attribution with a governed designation"
                ),
            )
            assertions.append(
                ContributionAssertion(
                    assertion_id=assertion_id,
                    subject=subject,
                    predicate=(
                        ContributionPredicate.CONTRIBUTES_TO_LLC_REQUIREMENT
                    ),
                    object=_entity(
                        "llc_requirement",
                        f"llc_requirement:{code}",
                        name,
                    ),
                    qualifiers={
                        "designation_code": code,
                        "designation_category": category,
                        "attribution_methods": sorted(
                            {
                                str(item.get("attribution_method") or "")
                                for item in rows
                                if item.get("attribution_method")
                            }
                        ),
                        "llc_policy_ids": list(
                            report.get("llc_policy_ids") or ()
                        ),
                    },
                    temporal_scope=_attribution_scope(report, scope),
                    evidence_bindings=(binding,),
                    provenance={
                        "source_semantic_object": "FacultyDeliveredSCHReport"
                    },
                    measures=_present(
                        (
                            _measure(
                                assertion_id,
                                binding_id,
                                "section_count",
                                len(rows),
                                "sections",
                                "Distinct sections carrying this governed LLC designation.",
                            ),
                            _measure(
                                assertion_id,
                                binding_id,
                                "mean_annual_student_credit_hours",
                                round(
                                    sum(float(item.get("sch") or 0) for item in rows)
                                    / divisor,
                                    6,
                                ),
                                "SCH",
                                "Mean annual SCH in sections carrying this LLC designation.",
                                qualifiers={
                                    "academic_year_count": divisor,
                                },
                            ),
                        )
                    ),
                )
            )
        return tuple(assertions)


def _scope_key(scope: ContributionTemporalScope) -> str:
    """Return a readable component of a contribution object's stable ID."""

    reporting = scope.reporting_period
    if reporting:
        value = reporting.label or "_".join(
            part for part in (reporting.start, reporting.end) if part
        )
    else:
        value = scope.publication_time or "bounded_scope"
    return "".join(
        character.lower() if character.isalnum() else "_"
        for character in value
    ).strip("_")


def _scope_fingerprint(scope: ContributionTemporalScope) -> str:
    encoded = json.dumps(
        scope.to_dict(),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _profile_scope(
    profile: Mapping[str, Any],
    fallback: ContributionTemporalScope,
) -> ContributionTemporalScope:
    earliest = profile.get("earliest_observed_term")
    latest = profile.get("latest_observed_term")
    if not earliest and not latest:
        return fallback
    period = ContributionPeriod(
        start=str(earliest) if earliest else None,
        end=str(latest) if latest else None,
        label="All schedule history represented by the Department Profile",
    )
    return ContributionTemporalScope(
        reporting_period=period,
        effective_period=fallback.effective_period,
        observation_period=period,
        publication_time=fallback.publication_time,
    )


def _attribution_scope(
    report: Mapping[str, Any],
    fallback: ContributionTemporalScope,
) -> ContributionTemporalScope:
    years = tuple(map(str, report.get("academic_years") or ()))
    if not years:
        return fallback
    period = ContributionPeriod(
        label=f"Academic years {', '.join(years)}"
    )
    return ContributionTemporalScope(
        reporting_period=period,
        effective_period=fallback.effective_period,
        observation_period=period,
        publication_time=fallback.publication_time,
    )


__all__ = [
    "BUILDER_ID",
    "BUILDER_VERSION",
    "DepartmentContributionBuilder",
    "DepartmentContributionKnowledgeObject",
]
