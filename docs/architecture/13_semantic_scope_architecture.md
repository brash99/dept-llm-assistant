# Semantic Scope Architecture

## Purpose

Semantic Scope makes the Knowledge Object—not a vector database—the primary
unit of semantic organization. A corpus is a semantic perspective on the
institution, not a storage container. The authoritative facts behind scope are
defined by [Knowledge Object Semantic Identity](14_knowledge_object_semantic_identity.md);
memberships are retrieval projections of that identity.

The persisted hierarchy remains:

```text
Source Document
  -> Knowledge Object (semantic identity and factual metadata)
    -> Chunk (inherits semantic metadata)
      -> Vector (searchable representation of chunk text)
```

No additional FAISS index is introduced in Phase I. A single index can behave
as multiple logical corpora because indexed chunk records carry inherited
Knowledge Object memberships and retrieval can apply an eligibility filter.

## Contracts

`app/semantic_scope.py` defines:

- `SemanticScope`: a registered logical perspective such as `institution` or
  `department:english`;
- `ScopeRegistry`: deterministic resolution of identifiers and aliases;
- `RetrievalProfile`: the rule connecting a retrieval mode to a scope kind;
- `ResolvedRetrievalProfile`: the selected scope and eligible memberships;
- `OrganizationalRelationship`: a small factual relationship contract for
  published organizational assertions.

The older `app.retrieval.RetrievalProfile` dataclass contains retrieval timing
measurements despite its historical name. It remains unchanged as a public
return contract. Semantic profile selection uses
`app.semantic_scope.RetrievalProfile`; a future compatibility release may give
the timing contract a clearer name.

The initial profiles are:

| Profile | Selector | Eligible membership |
|---|---|---|
| `institution` | none | `institution` |
| `department` | department identifier or alias | resolved `department:*` scope |

The registry at `config/semantic_scopes.yaml` contains the institution, the
departments published in the 2025–26 catalog, and the former PCSE department as
an explicitly historical scope. Registry status is descriptive; it does not
delete or reinterpret longitudinal evidence.

## Knowledge Object metadata

Knowledge Objects may carry these optional metadata fields:

```yaml
semantic_memberships:
  - institution
  - department:english
organizational_relationships:
  - relationship_type: belongs_to
    target: department:english
    published_label: Department of English
decision_domains:
  - academic_workforce_planning
institutional_relevance:
  published_scope: university-wide
```

`semantic_memberships` is intentionally plural. One fact object may
participate in several perspectives. Memberships are projections rather than
the primary ontology and may carry `asserted`, `reviewed`, `proposed`, or
`derived` provenance. They are not inferred from filenames by the retrieval
layer.

The other fields establish extension points rather than a complete ontology:

- organizational relationships store published factual relationships;
- decision domains identify explicitly supported decision contexts;
- institutional relevance stores factual relevance metadata where a source
  supplies it.

They must not contain derived rankings, recommendations, replaceability, or
other reasoning conclusions.

## Metadata inheritance

The generic chunking service copies all four fields from Knowledge Object
metadata into chunk metadata. This applies to ordinary documents,
constitutional objects, schedule observations, faculty observations, and
catalog observations. Chunk text and identifiers are unchanged.

Embeddings remain representations of chunk text. They do not become the source
of semantic membership, organizational identity, or decision meaning.

## Retrieval API

Existing calls remain unchanged:

```python
results, report, profile = retrieve(
    query="faculty capacity",
    vector_db_dir=vector_db,
    model_name=model,
)
```

Optional profile-aware calls are now supported:

```python
results, report, timing = retrieve(
    query="faculty capacity",
    vector_db_dir=vector_db,
    model_name=model,
    profile="institution",
)

results, report, timing = retrieve(
    query="service teaching obligations",
    vector_db_dir=vector_db,
    model_name=model,
    profile="department",
    department="english",
)
```

`search_index()` still searches the one configured FAISS index. When a profile
is supplied, it retains only records whose `semantic_memberships` intersect the
resolved eligible memberships. Constitutional fallback uses the same filter.
When no profile is supplied, no filter is applied and behavior is backward
compatible.

Profile filtering is strict: legacy records without semantic memberships are
not silently included in a scoped result. This makes incomplete migration
visible rather than manufacturing membership.

## Phase I limitations

- Existing objects and index records have not been backfilled.
- Profile-aware retrieval will return only objects already carrying inherited
  membership metadata.
- Filtering occurs after FAISS candidate ranking. A rare eligible membership
  may require a larger `fetch_k`; Phase I does not add a metadata-aware ANN
  engine.
- Membership does not imply access control, ownership, value, relevance, or
  decision fitness.
- Faculty, programs, research groups, and other entities remain relationships
  or first-class semantic entities as appropriate; they do not automatically
  become independent corpora.

## Migration path

1. Add evidence-backed memberships in normalization adapters and curated
   backfill utilities.
2. Re-chunk and rebuild derived embeddings/index artifacts only through the
   normal controlled operator workflow.
3. Measure scoped recall, missing membership coverage, and required `fetch_k`.
4. Add profile composition or relationship traversal only when decision use
   cases require it.
5. Consider physical index partitioning only if measured scale, isolation, or
   latency requirements cannot be met by one index plus metadata filtering.

If physical indexes are ever introduced, the Scope Registry and Knowledge
Object memberships remain authoritative. Physical placement must be a derived
deployment decision and must never become the semantic ontology.

## Invariants

1. Knowledge Objects store facts; services derive meaning.
2. A corpus is a semantic perspective, not a storage path.
3. Membership is many-to-many and provenance-bearing.
4. Chunks inherit meaning; they do not create it.
5. Vectors support search and are never authoritative semantic records.
6. Missing membership remains missing.
7. Unscoped retrieval remains compatible throughout incremental migration.
