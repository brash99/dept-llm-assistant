from __future__ import annotations

from typing import Iterable, Optional

from app.acquisition.external.contracts import AcquisitionPlan, AcquisitionPlanItem
from app.acquisition.external.registry import ExternalSourceRegistry


def _normalize_domain(value: str) -> str:
    return " ".join(value.casefold().replace("/", " ").replace("-", " ").split())


class EvidenceAcquisitionPlanner:
    """Map Evidence Fitness gaps to compatible curated resources."""

    def __init__(self, registry: ExternalSourceRegistry) -> None:
        self.registry = registry

    def plan(self, assessment, missing_domains: Optional[Iterable[str]] = None) -> AcquisitionPlan:
        decision_type = getattr(assessment.decision_type, "value", assessment.decision_type)
        decision_type = str(decision_type)
        decision_label = str(getattr(assessment, "decision_type_label", decision_type))
        domains = tuple(missing_domains if missing_domains is not None else assessment.missing_topics)

        items = []
        mapped = set()
        for domain in domains:
            normalized_domain = _normalize_domain(domain)
            for source in self.registry.sources:
                if decision_type not in source.supported_decision_types:
                    continue
                for resource in source.resources:
                    if normalized_domain not in {_normalize_domain(item) for item in resource.evidence_domains}:
                        continue
                    mapped.add(domain)
                    items.append(
                        AcquisitionPlanItem(
                            evidence_domain=domain,
                            source_key=source.key,
                            resource_id=resource.id,
                            title=resource.title,
                            canonical_url=resource.canonical_url,
                            issuing_authority=source.issuing_authority,
                            authority_class=source.authority_class.value,
                            evidence_role=source.evidence_role,
                        )
                    )

        return AcquisitionPlan(
            decision_type=decision_type,
            decision_label=decision_label,
            missing_domains=domains,
            items=tuple(items),
            unmapped_domains=tuple(domain for domain in domains if domain not in mapped),
        )

    @staticmethod
    def render_dry_run(plan: AcquisitionPlan) -> str:
        lines = [
            f"{plan.decision_label} Evidence Acquisition Plan",
            "",
            "Missing Domains",
            "",
            *[f"✓ {domain}" for domain in plan.missing_domains],
            "",
            "Candidate Authorities",
            "",
            *[f"* {authority}" for authority in plan.candidate_authorities],
            "",
            "Estimated Documents",
            "",
            str(plan.estimated_documents),
            "",
            "Validation Status",
            "",
            "Pending",
        ]
        if plan.unmapped_domains:
            lines.extend(["", "Unmapped Domains", "", *[f"* {item}" for item in plan.unmapped_domains]])
        return "\n".join(lines)
