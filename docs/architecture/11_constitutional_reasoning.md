# Constitutional Reasoning

ISO preserves institutional values and empirical observations as separate semantic spaces.

## Implemented

- `config/institutional_constitution.yaml` identifies approved source records and declared principles.
- `scripts/build_constitutional_catalog.py` builds Constitutional Knowledge Objects from already normalized sources.
- Chunking and retrieval include constitutional objects alongside normalized empirical objects.
- Constitutional fallback and quotas preserve constitutional evidence in retrieval.
- Constitutional orientation identifies potentially relevant Strategic Compass principles before retrieval.
- Decision Brief citations use a separate `Constitutional Source N` namespace.
- Prompt rules prevent constitutional commitments from becoming unsupported operational facts.

## Correct interpretation

Constitutional evidence can support wording such as “The Strategic Compass prioritizes…” or “The institution states a commitment to…”. It does not establish that a proposal is approved, funded, feasible, implemented, or successful.

Empirical evidence can describe conditions but does not decide which institutional values should prevail. Alignment remains a reasoned human judgment informed by identified sources.

## Partially implemented

- The current constitutional catalog is curated and limited.
- Orientation uses deterministic concept matching.
- The dashboard reports constitutional assessment connectivity, not a complete normative evaluation.
- Leadership approval, conflicts among values, temporal supersession, and authoritative policy interpretation require governance beyond the current service.

## Planned or aspirational

- broader leadership-approved constitutional sources;
- temporal validity and supersession workflows;
- explicit, reviewable alignment assessments; and
- integration with future Scenario Modeling and the Institutional Digital Twin.

Constitutional reasoning belongs primarily to the Semantic and Reasoning layers. It is not a seventh architectural layer.
