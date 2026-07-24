import json

import pytest

from app.contribution_ontology import (
    ContributionKnowledgeObject,
    ContributionPeriod,
    ContributionPredicate,
    ContributionTemporalScope,
)
from app.department_contributions import (
    DepartmentContributionBuilder,
    DepartmentContributionKnowledgeObject,
)


ENGLISH = "academic_unit:department_english"
HISTORY = "academic_unit:department_history"


def _scope():
    return ContributionTemporalScope(
        reporting_period=ContributionPeriod(
            start="2022-07-01", end="2025-06-30", label="AY 2022-23 to 2024-25"
        ),
        observation_period=ContributionPeriod(
            start="2022_fall", end="2025_summer"
        ),
        publication_time="2026-07-24T12:00:00+00:00",
    )


def _profile(
    unit_id=ENGLISH,
    name="Department of English",
    courses=("ENGL 490W", "ENGL 201"),
):
    return {
        "department_profile_id": f"department_profile:{unit_id}",
        "academic_unit_id": unit_id,
        "department_name": name,
        "governed_subject_prefixes": ["ENGL"],
        "courses_taught": list(courses),
        "earliest_observed_term": "2022_fall",
        "latest_observed_term": "2025_spring",
        "department_owned_instruction": {
            "teaching_assignment_count": 10,
            "section_count": 8,
            "subject_prefixes": ["ENGL"],
            "enrollment_total": 160,
            "student_credit_hours": 480.0,
            "enrollment_complete": True,
            "sch_complete": True,
        },
        "evidence_summary": {"schedule_observation_count": 10},
        "deterministic_fingerprint": "a" * 64,
    }


def _attribution(llc_only=False):
    return {
        "academic_years": ["2022-23", "2023-24", "2024-25"],
        "llc_only": llc_only,
        "llc_policy_ids": ["cnu_llc_designations"],
        "aggregation": "mean_annual_sch",
        "deterministic_fingerprint": ("c" if llc_only else "b") * 64,
        "section_attributions": [
            {
                "section_key": "2022_fall|ENGL|101|01",
                "subject": "ENGL",
                "governed_prefix_owner_unit_id": HISTORY,
                "workforce_attributed_unit_id": ENGLISH,
                "attribution_method": "instructor_home",
                "sch": 90.0,
                "llc_matched_designations": (
                    [
                        {
                            "code": "LLFW",
                            "name": "Written Communication",
                            "category": "foundations",
                        }
                    ]
                    if llc_only else []
                ),
            }
        ],
    }


def _by_predicate(result):
    return {
        predicate: tuple(
            item
            for item in result.assertions
            if item.predicate == predicate
        )
        for predicate in ContributionPredicate
    }


def test_department_specialization_is_a_contribution_knowledge_object():
    result = DepartmentContributionBuilder().build(
        (_profile(),), temporal_scope=_scope()
    )[0]
    assert isinstance(result, ContributionKnowledgeObject)
    assert isinstance(result, DepartmentContributionKnowledgeObject)
    assert result.entity.entity_id == ENGLISH
    assert result.to_dict()["contribution_object_type"] == (
        "department_contribution"
    )


def test_builder_composes_governed_curriculum_program_and_instruction():
    result = DepartmentContributionBuilder().build(
        (_profile(),), temporal_scope=_scope()
    )[0]
    assertions = _by_predicate(result)

    ownership = assertions[ContributionPredicate.OWNS_CURRICULUM]
    assert {item.object.entity_id for item in ownership} >= {
        "instructional_subject:ENGL"
    }
    programs = assertions[ContributionPredicate.ADMINISTERS_PROGRAM]
    assert {item.object.entity_id for item in programs} >= {
        "undergraduate_major:english"
    }
    delivery = assertions[ContributionPredicate.DELIVERS_INSTRUCTION_FOR]
    assert len(delivery) == 1
    measures = {item.measure_type: item.value for item in delivery[0].measures}
    assert measures == {
        "enrollment": 160,
        "section_count": 8,
        "student_credit_hours": 480.0,
        "teaching_assignment_count": 10,
    }


def test_capstone_assertion_requires_governed_requirement_and_observed_course():
    with_course = DepartmentContributionBuilder().build(
        (_profile(),), temporal_scope=_scope()
    )[0]
    without_course = DepartmentContributionBuilder().build(
        (_profile(courses=("ENGL 201",)),), temporal_scope=_scope()
    )[0]

    assert {
        item.object.entity_id
        for item in with_course.assertions
        if item.predicate
        == ContributionPredicate.PROVIDES_CAPSTONE_INSTRUCTION_FOR
    } == {"undergraduate_major:english"}
    assert not any(
        item.predicate
        == ContributionPredicate.PROVIDES_CAPSTONE_INSTRUCTION_FOR
        for item in without_course.assertions
    )


def test_existing_attribution_semantics_create_service_and_llc_assertions():
    result = DepartmentContributionBuilder().build(
        (_profile(),),
        temporal_scope=_scope(),
        instructional_attribution=_attribution(),
        llc_attribution=_attribution(llc_only=True),
    )[0]
    assertions = _by_predicate(result)

    service = assertions[
        ContributionPredicate.PROVIDES_SERVICE_TEACHING_FOR
    ][0]
    assert service.object.entity_id == HISTORY
    assert {
        item.measure_type: item.value for item in service.measures
    }["mean_annual_student_credit_hours"] == 30.0

    llc = assertions[
        ContributionPredicate.CONTRIBUTES_TO_LLC_REQUIREMENT
    ][0]
    assert llc.object.entity_id == "llc_requirement:LLFW"
    assert llc.qualifiers["designation_category"] == "foundations"
    assert llc.temporal_scope.reporting_period.label == (
        "Academic years 2022-23, 2023-24, 2024-25"
    )


def test_builder_does_not_infer_unsupported_program_support():
    result = DepartmentContributionBuilder().build(
        (_profile(),), temporal_scope=_scope()
    )[0]
    assert not any(
        item.predicate == ContributionPredicate.SUPPORTS_PROGRAM
        for item in result.assertions
    )


def test_department_object_round_trips_with_identical_fingerprint():
    result = DepartmentContributionBuilder().build(
        (_profile(),),
        temporal_scope=_scope(),
        instructional_attribution=_attribution(),
        llc_attribution=_attribution(llc_only=True),
    )[0]
    restored = DepartmentContributionKnowledgeObject.from_json(
        result.to_json()
    )

    assert isinstance(restored, DepartmentContributionKnowledgeObject)
    assert restored == result
    assert restored.deterministic_fingerprint == result.deterministic_fingerprint
    assert json.loads(result.to_json())["contribution_object_type"] == (
        "department_contribution"
    )
    payload = result.to_dict()
    payload["contribution_object_type"] = "faculty_contribution"
    with pytest.raises(ValueError, match="not a department contribution"):
        DepartmentContributionKnowledgeObject.from_dict(payload)


def test_repeated_builds_and_input_order_are_deterministic():
    profiles = (
        _profile(),
        _profile(
            HISTORY,
            "Department of History",
            courses=("HIST 201",),
        ),
    )
    first = DepartmentContributionBuilder().build(
        profiles, temporal_scope=_scope()
    )
    second = DepartmentContributionBuilder().build(
        reversed(profiles), temporal_scope=_scope()
    )

    assert [item.to_json() for item in first] == [
        item.to_json() for item in second
    ]
    assert [item.deterministic_fingerprint for item in first] == [
        item.deterministic_fingerprint for item in second
    ]


def test_non_department_profiles_and_duplicate_profiles_are_rejected():
    invalid = {
        **_profile(),
        "academic_unit_id": "academic_unit:honors_program",
    }
    with pytest.raises(ValueError, match="not governed as a department"):
        DepartmentContributionBuilder().build(
            (invalid,), temporal_scope=_scope()
        )
    with pytest.raises(ValueError, match="Duplicate Department Profile"):
        DepartmentContributionBuilder().build(
            (_profile(), _profile()), temporal_scope=_scope()
        )


def test_llc_builder_rejects_non_llc_attribution_input():
    with pytest.raises(ValueError, match="LLC-only"):
        DepartmentContributionBuilder().build(
            (_profile(),),
            temporal_scope=_scope(),
            llc_attribution=_attribution(llc_only=False),
        )


def test_incomplete_sch_is_preserved_as_measure_limitation():
    profile = _profile()
    profile["department_owned_instruction"] = {
        **profile["department_owned_instruction"],
        "student_credit_hours": 450.0,
        "sch_complete": False,
    }
    result = DepartmentContributionBuilder().build(
        (profile,), temporal_scope=_scope()
    )[0]
    assertion = next(
        item
        for item in result.assertions
        if item.predicate == ContributionPredicate.DELIVERS_INSTRUCTION_FOR
    )
    measure = next(
        item
        for item in assertion.measures
        if item.measure_type == "student_credit_hours"
    )
    assert measure.value == 450.0
    assert measure.limitations


def test_department_profile_measures_retain_their_actual_temporal_scope():
    result = DepartmentContributionBuilder().build(
        (_profile(),), temporal_scope=_scope()
    )[0]
    assertion = next(
        item
        for item in result.assertions
        if item.predicate == ContributionPredicate.DELIVERS_INSTRUCTION_FOR
    )
    assert assertion.temporal_scope.reporting_period.to_dict() == {
        "start": "2022_fall",
        "end": "2025_spring",
        "label": "All schedule history represented by the Department Profile",
    }
    assert result.temporal_scope == _scope()


def test_builder_does_not_mutate_existing_semantic_inputs():
    profile = _profile()
    attribution = _attribution()
    before_profile = json.dumps(profile, sort_keys=True)
    before_attribution = json.dumps(attribution, sort_keys=True)

    DepartmentContributionBuilder().build(
        (profile,),
        temporal_scope=_scope(),
        instructional_attribution=attribution,
    )

    assert json.dumps(profile, sort_keys=True) == before_profile
    assert json.dumps(attribution, sort_keys=True) == before_attribution
