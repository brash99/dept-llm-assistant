from __future__ import annotations

from typing import Any

from .common import (
    as_list,
    display_name,
    get_value,
)


class EcosystemPanel:
    def render(
        self,
        observatory_assessment: Any = None,
        evidence_fitness: Any = None,
    ) -> str:
        covered = as_list(
            get_value(
                evidence_fitness,
                "covered_topics",
                "covered_domains",
                "coverage",
                default=[],
            )
        )

        missing = as_list(
            get_value(
                evidence_fitness,
                "missing_topics",
                "missing_domains",
                "gaps",
                default=[],
            )
        )

        evidence_count = get_value(
            observatory_assessment,
            "evidence_count",
            "retrieved_evidence_count",
            "source_count",
            "document_count",
        )

        lines = [
            "## Knowledge Ecosystem",
            "",
            "| Measure | Current State |",
            "|---|---:|",
            (
                "| Retrieved evidence objects "
                f"| {evidence_count if evidence_count is not None else 'Unavailable'} |"
            ),
            f"| Covered evidence domains | {len(covered)} |",
            f"| Identified evidence gaps | {len(missing)} |",
        ]

        if covered:
            lines.extend(
                [
                    "",
                    "### Covered Domains",
                    "",
                    *[
                        f"- ✓ {display_name(item)}"
                        for item in covered
                    ],
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "*No explicit covered-domain list was supplied by "
                    "the evidence-fitness service.*",
                ]
            )

        if missing:
            lines.extend(
                [
                    "",
                    "### Evidence Gaps",
                    "",
                    *[
                        f"- ⚠ {display_name(item)}"
                        for item in missing
                    ],
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "### Evidence Gaps",
                    "",
                    "- No explicit evidence gaps were reported.",
                ]
            )

        return "\n".join(lines)
