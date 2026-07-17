from __future__ import annotations

from typing import Any, Optional

from .common import (
    get_value,
    percentage,
    progress_bar,
    score_label,
)


class ReadinessPanel:
    def score(
        self,
        observatory_assessment: Any = None,
        evidence_fitness: Any = None,
    ) -> Optional[float]:
        readiness = percentage(
            get_value(
                observatory_assessment,
                "decision_readiness_score",
                "readiness_score",
                "overall_score",
                "score",
            )
        )

        if readiness is not None:
            return readiness

        return percentage(
            get_value(
                evidence_fitness,
                "fitness_score",
                "score",
            )
        )

    def render(
        self,
        observatory_assessment: Any = None,
        evidence_fitness: Any = None,
    ) -> str:
        readiness = self.score(
            observatory_assessment=observatory_assessment,
            evidence_fitness=evidence_fitness,
        )

        label = score_label(readiness)

        if readiness is None:
            recommendation = (
                "Decision readiness could not be calculated from "
                "the currently connected services."
            )
        elif readiness >= 85:
            recommendation = "Strong evidence base."
        elif readiness >= 70:
            recommendation = (
                "Suitable for review, with identified evidence gaps."
            )
        elif readiness >= 50:
            recommendation = (
                "Additional evidence is recommended before action."
            )
        else:
            recommendation = (
                "Current evidence is insufficient for a reliable decision."
            )

        status = (
            "READY"
            if readiness is not None and readiness >= 85
            else label.upper()
        )

        return "\n".join(
            [
                "## Decision Readiness",
                "",
                f"### {progress_bar(readiness)}",
                "",
                f"**{status}** — {recommendation}",
            ]
        )
