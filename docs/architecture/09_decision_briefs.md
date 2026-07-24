# Decision Briefs

A Decision Brief is the primary executive knowledge product of the current Reasoning Layer. It organizes retrieved evidence, deterministic service assessments, uncertainty, and missing information. It supports human judgment; it is not an autonomous recommendation engine.

## Current execution path

1. The application receives the institutional question.
2. The Semantic Control Plane produces institutional and constitutional orientation and deterministic question scope.
3. Retrieval returns a diversified constitutional/empirical evidence set.
4. Evidence services assign stable citation identities, classes, and roles.
5. Evidence Fitness classifies the decision and grades its expected domains.
6. Topology context is resolved only when the question permits one unambiguous entity.
7. A governed prompt sends the question, evidence, roles, fitness limitations, and permitted topology context to the configured LLM.
8. Dashboard V2 and authoritative topology Markdown are rendered deterministically around the synthesis.
9. `DecisionBrief.raw_markdown` contains the final rendered product.

## Claim safety

The governed prompt requires the model to distinguish:

- institutional values from empirical facts;
- current institutional records from planning documents;
- historical evidence from current conditions;
- formal external requirements from institutional self-study assertions;
- local practice from universal requirements;
- external comparators from evidence about CNU; and
- documentary findings from topology-derived structural context.

A self-study statement must not become a universal accreditation rule unless a retrieved formal standard supports it. When applicability or current compliance is unknown, the brief must preserve that uncertainty.

## Stable citations

Constitutional and empirical sources have separate numbering namespaces. Evidence is grouped for the prompt without changing those identities. The executive source list displays citation label, evidence class, and title; uncalibrated retrieval logits remain in Developer Mode.

## Deterministic dashboard products

Implemented panels include:

- Decision Readiness;
- Observatory Status;
- Knowledge Ecosystem;
- Executive Workforce Decision Framework;
- Academic Workforce Evidence Map; and
- Institutional Participation Profile.

Panels render existing service contracts and deterministic explanatory metadata. They do not retrieve additional evidence or call an LLM.

## Academic Workforce Planning

The eight canonical domains are:

1. Instructional Demand
2. Faculty Capacity
3. Service Teaching Dependence
4. Accreditation and External Constraints
5. Enrollment Trends
6. Financial Implications
7. Strategic Priority Alignment
8. One-Line Loss Scenario

The workforce framework reports grades, support counts, unique document families, and remaining evidence. The evidence map explains domain relevance, available support, and evidence still required. The participation profile describes evidence-backed unit functions and dependencies when a valid academic unit/profile exists.

Institution-wide questions render:

```text
Selected Academic Unit: Not applicable — comparative multi-unit analysis required
```

Without comparable unit profiles and scenario inputs, the brief must not recommend which departments should lose positions.

## Implemented versus future

### Implemented

- evidence-grounded LLM synthesis;
- Evidence Fitness guidance;
- deterministic workforce and participation panels;
- constitutional/empirical separation;
- topology scope notices;
- stable citations; and
- explicit Missing Information and Recommended Follow-Up sections.

### Planned

- structured Scenario Modeling outputs;
- comparable institution-wide unit collections;
- financial and enrollment model integration; and
- scenario-specific course, capability, substitution, and accreditation effects.

### Not implemented

- department rankings;
- faculty rankings;
- automatic position-reduction recommendations;
- a complete institutional ontology or digital twin; and
- guaranteed validation of arbitrary generated prose.

See [Decision Brief product guide](../decision_support/decision_briefs.md) and [Current Status](../status.md).
