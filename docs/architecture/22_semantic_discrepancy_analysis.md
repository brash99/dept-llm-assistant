# Semantic Discrepancy Analysis

> Evidence Fitness measures not only what ISO knows.
>
> It also measures how well ISO understands what it does not yet know.

Catalogs, schedules, and governed registries answer different factual
questions. A current catalog describes currently published courses. A
longitudinal schedule records courses actually offered across time. Governance
records reviewed institutional ownership. Their prefix sets should not be
expected to match automatically.

## Deterministic explanation

`SemanticDiscrepancyAnalyzer` compares catalog observations, schedule inventory,
and `subject_ownership.yaml`. Every investigated discrepancy receives exactly
one primary explanation, evidence summary, confidence, rationale, next action,
review priority, and deterministic fingerprint.

Categories distinguish current-source differences, historical prefixes,
service and interdisciplinary exceptions, central administration,
graduate-only evidence, parser or structure limitations, schedule
normalization limitations, governance gaps, and genuinely unknown cases.
Rules are ordered so stronger explicit evidence wins. Unknown is preferable to
an invented explanation.

Review priority uses evidence volume, term breadth, ambiguity, and parser
uncertainty. It is an engineering workload signal—not a ranking of academic
importance or institutional value.

## Evidence Fitness

The dashboard reports catalog, schedule, governance, parser, and semantic
completeness; category and confidence distributions; discrepancy volume; and
remaining high/medium/low review workload. Completeness is evidence alignment,
not institutional decision readiness. A well-explained historical or service
exception may be semantically complete even though the sources disagree.

The catalog extraction CLI exposes this analysis through
`--explain-discrepancies` and writes a compact discrepancy CSV alongside the
JSON, Markdown, candidate YAML, candidate CSV, and review queue. It cannot
promote a candidate into governance.

## Architectural role

This capability connects:

1. Evidence Layer — source-specific catalog and schedule observations;
2. Semantic Layer — governed ownership and typed exceptions;
3. Reasoning Layer — deterministic explanation rules;
4. Evidence Fitness — quantified uncertainty and review workload;
5. Scenario Modeling — future consumer of governed, fitness-qualified inputs;
6. Institutional Digital Twin — longer-term temporal institutional model.

It does not implement Scenario Modeling, workload inference, or staffing
recommendations. Disagreement is valuable because it reveals history,
exceptions, governance gaps, and extraction weaknesses that a single-source
view would conceal.
