# Semantic Derived-Data Pipeline Operations

`scripts/semantic_pipeline.py` is the canonical operational interface for the bounded derived-data dependency chain:

```text
normalized Knowledge Objects
  -> chunks
  -> normalized sentence-transformer embeddings
  -> FAISS IndexFlatIP index and metadata records
```

The command orchestrates the existing `app.chunk.run_chunking`, `app.embed.embed_chunks`, and `app.vector_index.build_faiss_index` implementations. It does not normalize or classify evidence, synchronize Google Drive, acquire sources, change retrieval ranking, call an LLM, or deploy ISO.

## Status meanings

- `CURRENT`: the artifact agrees with a successful pipeline manifest and its immediate dependency.
- `STALE`: a dependency fingerprint, configured embedding model, or upstream state changed after the recorded build.
- `MISSING`: required artifacts are absent.
- `INCONSISTENT`: artifacts are unreadable or structural counts/dimensions disagree.
- `UNKNOWN`: artifacts are structurally inspectable, but no durable pipeline manifest establishes freshness.

Status prefers recorded fingerprints and counts over timestamps. Timestamps are displayed as operational context only. An index built before this tool will normally be `UNKNOWN`, not falsely labeled current. Status is read-only and does not load the embedding model or reranker.

```bash
PYTHONPATH="$PWD" python3 scripts/semantic_pipeline.py status
PYTHONPATH="$PWD" python3 scripts/semantic_pipeline.py status --json
```

## Dry-run preflight

Always run preflight first:

```bash
PYTHONPATH="$PWD" python3 scripts/semantic_pipeline.py rebuild --dry-run
```

It resolves configured paths, counts normalized objects, reports current artifacts, planned replacements and backups, model/device configuration, expected GPU use, free disk space, optional dependencies, filesystem compatibility, and incomplete staging runs. It creates no directories, caches, models, manifests, chunks, embeddings, or index files.

## Safe rebuild and promotion

```bash
PYTHONPATH="$PWD" python3 scripts/semantic_pipeline.py rebuild
```

The rebuild:

1. creates a unique marked run under `storage/.semantic_pipeline_staging/`;
2. builds chunks, embeddings, and the vector database entirely in that run;
3. performs structural and Semantic Identity propagation verification;
4. moves existing configured artifacts to `storage/.semantic_pipeline_backups/<run-id>/`;
5. atomically renames each staged directory into its configured location;
6. verifies the promoted pipeline again; and
7. restores the immediately previous artifacts automatically if promotion or post-promotion verification fails.

Directory replacement is sequential, not a distributed transaction. The script validates that staging and all targets reside on the same filesystem and rolls back already-promoted stages if a later rename fails. Backups are retained; there is no automatic retention deletion in v1.

The build manifest is written to:

```text
<configured vector_db>/semantic_pipeline_manifest.json
```

It records the run and commit, normalized dependency fingerprint, counts and fingerprints, chunk configuration, embedding model/dimension/normalization/context/device, FAISS type and counts, configured/staged/backup paths, verification results, and semantic metadata coverage.

## Verification

```bash
PYTHONPATH="$PWD" python3 scripts/semantic_pipeline.py verify
PYTHONPATH="$PWD" python3 scripts/semantic_pipeline.py verify --json
```

Verification checks:

- readable, unique chunks mapped to existing Knowledge Objects;
- embedding/chunk identity equality, dimensions, model, finite values, and unit norms;
- FAISS/embedding/record counts and dimensions;
- unique FAISS metadata mappings;
- a small direct FAISS vector-search smoke check;
- aggregate Semantic Identity coverage; and
- exact normalized-object-to-chunk-to-index metadata equality for representatives of CNU Institutional Research, curated external evidence, SCHEV, SEC Annual Reports, SEC Planning, SEC Program Review, and SEC Statistics.

Reports expose object IDs and field names, not sensitive titles or text. Operational vector smoke checks establish index function, not retrieval quality.

## Failure, incomplete runs, and resume

A stage failure stops the pipeline immediately and never promotes partial output. The marked staging directory remains available for diagnosis. V1 has no resume support because the existing embedding builder has no safe checkpoint contract; a retry starts from the beginning.

The next rebuild refuses to proceed while marked incomplete runs exist. After inspection, removal must be explicit:

```bash
PYTHONPATH="$PWD" python3 scripts/semantic_pipeline.py rebuild --cleanup-staging
```

This removes only children of the configured staging root that contain the pipeline's incomplete-run marker. It does not weaken dependency or verification checks.

## Rollback

Promotion and post-promotion verification failures roll back automatically. For a later operator-initiated rollback:

1. stop Streamlit and other processes that may cache the FAISS index;
2. identify one complete run under `storage/.semantic_pipeline_backups/<run-id>/`;
3. move the current `chunks`, `embeddings`, and `vector_db` directories to a separate quarantine location; and
4. move all three matching backup directories back to the configured locations.

Do not mix stages from different run IDs. Do not delete normalized Knowledge Objects. Re-run `verify` before restarting applications. V1 intentionally provides no automatic arbitrary historical rollback command.

## macOS development workflow

The Mac checkout is typically `/Users/brash/dept-llm-assistant`. It may lack the production corpus, CUDA, model cache, or full vector database. Safe development commands are:

```bash
cd /Users/brash/dept-llm-assistant
export PYTHONPATH="$PWD"
python3 scripts/semantic_pipeline.py status
python3 scripts/semantic_pipeline.py rebuild --dry-run
.venv/bin/python -m pytest -q scripts/test_semantic_pipeline.py
```

Do not run a full Mac rebuild merely to test orchestration. Mutation tests use temporary miniature artifacts.

## Reviewed A100 workflow

Only after Mac review, commit, push, and an operator-approved pull:

```bash
cd /work/brash/dept-llm-assistant
source .venv/bin/activate
export PYTHONPATH="$PWD"

python3 scripts/semantic_pipeline.py status
python3 scripts/semantic_pipeline.py rebuild --dry-run
python3 scripts/semantic_pipeline.py rebuild
python3 scripts/semantic_pipeline.py verify
```

The A100 operator must inspect disk space, dependencies, incomplete runs, resolved paths, model, device, and planned backups in dry-run output before rebuilding. Restart long-lived applications after promotion so their in-memory FAISS caches do not retain the previous index.

## Review and synchronization workflow

1. Implement and test in the Mac checkout.
2. Review the engineering report and diff.
3. Commit and push only after explicit approval.
4. Pull `sprint/academic-workforce-planning` on the A100.
5. Run status and dry-run.
6. Execute rebuild and verify only after operator review.

No pipeline command performs Git synchronization or deployment.
