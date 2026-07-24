# Contribution Ontology Contracts

## Status and scope

This chapter specifies the implemented, entity-neutral foundation of ISO's
contribution ontology. It implements the architectural commitments in
[Institutional Ontology and Explainable Reasoning](40_contribution_ontology.md).
It does not define department, faculty, program, or college contribution
objects, and it contains no report, recommendation, scenario, or LLM behavior.

> Knowledge objects store facts. Services derive meaning.

## Ontological position

`ContributionKnowledgeObject<T>` is ISO's model of the institutional function
of governed entity `T` over an explicit temporal scope. It is not a report about
the entity. Reports will be projections of contribution objects; reasoning will
consume them; scenarios may transform them into explicitly counterfactual
states.

The foundation is intentionally separate from the legacy text-centered
`KnowledgeObject` container. Both belong to the Semantic Layer, but they solve
different representation problems:

- normalized evidence objects preserve source facts as text and metadata;
- contribution objects preserve typed institutional contribution facts.

No inheritance from the text container is required to make a contribution
object ontological.

## Composition

```text
governed institutional entity T
              |
              v
+---------------------------------------------+
| ContributionKnowledgeObject<T>              |
| temporal scope                              |
|                                             |
|  ContributionAssertion                     |
|    subject -- governed predicate --> object |
|    qualifiers                               |
|    evidence bindings                        |
|    attached measures                        |
|                                             |
|  ContributionAssertion ...                 |
+---------------------------------------------+
```

The generic object is an entity-centered, temporally bounded subgraph of
institutional function. Every contained assertion must have the object's entity
as its governed subject.

## Contribution assertions

`ContributionAssertion` is the atomic semantic contract. It contains:

- a governed subject and object, represented by stable
  `InstitutionalEntity` references;
- one governed `ContributionPredicate`;
- assertion qualifiers;
- explicit temporal scope;
- direct evidence bindings and provenance;
- zero or more attached measures.

An assertion is an institutional fact. It does not state how important the
contribution is or what decision follows from it.

The initial predicate vocabulary is deliberately small:

- `administers_program`;
- `supports_program`;
- `owns_curriculum`;
- `provides_service_teaching_for`;
- `delivers_instruction_for`;
- `contributes_to_llc_requirement`;
- `provides_capstone_instruction_for`.

Unknown free-text predicates are rejected. Expansion requires an explicit
ontology change rather than accidental vocabulary growth.

## Measures are properties

`ContributionMeasure` attaches a quantitative property to an assertion. Its
contract includes a measure type, numeric value, unit, definition, qualifiers,
evidence-binding references, and limitations.

```text
ContributionAssertion
        |
        +-- has measure --> section count
        +-- has measure --> enrollment
        +-- has measure --> SCH
```

The assertion remains meaningful when no measure is available. A missing
metric therefore cannot erase a governed contribution relationship.

## Evidence is epistemic grounding

`ContributionEvidenceBinding` is separate from the assertion it establishes.
It records source references, provenance, builder identity and version, source
fingerprints, and the deterministic derivation basis.

```text
Evidence Layer facts
        |
        | deterministic builder
        v
ContributionEvidenceBinding
        |
        | establishes
        v
ContributionAssertion
```

The binding explains how ISO knows the asserted fact. It is not itself the
institutional relationship. Evidence Fitness assessments can later evaluate
fitness for particular uses without changing the assertion.

## Temporal semantics

`ContributionTemporalScope` keeps four dimensions distinct:

- **reporting period**: the interval summarized by attached measures;
- **effective period**: when the institutional relationship is in force;
- **observation period**: when supporting evidence was observed;
- **publication time**: when the semantic object was published.

Each period may have explicit bounds, a governed label, or both. The contract
does not substitute a catalog year for an effective date or a publication
timestamp for an observation period.

## Serialization and identity

Every contract has deterministic dictionary serialization and deserialization.
Contribution assertions and contribution objects expose SHA-256 fingerprints
of canonical semantic content. Collection ordering does not change a
fingerprint, duplicate semantic IDs are rejected, and supplied fingerprints
are checked during deserialization.

Frozen dataclasses are the current engineering mechanism used to protect
published values in memory. Immutability is not an ontological claim. The
ontology requires only that each object model its entity over a stated temporal
scope; persistence and versioning may evolve independently.

## Layer boundaries

- Deterministic builders will construct these semantic objects from evidence.
- Evidence Fitness will assess the suitability and limitations of their
  grounding.
- Reasoning will consume contribution objects without constructing or mutating
  their institutional facts.
- Reports will serialize selected projections.
- Scenario Modeling will create labeled counterfactual transformations rather
  than overwrite the observed contribution baseline.
- LLMs will not author predicates, assertions, measures, or evidence bindings.

Entity-specific contribution models and builders are intentionally deferred.
