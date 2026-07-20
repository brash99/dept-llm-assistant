from __future__ import annotations

from typing import Any

from .common import get_value, percentage, status_symbol
from .contracts import (
    ACADEMIC_WORKFORCE_PLANNING_DOMAINS,
)


class WorkforceDecisionFrameworkPanel:
    """Render the deterministic Academic Workforce Planning framework."""

    @staticmethod
    def _evidence_required(grade: str) -> str:
        requirements = {
            "strong": "No additional evidence indicated by the current grade.",
            "partial": "Additional corroborating evidence to reach strong support.",
            "weak": "Additional direct sources and broader evidence coverage.",
            "missing": "Direct evidence for this domain.",
        }
        return requirements.get(
            grade.casefold(),
            "A current domain grade and supporting evidence.",
        )

    def render(self, evidence_fitness: Any = None) -> str:
        decision_type = get_value(
            evidence_fitness,
            "decision_type",
        )

        decision_type_value = getattr(
            decision_type,
            "value",
            decision_type,
        )
        normalized_decision_type = str(
            decision_type_value or ""
        ).strip().casefold()

        if normalized_decision_type != "academic_workforce_planning":
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
            "## Executive Workforce Decision Framework",
            "",
            (
                "This panel reports the current evidence available for the "
                "eight Academic Workforce Planning domains. It identifies "
                "evidence gaps; it does not recommend departmental position "
                "reductions."
            ),
            "",
            (
                "| Evidence Domain | Current Grade | Support | "
                "Evidence Still Required |"
            ),
            "|---|---|---|---|",
        ]

        for domain in ACADEMIC_WORKFORCE_PLANNING_DOMAINS:
            grade = str(topic_grades.get(domain, "unavailable"))
            support = topic_support.get(domain, {}) or {}
            score = percentage(support.get("score"))
            sources = support.get("sources", 0)
            keywords = support.get("keywords", 0)
            score_text = (
                f"{score:.0f}%"
                if score is not None
                else "Unavailable"
            )
            source_word = "source" if sources == 1 else "sources"
            keyword_word = (
                "keyword concept"
                if keywords == 1
                else "keyword concepts"
            )
            support_text = (
                f"{score_text}; {sources} {source_word}; "
                f"{keywords} {keyword_word}"
            )
            grade_label = grade.replace("_", " ").title()

            lines.append(
                f"| {domain} "
                f"| {status_symbol(grade)} {grade_label} "
                f"| {support_text} "
                f"| {self._evidence_required(grade)} |"
            )

        return "\n".join(lines)
