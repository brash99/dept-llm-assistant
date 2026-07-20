from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from app.observatory.topology.impact import ImpactSummary

from .ecosystem import EcosystemPanel
from .header import HeaderPanel
from .observatory import ObservatoryPanel
from .readiness import ReadinessPanel
from .workforce import WorkforceDecisionFrameworkPanel


class ExecutiveDashboardV2:
    """Data-driven executive instrument panel."""

    def __init__(self) -> None:
        self.header = HeaderPanel()
        self.readiness = ReadinessPanel()
        self.observatory = ObservatoryPanel()
        self.ecosystem = EcosystemPanel()
        self.workforce = WorkforceDecisionFrameworkPanel()

    def render(
        self,
        question: str,
        observatory_assessment: Any = None,
        evidence_fitness: Any = None,
        topology_impact: Optional[ImpactSummary] = None,
        evidence_count: int | None = None,
        generated_at: datetime | None = None,
    ) -> str:
        sections = [
            self.header.render(
                question=question,
                generated_at=generated_at,
            ),
            self.readiness.render(
                observatory_assessment=observatory_assessment,
                evidence_fitness=evidence_fitness,
            ),
            self.observatory.render(
                observatory_assessment=observatory_assessment,
                evidence_fitness=evidence_fitness,
                topology_impact=topology_impact,
            ),
            self.ecosystem.render(
                observatory_assessment=observatory_assessment,
                evidence_fitness=evidence_fitness,
                evidence_count=evidence_count,
            ),
            self.workforce.render(
                evidence_fitness=evidence_fitness,
            ),
            (
                "> **Observatory note:** All displayed measurements are "
                "derived from connected deterministic services. Capabilities "
                "that are not yet implemented are shown explicitly as "
                "unavailable rather than estimated."
            ),
            "---",
        ]

        return "\n\n".join(
            section.strip()
            for section in sections
            if section and section.strip()
        )
