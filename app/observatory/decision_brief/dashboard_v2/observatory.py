from __future__ import annotations

from typing import Any, Optional

from app.observatory.topology.impact import ImpactSummary

from .common import (
    get_value,
    percentage,
    progress_bar,
    score_label,
    status_symbol,
)


class ObservatoryPanel:
    @staticmethod
    def _topology_status(
        impact: Optional[ImpactSummary],
    ) -> tuple[str, str]:
        if impact is None:
            return (
                "Unavailable",
                "No unambiguous institutional entity was resolved.",
            )

        reach = impact.total_relationships

        if reach >= 7:
            label = "High Reach"
        elif reach >= 3:
            label = "Moderate Reach"
        else:
            label = "Focused Reach"

        relationship_word = (
            "relationship"
            if reach == 1
            else "relationships"
        )

        return (
            label,
            f"{reach} direct institutional {relationship_word}",
        )

    def render(
        self,
        observatory_assessment: Any = None,
        evidence_fitness: Any = None,
        topology_impact: Optional[ImpactSummary] = None,
    ) -> str:
        fitness_score = percentage(
            get_value(
                evidence_fitness,
                "fitness_score",
                "score",
            )
        )
        fitness_label = score_label(fitness_score)

        topology_label, topology_detail = (
            self._topology_status(topology_impact)
        )

        constitutional_available = (
            observatory_assessment is not None
        )

        constitutional_status = (
            "Connected"
            if constitutional_available
            else "Unavailable"
        )

        constitutional_detail = (
            "Constitutional assessment included"
            if constitutional_available
            else "No constitutional assessment supplied"
        )

        rows = [
            (
                "Evidence Fitness",
                progress_bar(fitness_score),
                (
                    f"{status_symbol(fitness_label)} "
                    f"{fitness_label}"
                ),
            ),
            (
                "Constitutional Alignment",
                (
                    f"{status_symbol(constitutional_status)} "
                    f"{constitutional_status}"
                ),
                constitutional_detail,
            ),
            (
                "Institutional Topology",
                (
                    f"{status_symbol(topology_label)} "
                    f"{topology_label}"
                ),
                topology_detail,
            ),
            (
                "Operational State",
                "○ Not connected",
                "Operational observer not yet implemented",
            ),
            (
                "Financial Model",
                "○ Not connected",
                "Financial observer not yet implemented",
            ),
            (
                "Enrollment Model",
                "○ Not connected",
                "Enrollment observer not yet implemented",
            ),
            (
                "Scenario Engine",
                "○ Not connected",
                "Scenario service not yet implemented",
            ),
        ]

        lines = [
            "## Observatory Status",
            "",
            "| Observer | Status | Current Assessment |",
            "|---|---|---|",
        ]

        lines.extend(
            f"| {name} | {status} | {detail} |"
            for name, status, detail in rows
        )

        return "\n".join(lines)
