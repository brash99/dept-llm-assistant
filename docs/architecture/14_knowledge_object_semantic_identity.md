# Knowledge Object Semantic Identity

## Ontological position

The Institutional Semantic Observatory treats Knowledge Objects as the
authoritative statements of what exists in its represented institutional
universe.

> Knowledge Objects store facts. Services derive meaning.

Semantic identity answers factual questions before retrieval begins:

- What kind of object is this?
- Which institutional entities does it describe or concern?
- Who published it and what authority does it carry?
- What organizational relationships does the source assert?
- What time period does it describe?
- Which decision domains may legitimately use the evidence, when explicitly
  established?

It does not answer whether an object is relevant to a particular query, whether
its evidence is sufficient, or what decision should be made.

## Identity and representation

```text
Institutional facts
        |
        v
+------------------------------+
| Knowledge Object             |
|                              |
| semantic_identity            |  authoritative factual identity
| provenance                   |  source and preservation history
| text / factual observations  |
+------------------------------+
        |
        | deterministic inheritance
        v
+------------------------------+
| Chunk                        |  retrieval-sized representation
+------------------------------+
        |
        | embedding
        v
+------------------------------+
| Vector                       |  similarity-search representation
+------------------------------+
```

Neither a chunk nor a vector creates institutional identity. Rebuilding an
embedding may change search behavior, but it must not change what the Knowledge
Object says exists.

## Semantic identity contract

`app/semantic_identity.py` defines a deliberately small extensible framework:

- `SemanticIdentity`
- `InstitutionalEntity`
- `OrganizationalRelationship`
- `Authority`
- `TemporalScope`

An example serialized identity is:

```yaml
semantic_identity:
  object_type: document
  institutional_entities:
    - entity_type: institution
      entity_id: institution:cnu
      published_name: Christopher Newport University
    - entity_type: department
      entity_id: department:english
      published_name: Department of English
  organizational_relationships:
    - relationship_type: published_by
      source: knowledge_object:annual_report
      target: department:english
      evidence_reference: page:1
  decision_domains:
    - academic_workforce_planning
  authority:
    issuing_authority: Department of English
    authority_class: institutional_report
    evidence_role: Departmental Report
  temporal_scope:
    effective_from: 2025-07-01
    effective_until: 2026-06-30
    published_label: Academic Year 2025-26
  institutional_relevance:
    published_scope: departmental
```

The contract is stored inside Knowledge Object metadata to preserve serialized
backward compatibility. `KnowledgeObject.semantic_identity` exposes the typed
contract, and `set_semantic_identity()` validates that its `object_type` agrees
with the enclosing Knowledge Object. It does not alter deterministic IDs.

## Institutional entities

`InstitutionalEntity` is a stable reference, not a complete university
ontology. Initial entity types may include institution, college, department,
program, faculty, and research group. The vocabulary is extensible because
later evidence may require additional entity kinds.

An entity reference preserves factual identifiers and published names. It does
not infer organizational membership, employment category, importance, or
equivalence.

## Organizational relationships

`OrganizationalRelationship` generalizes the Phase I relationship contract.
It can preserve factual assertions such as:

- `belongs_to`
- `published_by`
- `describes`
- `governs`
- `supports`
- `references`
- `concerns`

The vocabulary is not a reasoning rule set. A relationship is recorded only
when supported by evidence or a reviewed factual source. Optional source,
published label, evidence reference, and effective period fields preserve why
the assertion exists.

## Semantic memberships are projections

Semantic identity and semantic membership are different:

```text
SemanticIdentity (authoritative facts)
        |
        | future eligibility service
        v
SemanticMembership (retrieval projection)
        |
        v
RetrievalProfile eligibility
```

For example, an annual report may factually identify its publisher as the
Department of English, concern CNU, and cover academic year 2025–26. A future
service may project those facts into:

```yaml
semantic_memberships:
  - scope: department:english
    provenance: derived
  - scope: institution
    provenance: reviewed
    reviewed_by: reviewer:institutional_research
```

The membership does not replace the publisher, entity, relationship, temporal,
or authority facts from which eligibility was determined.

Phase I supports four membership provenance states:

- `asserted`: directly supplied by an adapter or factual source;
- `reviewed`: confirmed through an explicit review process;
- `proposed`: recorded for review so consumers can distinguish it from an
  accepted membership;
- `derived`: produced by a future deterministic service from identity facts.

Legacy membership strings remain readable. No memberships are automatically
derived in this sprint.

## Future retrieval flow

Current retrieval behavior is unchanged. The intended future flow is:

```text
+---------------------------+
| Knowledge Object facts    |
| - entities                |
| - relationships           |
| - authority               |
| - temporal scope          |
+---------------------------+
              |
              v
+---------------------------+
| Semantic eligibility      |  deterministic service, inspectable rules
+---------------------------+
              |
              v
+---------------------------+
| Retrieval Profile         |  institution / department perspective
+---------------------------+
              |
              v
+---------------------------+
| Metadata filtering        |  membership projection
+---------------------------+
              |
              v
+---------------------------+
| Vector similarity         |  ranking within eligible evidence
+---------------------------+
```

Eligibility must be explainable from Knowledge Object facts. Vector similarity
must never decide what institution, department, program, or authority an object
belongs to.

## Backward compatibility

- Existing Knowledge Objects without `semantic_identity` remain valid.
- Existing top-level metadata projections remain readable.
- Legacy string memberships remain eligible for the Phase I filter.
- Chunk text, deterministic chunk IDs, embeddings, and FAISS records are not
  changed by this contract-only sprint.
- `OrganizationalRelationship` remains importable from `app.semantic_scope`
  while its authoritative definition now lives in `app.semantic_identity`.

## Migration plan

1. Add semantic identity only through adapters that can cite source facts.
2. Validate identity completeness and provenance without requiring it from
   legacy objects.
3. Introduce reviewed adapters for high-value institutional entity types.
4. Design a deterministic eligibility service with inspectable derivation
   records.
5. Materialize derived memberships only after identity coverage is sufficient.
6. Rebuild derived artifacts through the ordinary operator workflow when an
   intentional backfill occurs.
7. Let Evidence Fitness assess identity, authority, temporal, and scope gaps.
8. Let Scenario Modeling consume factual entities and relationships rather than
   vector neighborhoods.

The Institutional Digital Twin may eventually build on these contracts, but it
does not determine their current scope.
