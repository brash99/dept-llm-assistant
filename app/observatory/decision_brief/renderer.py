from __future__ import annotations

from typing import Any, Optional

from app.observatory.decision_brief.dashboard_v2 import (
    ExecutiveDashboardV2,
)
from app.observatory.topology.impact import ImpactSummary


def render_topology_markdown(
    impact: Optional[ImpactSummary],
) -> str:
    """Render authoritative topology facts."""
    if impact is None:
        return ""

    def bullets(items) -> str:
        if not items:
            return (
                "- None represented in the current topology"
            )

        return "\n".join(
            f"- {item}"
            for item in items
        )

    relationship_word = (
        "relationship"
        if impact.total_relationships == 1
        else "relationships"
    )

    return f"""
## Institutional Topology Assessment

**Entity:** {impact.entity.name}

### Supports

{bullets(impact.supports)}

### Contributes To

{bullets(impact.contributes_to)}

### Supported By

{bullets(impact.supported_by)}

### Receives Contributions From

{bullets(impact.contributed_to_by)}

### Institutional Reach

The current institutional topology records
**{impact.total_relationships} direct institutional {relationship_word}**
for {impact.entity.name}.

### Deterministic Assessment

{impact.narrative()}

> **Topology scope notice:** This is a small, manually curated model of
> institutional relationships. It represents only relationships currently
> encoded in the catalog. Absence of a represented relationship does not
> establish absence of a real-world institutional connection. These
> structural facts are derived from the institutional topology, not from
> retrieved documentary evidence.
""".strip()


def render_decision_brief(
    question: str,
    synthesis_markdown: str,
    observatory_assessment: Any = None,
    evidence_fitness: Any = None,
    topology_impact: Optional[ImpactSummary] = None,
) -> str:
    """Assemble the complete Decision Brief 2.0 knowledge product."""

    dashboard = ExecutiveDashboardV2().render(
        question=question,
        observatory_assessment=observatory_assessment,
        evidence_fitness=evidence_fitness,
        topology_impact=topology_impact,
    )

    sections = [
        dashboard,
        synthesis_markdown.strip(),
        render_topology_markdown(topology_impact),
    ]

    return "\n\n".join(
        section
        for section in sections
        if section
    ).strip()
