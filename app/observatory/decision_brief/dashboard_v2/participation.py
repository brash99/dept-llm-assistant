from __future__ import annotations

from typing import Any

from .common import get_value, percentage, status_symbol
from .contracts import (
    LLC_AREAS_OF_INQUIRY,
    LLC_CORE_REQUIREMENTS,
    InstitutionalParticipationProfile,
    ParticipationFunction,
    ParticipationRelationship,
)


ORGANIZATIONAL_FIELDS = (
    ("college", "College"),
    ("faculty", "Faculty"),
    ("staff", "Staff"),
    ("majors", "Majors"),
    ("minors", "Minors"),
    ("certificates", "Certificates"),
    ("operating_budget", "Operating Budget"),
    ("salary_budget", "Salary Budget"),
    ("physical_space", "Physical Space"),
)


EVIDENCE_COVERAGE_AREAS = (
    (
        "Organizational Context",
        ("Faculty Capacity",),
        "Unit roster, staffing, program ownership, budget, and space records.",
    ),
    (
        "Instructional Participation",
        ("Instructional Demand", "Service Teaching Dependence"),
        (
            "Course-to-program mappings, section capacities, historical "
            "enrollments, prerequisite chains, and laboratory obligations."
        ),
    ),
    (
        "Liberal Learning Core (LLC)",
        ("Service Teaching Dependence",),
        (
            "Course-level LLC designations for Core Requirements and Areas "
            "of Inquiry."
        ),
    ),
    (
        "Institutional Relationships",
        ("Service Teaching Dependence", "Strategic Priority Alignment"),
        (
            "Evidence-backed links to departments, programs, research centers, "
            "facilities, interdisciplinary work, and external partners."
        ),
    ),
    (
        "Institutional Capabilities",
        (
            "Strategic Priority Alignment",
            "Accreditation and External Constraints",
        ),
        (
            "Advising assignments, research supervision, governance, community "
            "engagement, partnerships, and accreditation obligations."
        ),
    ),
    (
        "Functional Substitutability",
        ("One-Line Loss Scenario",),
        (
            "Function-specific alternative providers, their qualifications, "
            "available capacity, and transition constraints."
        ),
    ),
)


def _decision_type_value(evidence_fitness: Any) -> str:
    decision_type = get_value(evidence_fitness, "decision_type")
    value = getattr(decision_type, "value", decision_type)
    return str(value or "").strip().casefold()


def _display_value(value: Any) -> str:
    if value is None or value == "":
        return "Unknown"
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value) or "Unknown"
    return str(value)


def _topology_target(value: Any) -> str:
    target = str(value)
    if target == "General Education":
        return (
            "Legacy curriculum category (recorded as General Education; "
            "LLC mapping not established)"
        )
    return target


def _topology_profile(topology_impact: Any) -> InstitutionalParticipationProfile:
    if topology_impact is None:
        return InstitutionalParticipationProfile()

    entity = get_value(topology_impact, "entity")
    entity_type = get_value(entity, "entity_type")
    entity_type_value = getattr(entity_type, "value", entity_type)
    normalized_entity_type = str(
        entity_type_value or ""
    ).strip().casefold()

    if normalized_entity_type not in {"department", "college"}:
        return InstitutionalParticipationProfile()

    academic_unit = get_value(entity, "name")
    metadata = get_value(entity, "metadata", default={}) or {}
    supports = tuple(get_value(topology_impact, "supports", default=()) or ())
    contributes_to = tuple(
        get_value(topology_impact, "contributes_to", default=()) or ()
    )

    relationships = tuple(
        ParticipationRelationship(
            source=academic_unit or "Selected academic unit",
            relationship="supports",
            target=_topology_target(target),
        )
        for target in supports
    ) + tuple(
        ParticipationRelationship(
            source=academic_unit or "Selected academic unit",
            relationship="contributes to",
            target=_topology_target(target),
        )
        for target in contributes_to
    )

    instructional_functions = tuple(
        ParticipationFunction(
            name=f"Support for {_topology_target(target)}",
            evidence_status="indicated_but_incomplete",
            evidence=("Represented in the current institutional topology.",),
            missing_evidence=(
                "Course-level mapping and documentary relationship evidence.",
            ),
        )
        for target in supports
    ) + tuple(
        ParticipationFunction(
            name=(
                "Liberal Learning Core (LLC) instruction"
                if str(target) == "Liberal Learning Core"
                else f"Curricular contribution to {_topology_target(target)}"
            ),
            evidence_status="indicated_but_incomplete",
            evidence=("Represented in the current institutional topology.",),
            missing_evidence=(
                "Course-level mapping and current curricular designation.",
            ),
        )
        for target in contributes_to
    )

    capabilities = tuple(
        ParticipationFunction(
            name=function.name,
            evidence_status=function.evidence_status,
            evidence=function.evidence,
            missing_evidence=function.missing_evidence,
        )
        for function in instructional_functions
    )

    return InstitutionalParticipationProfile(
        academic_unit=academic_unit,
        organizational_context=dict(metadata),
        instructional_functions=instructional_functions,
        relationships=relationships,
        capabilities=capabilities,
    )


def _function_key(function: ParticipationFunction) -> tuple[Any, ...]:
    """Return a stable identity without merging substantively different uses."""
    return (
        function.name,
        function.evidence_status,
        function.evidence,
        function.missing_evidence,
        function.substitutability_status,
        function.alternative_providers,
    )


def _combined_functions(
    profile: InstitutionalParticipationProfile,
) -> tuple[ParticipationFunction, ...]:
    combined = (
        profile.instructional_functions
        + profile.capabilities
    )
    seen: set[tuple[Any, ...]] = set()
    result = []

    for function in combined:
        key = _function_key(function)
        if key in seen:
            continue
        seen.add(key)
        result.append(function)

    return tuple(result)


def _alternative_provider_text(function: ParticipationFunction) -> str:
    status = function.substitutability_status

    if status == "Substitutability not assessed":
        return "Not assessed"
    if status == "Insufficient evidence":
        return "Not established from supplied evidence"
    if status == "No alternative provider evidenced":
        return "No alternative provider established by supplied evidence"
    if status == "Potential alternative providers indicated":
        return (
            "Potential providers indicated — "
            + ", ".join(function.alternative_providers)
        )
    return ", ".join(function.alternative_providers)


class InstitutionalParticipationProfilePanel:
    """Render evidence-backed participation without scoring academic units."""

    @staticmethod
    def _render_functions(
        functions: tuple[ParticipationFunction, ...],
    ) -> list[str]:
        if not functions:
            return [
                "- **Not Yet Available:** Function-level relationships have "
                "not been established from current evidence."
            ]

        lines: list[str] = []
        for function in functions:
            status = function.evidence_status.replace("_", " ").title()
            evidence = "; ".join(function.evidence) or "Unknown"
            missing = "; ".join(function.missing_evidence) or "Not Yet Available"
            lines.extend(
                [
                    f"#### {function.name}",
                    "",
                    f"- **Evidence Status:** {status}",
                    f"- **Available Evidence:** {evidence}",
                    f"- **Unresolved Evidence:** {missing}",
                    "",
                ]
            )
        return lines

    @staticmethod
    def _coverage_text(
        topics: tuple[str, ...],
        topic_grades: dict[str, Any],
        topic_support: dict[str, Any],
    ) -> str:
        parts = []
        for topic in topics:
            grade = str(topic_grades.get(topic, "unavailable"))
            support = topic_support.get(topic, {}) or {}
            score = percentage(support.get("score"))
            score_text = f"{score:.0f}%" if score is not None else "unavailable"
            parts.append(
                f"{topic}: {status_symbol(grade)} "
                f"{grade.replace('_', ' ').title()} ({score_text})"
            )
        return "; ".join(parts)

    def render(
        self,
        evidence_fitness: Any = None,
        topology_impact: Any = None,
        participation_profile: InstitutionalParticipationProfile | None = None,
    ) -> str:
        if _decision_type_value(evidence_fitness) != "academic_workforce_planning":
            return ""

        profile = participation_profile or _topology_profile(topology_impact)
        question_scope = str(
            get_value(evidence_fitness, "question_scope", default="unresolved")
            or "unresolved"
        ).casefold()
        comparative_scope = question_scope in {"institution_wide", "multi_entity"}
        scope_label = str(
            get_value(
                evidence_fitness,
                "question_scope_label",
                default=(
                    "Multi-Entity Comparison"
                    if question_scope == "multi_entity"
                    else "Institution-Wide Academic Workforce Planning"
                ),
            )
        )
        if comparative_scope and participation_profile is None:
            profile = InstitutionalParticipationProfile()
        unit = (
            "Not applicable — comparative multi-unit analysis required"
            if comparative_scope
            else profile.academic_unit or "Not Yet Available"
        )
        topic_grades = get_value(
            evidence_fitness,
            "topic_grades",
            default={},
        ) or {}
        topic_support = get_value(
            evidence_fitness,
            "topic_support",
            default={},
        ) or {}

        lines = [
            "## Institutional Participation Profile",
            "",
            f"**Selected Academic Unit:** {unit}",
            "",
            *(
                [
                    f"**Question Scope:** {scope_label}",
                    "",
                    (
                        "Institution-wide comparison required. Unit-level "
                        "participation profiles are not yet available."
                    ),
                    "",
                ]
                if comparative_scope
                else []
            ),
            (
                "This profile describes evidenced and unresolved institutional "
                "participation. It does not score the academic unit, rank "
                "departments or faculty, recommend a workforce reduction, or "
                "determine whether a reduction should occur."
            ),
            "",
            "### 1. Organizational Context",
            "",
            f"- **Academic Unit:** {unit}",
        ]

        for key, label in ORGANIZATIONAL_FIELDS:
            lines.append(
                f"- **{label}:** "
                f"{_display_value(profile.organizational_context.get(key))}"
            )

        lines.extend(
            [
                "",
                "### 2. Instructional Participation",
                "",
                *self._render_functions(profile.instructional_functions),
                "#### Participation Areas Not Yet Established",
                "",
                (
                    "- Owned-program instruction, LLC course designations, "
                    "prerequisite instruction, cross-program teaching, "
                    "elective/service teaching, and laboratory instruction "
                    "remain Unknown unless represented above."
                ),
                "",
                "### 3. Institutional Relationships",
                "",
            ]
        )

        if profile.relationships:
            for relationship in profile.relationships:
                evidence = (
                    "; ".join(relationship.evidence)
                    if relationship.evidence
                    else "Supporting source not attached"
                )
                lines.append(
                    f"- **{relationship.source}** "
                    f"{relationship.relationship} **{relationship.target}** "
                    f"— {evidence}."
                )
        else:
            lines.append(
                "- **Not Yet Available:** No evidence-backed institutional "
                "relationships are available for the selected unit."
            )

        lines.extend(
            [
                "",
                (
                    "Relationships with other departments, interdisciplinary "
                    "programs, research centers, facilities, external partners, "
                    "and prerequisite chains remain Unknown unless shown above."
                ),
                "",
                "### 4. Institutional Capabilities Supported",
                "",
                "#### Evidenced Capabilities",
                "",
            ]
        )

        evidenced = tuple(
            capability
            for capability in profile.capabilities
            if capability.evidence_status == "evidenced"
        )
        indicated = tuple(
            capability
            for capability in profile.capabilities
            if capability.evidence_status == "indicated_but_incomplete"
        )
        not_assessed = tuple(
            capability
            for capability in profile.capabilities
            if capability.evidence_status == "not_yet_assessed"
        )
        lines.extend(self._render_functions(evidenced))
        lines.extend(["", "#### Indicated but Incomplete", ""])
        lines.extend(self._render_functions(indicated))
        lines.extend(
            [
                "",
                "#### Not Yet Assessed",
                "",
            ]
        )
        lines.extend(self._render_functions(not_assessed))
        lines.extend(
            [
                "",
                (
                    "Undergraduate research, student advising, specialized "
                    "facilities, accreditation support, faculty governance, "
                    "community engagement, and external partnerships remain "
                    "not assessed unless represented above."
                ),
                "",
                "### 5. Functional Substitutability",
                "",
                (
                    "Substitutability is assessed by institutional function, "
                    "not by assigning a value or substitutability label to the "
                    "academic unit."
                ),
                "",
            ]
        )

        functions = _combined_functions(profile)
        if functions:
            for function in functions:
                lines.extend(
                    [
                        f"#### {function.name}",
                        "",
                        (
                            "- **Alternative-provider status:** "
                            f"{function.substitutability_status}"
                        ),
                        (
                            "- **Alternative providers:** "
                            f"{_alternative_provider_text(function)}"
                        ),
                        "",
                    ]
                )
        else:
            lines.append(
                "- **Substitutability not assessed:** No supported functions "
                "are available for function-level review."
            )

        lines.extend(["", "### 6. Evidence Coverage", ""])
        for area, topics, missing in EVIDENCE_COVERAGE_AREAS:
            lines.extend(
                [
                    f"#### {area}",
                    "",
                    (
                        "- **Available Evidence:** The current question-level "
                        "Evidence Fitness assessment covers: "
                        + ", ".join(topics)
                        + "."
                    ),
                    (
                        "- **Evidence Fitness:** "
                        f"{self._coverage_text(topics, topic_grades, topic_support)}"
                    ),
                    (
                        "- **Missing Evidence:** Unit-specific completeness, "
                        "recency, and relationship provenance are not established "
                        "by the question-level assessment."
                    ),
                    f"- **Additional Evidence Needed:** {missing}",
                    "",
                ]
            )

        lines.extend(
            [
                "### Liberal Learning Core Reference",
                "",
                (
                    "- **Core Requirements:** "
                    + ", ".join(LLC_CORE_REQUIREMENTS)
                ),
                (
                    "- **Areas of Inquiry:** "
                    + ", ".join(LLC_AREAS_OF_INQUIRY)
                ),
                (
                    "- These categories define the LLC reference frame; they "
                    "do not establish that the selected unit participates in "
                    "any category without course-level evidence."
                ),
            ]
        )

        return "\n".join(lines)
