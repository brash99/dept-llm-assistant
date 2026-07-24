# Configuration Reference

> **Status:** Current operational reference, synchronized July 23, 2026.

Configuration files store governed facts, policies, source definitions, and
runtime settings. Services interpret them; configuration does not contain
derived conclusions.

> Knowledge objects store facts. Services derive meaning.

## Runtime settings

The primary runtime configuration is `config/settings.yaml`. The checked-in
file uses the canonical A100 production root:

```yaml
project:
  root: /work/brash/dept-llm-assistant
```

Do not commit a Mac path as the production project root.

Storage paths are relative to `project.root` unless a script documents
otherwise. Important directories include `normalized`, `constitutional`,
`chunks`, `embeddings`, `vector_db`, `cache`, and `logs`.

Governed normalized evidence may be tracked in the Mac checkout. Its presence
does not prove that it is identical to the current A100 production corpus.
Verify source inventories and deterministic fingerprints before using local
results as production conclusions.

## Semantic and policy registries

### Institutional structure

- `config/institutional_units.yaml` stores governed academic and
  administrative unit identities, canonical names, aliases, formal types,
  current/historical status, supported relationships, analytical roles, and
  eligibility dimensions. It does not store derived workforce assignments.
- `config/subject_ownership.yaml` stores effective-dated governed ownership of
  published schedule subject prefixes. It does not rename source prefixes or
  infer faculty home.
- `config/semantic_scopes.yaml` stores governed scope labels used by semantic
  orientation and unit resolution.
- `config/institutional_programs.yaml` stores governed program identities and
  aliases used by program orientation.

### Faculty identity and workforce

- `config/faculty_identity_aliases.yaml` stores institutionally reviewed
  canonical faculty identities, observed name forms, and review provenance.
  The resolver remains deterministic.
- `config/faculty_identity_match_reviews.yaml` stores durable human decisions
  from schedule-only to governed-identity match review, including approvals,
  rejections, and deferred decisions. Approved reviews may generate governed
  aliases; raw observations remain unchanged.
- `config/analytical_workforce_policy.yaml` stores the versioned default
  include, exclude, and review policy for the analytical workforce, including
  teaching recency and title/role treatment.
- `config/analytical_workforce_overrides.yaml` stores reviewed person-level
  workforce and analytical-unit decisions with reviewer provenance. Overrides
  do not mutate identity or appointment evidence.
- `config/faculty_roster_schema.yaml` defines the canonical contract and
  configurable source-column aliases for future authoritative effective-dated
  faculty-roster ingestion. It is a schema, not a production roster.

### Curriculum

- `config/llc_designations.yaml` stores effective-dated governed Liberal
  Learning Curriculum designation tokens, categories, inclusion rules, and
  section-counting behavior. Published LLC text remains source evidence.
- `config/undergraduate_majors.yaml` stores stable undergraduate-major
  identities, names and aliases, degree facts, status, effective dates when
  known, source-specific ownership assertions, provenance, and limitations.
- `config/undergraduate_major_capstones.yaml` stores governed Major → Capstone
  relationships, requirement types, pathways, course identifiers, catalog
  citations, confidence, and unresolved/no-identifiable cases. It does not
  store estimated graduates.

### Constitutional and evidence governance

- `config/institutional_constitution.yaml` stores curated constitutional source
  records and institutional principles.
- `config/external_evidence_sources.yaml` stores eligible external authorities,
  resources, domains, refresh expectations, extraction methods, versions, and
  geographic scope. Changing it changes acquisition eligibility, not Decision
  Brief conclusions.
- `config/document_classification_registry.yaml` stores governed
  document-routing and classification rules.
- `config/classification_evaluation_cases.yaml` stores deterministic evaluation
  cases for classification policies.
- `config/subject_mapping_review_template.yaml` is a review template; it is not
  authoritative subject ownership.

### Observers and validation

- `config/observers_v2.yaml` stores governed observer definitions.
- `config/web_observers.yaml` stores website observer definitions.
- `config/schev_observers.yaml` stores SCHEV observer definitions.
- `config/retrieval_smoke_tests.yaml` stores governed retrieval smoke-test
  cases.
- `config/models.yaml` is retained model configuration; an empty file asserts
  no additional model entries.

## LLM, embedding, and retrieval settings

`llm.base_url` and `llm.model` identify an OpenAI-compatible inference
endpoint. ISO consumes the endpoint but does not launch or supervise it.

`embedding` selects the sentence-transformer model, batch size, and device.
`reranking` controls the cross-encoder, device, and optional minimum logit.
Reranker logits are not calibrated confidence scores.

`retrieval.fetch_k` controls the broad candidate pool.
`constitutional_top_k` and `empirical_top_k` control final evidence allocation.
Decision Brief retrieval also applies its configured/default document-family
maximum.

## Chunking and normalization

`chunking.chunk_size`, `overlap`, and `max_chunks_per_document` control derived
chunks. Changing these settings requires rebuilding chunks, embeddings, and the
index.

`normalization_sources` is an ordered registry. Each source has a stable key,
root, priority, and description. Lower priority numbers are processed first
and influence which byte-identical source becomes canonical.

List resolved sources before a large run:

```bash
.venv/bin/python -m scripts.normalize_documents --list-sources
```

Configuration changes that alter governed meaning should be reviewed, tested,
and validated against the correct environment before production use.
