# Semantic Control Plane

The Semantic Control Plane is an implemented Semantic Layer subsystem that interprets a question before evidence retrieval. It performs deterministic orientation, not retrieval, evidence grading, scenario analysis, or recommendation.

## Institutional orientation

The program catalog stores asserted program facts and aliases. `ProgramResolver` prefers longer/full-name matches. High-risk short aliases—one or two characters or common English words—must match exact capitalization, token boundaries, and nearby academic context.

Consequently:

- lowercase grammatical `is` does not resolve to Information Science;
- bare uppercase `IS` without academic context is rejected;
- `IS program`, `students majoring in IS`, and `Information Science major` can resolve when supported by the catalog; and
- diagnostics explain high-risk alias acceptance or rejection.

Semantic program neighbors are advisory context. They are not asserted entities.

## Question scope

The deterministic scope contract supports:

- `single_entity`;
- `multi_entity`;
- `institution_wide`; and
- `unresolved`.

Academic Workforce Planning indicators include institution-wide language, comparison across departments/units, total faculty reductions, and allocation across units. Scope classification does not depend on Quentin’s exact benchmark wording.

When scope is institution-wide or multi-entity:

- program mentions remain contextual;
- one topology node is not forced as the primary entity;
- Liberal Learning Core context cannot override comparative scope; and
- the participation panel reports that comparative unit-level analysis is required.

## Constitutional orientation

Constitutional orientation matches question concepts to configured Constitutional Knowledge Objects, currently including Strategic Compass principles. It identifies potentially relevant values before retrieval but does not determine constitutional alignment, approval, feasibility, funding, or outcome.

## Boundaries

- Catalog entities and Knowledge Objects store facts.
- Orientation services derive question context.
- Retrieval still receives the user’s institutional question.
- Evidence Fitness independently classifies decision type and adequacy.
- The LLM cannot create or override the deterministic scope or resolved entity contract.

## Partial capabilities

- Catalog coverage is incomplete.
- Only one program is currently resolved by `ProgramResolver`; multi-entity scope prevents a false primary selection but does not create a full entity collection.
- Neighbor models require sentence-transformer dependencies.
- Scope rules are deterministic phrase patterns and may leave implicit questions unresolved.
