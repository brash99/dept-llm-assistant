# Institutional Semantic Observatory

The Institutional Semantic Observatory (ISO) is an evidence-centered decision-support system for Christopher Newport University. It acquires governed institutional sources, preserves provenance in Knowledge Objects, retrieves relevant evidence, derives deterministic semantic and evidence-fitness assessments, and produces citation-grounded answers and Decision Briefs.

ISO’s governing principle is:

> Knowledge Objects store facts. Services derive meaning.

The system must not manufacture a recommendation when the available evidence is inadequate.

## Permanent architecture

ISO uses one permanent six-layer architecture:

1. **Evidence Layer** — acquisition, manifests, normalization, Knowledge Objects, constitutional objects, chunking, embeddings, FAISS indexing, retrieval, reranking, exact deduplication, and document-family diversity.
2. **Semantic Layer** — institutional program orientation, constitutional orientation, deterministic question scope, evidence classes and roles, and institutional topology context.
3. **Reasoning Layer** — grounded question answering, Decision Brief synthesis, deterministic dashboard products, and claim-safety rules.
4. **Evidence Fitness** — decision-type classification, domain-level support grading, directness, authority, scope, breadth, document-family independence, missing evidence, and decision readiness.
5. **Scenario Modeling** — planned; no production scenario engine or departmental reduction model is implemented.
6. **Institutional Digital Twin** — aspirational long-term objective; the current topology and participation profile are limited precursors, not a complete digital twin.

See [Architecture Overview](docs/architecture/01_architecture_overview.md) and [Current Status](docs/status.md).

## Current milestone

The active Academic Workforce Planning benchmark asks whether available institutional evidence can support reducing approximately 275 full-time faculty positions to approximately 250 and allocating reductions across departments. The current implementation:

- detects institution-wide and multi-unit scope;
- refuses to select one academic unit for an institution-wide comparison;
- evaluates eight canonical workforce evidence domains;
- distinguishes institutional self-studies from formal external standards;
- prevents drafts and document-family variants from acting as independent corroboration;
- requires genuine temporal evidence for Enrollment Trends;
- renders the Executive Workforce Decision Framework, Academic Workforce Evidence Map, and Institutional Participation Profile; and
- refuses departmental recommendations when evidence is insufficient.

It does **not** rank departments, score faculty, calculate reduction scenarios, or establish that a workforce reduction should occur.

## Environments

The canonical A100 checkout is:

```text
/work/brash/dept-llm-assistant
```

- For A100 launch, ingestion, indexing, monitoring, and benchmarking, use [A100 Operations](docs/operations/a100.md).
- For local macOS editing and lightweight tests, use [macOS Development](docs/operations/macos.md).
- Do not use macOS paths in server commands or treat a local checkout as the production data environment.

## Documentation map

- [Documentation index](docs/README.md)
- [Current implementation status](docs/status.md)
- [Architecture book](docs/architecture/README.md)
- [A100 operations](docs/operations/a100.md)
- [macOS development](docs/operations/macos.md)
- [Testing](docs/operations/testing.md)
- [Decision Briefs](docs/decision_support/decision_briefs.md)
- [Glossary](docs/reference/glossary.md)

## Safety

Corpus synchronization, clearing derived data, rebuilding embeddings/indexes, deployment, and Git publication change shared state. Inspect commands before running them. In particular, `scripts/sync_drive.sh` uses `rclone sync`, and `scripts/run_full_pipeline.sh` clears derived outputs before rebuilding them.
