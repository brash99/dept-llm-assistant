from __future__ import annotations

from typing import Any

from .common import get_value, percentage, status_symbol
from .contracts import ACADEMIC_WORKFORCE_PLANNING_DOMAINS


ACADEMIC_WORKFORCE_EVIDENCE_MAP = {
    "Instructional Demand": {
        "relevance": (
            "Measures teaching demand and workload; shows where instructional "
            "capacity is needed to serve students."
        ),
        "required": (
            "Student credit hours, section enrollments, class sizes, and "
            "teaching-workload data."
        ),
    },
    "Faculty Capacity": {
        "relevance": (
            "Measures available faculty staffing and teaching capacity; shows "
            "whether obligations can be covered sustainably."
        ),
        "required": (
            "Faculty headcount and FTE, teaching assignments, normal loads, "
            "adjunct use, vacancies, retirements, and attrition."
        ),
    },
    "Service Teaching Dependence": {
        "relevance": (
            "Measures teaching provided across programs; identifies staffing "
            "effects that extend beyond a department's own majors."
        ),
        "required": (
            "Service-course and non-major enrollments, general-education "
            "obligations, prerequisites, and cross-program dependencies."
        ),
    },
    "Accreditation and External Constraints": {
        "relevance": (
            "Measures binding external staffing constraints; identifies limits "
            "that workforce changes must continue to satisfy."
        ),
        "required": (
            "Program accreditation, licensure, faculty-count, qualification, "
            "and regulatory requirements."
        ),
    },
    "Enrollment Trends": {
        "relevance": (
            "Measures sustained student demand and completions; distinguishes "
            "multi-year patterns from a single enrollment snapshot."
        ),
        "required": (
            "Multi-year major enrollment, completions, applications, yield, "
            "retention, and relevant demand trends."
        ),
    },
    "Financial Implications": {
        "relevance": (
            "Measures costs, savings, and revenue effects; makes financial "
            "assumptions visible without treating them as the sole criterion."
        ),
        "required": (
            "Instructional costs, faculty compensation, savings assumptions, "
            "revenue effects, and resource-allocation data."
        ),
    },
    "Strategic Priority Alignment": {
        "relevance": (
            "Measures connection to mission and strategic priorities; ensures "
            "workforce analysis reflects institutional commitments."
        ),
        "required": (
            "Authoritative strategic priorities, mission-critical functions, "
            "and relevant state, regional, or workforce priorities."
        ),
    },
    "One-Line Loss Scenario": {
        "relevance": (
            "Measures operational exposure to losing one faculty line; reveals "
            "coverage, continuity, and program-viability risks."
        ),
        "required": (
            "Post-loss course and schedule coverage, required-course and "
            "program effects, expertise gaps, succession, and replacement risks."
        ),
    },
}


def _decision_type_value(evidence_fitness: Any) -> str:
    decision_type = get_value(evidence_fitness, "decision_type")
    value = getattr(decision_type, "value", decision_type)
    return str(value or "").strip().casefold()


def _count_text(count: Any, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


class AcademicWorkforceEvidenceMapPanel:
    """Render evidence structure without evaluating workforce alternatives."""

    @staticmethod
    def _support_text(grade: str, support: dict[str, Any]) -> str:
        score = percentage(support.get("score"))
        score_text = f"{score:.0f}%" if score is not None else "score unavailable"
        label = grade.replace("_", " ").title()
        return f"{status_symbol(grade)} {label}; {score_text}"

    @staticmethod
    def _available_text(support: dict[str, Any]) -> str:
        if not support:
            return "No support details reported."

        sources = support.get("sources")
        keywords = support.get("keywords")
        details = []

        if sources is not None:
            details.append(_count_text(sources, "supporting source", "supporting sources"))
        if keywords is not None:
            details.append(_count_text(keywords, "keyword concept", "keyword concepts"))

        return "; ".join(details) if details else "No support counts reported."

    @staticmethod
    def _required_text(grade: str, domain: str) -> str:
        required = ACADEMIC_WORKFORCE_EVIDENCE_MAP[domain]["required"]

        if grade.casefold() == "strong":
            return (
                "Current corpus support is strong; confirm recency, unit-level "
                "coverage, and decision-specific completeness before use."
            )
        if grade.casefold() == "partial":
            return f"Additional corroboration or coverage: {required}"
        return required

    def render(self, evidence_fitness: Any = None) -> str:
        if _decision_type_value(evidence_fitness) != "academic_workforce_planning":
            return ""

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
            "## Academic Workforce Evidence Map",
            "",
            (
                "This map identifies decision evidence, not a workforce "
                "recommendation. Evidence support does not determine which "
                "departments should lose positions; strategic priorities, "
                "accreditation obligations, institutional mission, and human "
                "judgment remain necessary."
            ),
            "",
        ]

        for domain in ACADEMIC_WORKFORCE_PLANNING_DOMAINS:
            metadata = ACADEMIC_WORKFORCE_EVIDENCE_MAP[domain]
            grade = str(topic_grades.get(domain, "unavailable"))
            support = topic_support.get(domain, {}) or {}
            lines.extend(
                [
                    f"### {domain}",
                    "",
                    f"- **Decision Relevance:** {metadata['relevance']}",
                    (
                        "- **Current Support:** "
                        f"{self._support_text(grade, support)}"
                    ),
                    (
                        "- **Evidence Available:** "
                        f"{self._available_text(support)}"
                    ),
                    (
                        "- **Evidence Still Required:** "
                        f"{self._required_text(grade, domain)}"
                    ),
                    "",
                ]
            )

        return "\n".join(lines)
