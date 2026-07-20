# ISO AI Engineering Context

This is the canonical engineering onboarding guide for the Institutional
Semantic Observatory (ISO). Read it before changing the repository. It is an
implementation-oriented map of the current system, not a product overview or
a replacement for the README.

The canonical production checkout is:

```text
/work/brash/dept-llm-assistant
```

Local macOS checkouts are useful for editing and deterministic tests, but they
do not contain the production corpus, FAISS index, GPU runtime, or local LLM by
default.

## 1. Project Overview

ISO is an evidence-centered institutional decision-support system for
Christopher Newport University. It acquires and normalizes institutional and
external evidence, represents that evidence as provenance-bearing Knowledge
Objects, retrieves relevant evidence, assesses its fitness for a decision, and
produces grounded answers and governed Decision Briefs.

The system is operational but incomplete. Acquisition, normalization,
chunking, embeddings, FAISS retrieval, reranking, evidence allocation,
constitutional orientation, deterministic Evidence Fitness, and Decision
Brief generation are implemented. Institutional topology and participation
models are partial. Scenario Modeling is planned, and the Institutional
Digital Twin remains aspirational.

The August 1, 2026 milestone is driven by this benchmark:

> If CNU reduced full-time faculty from roughly 275 to 250, which departments
> should lose faculty positions and why?

The benchmark is intentionally difficult. A credible answer requires
institution-wide staffing, instructional demand, enrollment trends,
cross-program dependencies, accreditation constraints, financial effects,
strategic priorities, and function-level substitutability. ISO must refuse to
manufacture a departmental ranking when these inputs are missing. That
requirement drives the architecture toward provenance, explicit uncertainty,
scope-aware Evidence Fitness, inspectable allocation, and future scenario
services rather than a single unconstrained RAG prompt.

## 2. Permanent Architecture

ISO uses a permanent six-layer architecture:

1. **Evidence Layer** — Acquires files and curated external resources,
   preserves provenance, normalizes sources into Knowledge Objects, chunks and
   embeds them, and builds the FAISS index.
2. **Semantic Layer** — Resolves institutional entities and proposed concepts,
   classifies question scope, orients questions against program catalogs and
   constitutional knowledge, and provides the current topology model.
3. **Reasoning Layer** — Builds governed evidence context, invokes the
   configured OpenAI-compatible LLM, and produces grounded answers and
   Decision Briefs with stable citations.
4. **Evidence Fitness** — Classifies decision type, evaluates required evidence
   domains, qualifies scope and authority, allocates diverse evidence, and
   reports Strong, Partial, Weak, Missing, and not-assessed states.
5. **Scenario Modeling** — Planned deterministic comparison of explicit
   alternatives, assumptions, capacity effects, financial effects, and risks.
   No production scenario engine currently ranks departments or recommends
   reductions.
6. **Institutional Digital Twin** — Aspirational temporal representation of
   institutional entities, functions, dependencies, constraints, and change.
   Current topology and participation contracts are foundations, not a
   complete twin.

Do not replace these layers with temporary phase terminology.

## 3. Repository Layout

| Path | Purpose |
| --- | --- |
| `app/` | Runtime services and contracts. Major areas include acquisition, parsers, normalization, retrieval, constitutional reasoning, the Semantic Control Plane, Evidence Fitness, topology, Decision Briefs, and dashboard presentation. |
| `app/acquisition/` | Filesystem, web, directory, observer, manifest, and curated external acquisition services. `app/acquisition/external/` contains the decision-driven external evidence pilot. |
| `app/constitution/` | Constitutional Knowledge Objects, catalog construction, retrieval, and Strategic Compass orientation. |
| `app/control_plane/` | Program catalog resolution, guarded aliases, semantic neighbors, and dual institutional/constitutional orientation. |
| `app/observatory/` | Evidence Fitness, decision readiness, topology, scope-aware workforce logic, and Decision Brief dashboard components. |
| `app/knowledge.py` | Base `KnowledgeObject` and `Document` persistence contracts. |
| `app/chunk.py` | Chunk generation and propagation of constitutional and external provenance metadata. |
| `app/vector_index.py` | Embedding-record loading, FAISS index construction, cached model/index access, and vector search. |
| `app/retrieval.py` | Unified retrieval pipeline, reports, traces, evidence quotas, and context grouping. |
| `app/document_family.py` | Dependency-light document-family normalization for revisions and related source families. |
| `app/evidence_roles.py` | Deterministic evidence-role derivation, expected-role coverage, relevance guardrails, and role-aware empirical allocation. |
| `app/evidence.py` | Evidence classes, claim-safe evidence-role labels, source titles, citation identities, and reasoning guidance. |
| `app/rag.py` | Grounded question-answering entry point. |
| `app/decision_brief.py` | Decision Brief orchestration parallel to RAG, connected to Evidence Fitness and governed synthesis. |
| `config/` | Runtime settings, source registries, program and constitutional catalogs, observer definitions, and curated-resource metadata. |
| `scripts/` | Operator CLIs, ingestion/build tools, diagnostics, benchmarks, and executable regression tests. |
| `storage/` | Raw sources, staged external evidence, normalized Knowledge Objects, constitutional objects, chunks, embeddings, vector database, logs, and caches. Most production data is intentionally not in Git. |
| `benchmarks/` | Retrieval benchmark definitions and cases. |
| `docs/` | Architecture, operations, engineering notes, status, and decision-support documentation. |
| `web_app.py` | Streamlit integration surface for observatory panels, RAG, Decision Briefs, and Developer Mode diagnostics. |

Historical `.pre_*` and `.bak` files are not the runtime implementation.

## 4. Core Architectural Principles

- **Knowledge Objects store facts. Services derive meaning.** Do not persist
  opaque relevance judgments, rankings, or recommendations as source facts.
- **Constitutional knowledge is separate from empirical evidence.** Mission and
  Strategic Compass commitments inform normative reasoning but do not prove
  operational conditions. Constitutional fallback has its own quota and is
  never allowed to consume empirical slots.
- **Evidence quality matters more than retrieval volume.** Reranker relevance,
  exact deduplication, document-family diversity, evidence-role concentration,
  authority, scope, and decision coverage all matter.
- **Missing evidence remains missing.** Role allocation uses a reranker-relative
  relevance floor and may return fewer results rather than promote weak
  evidence merely to fill a category.
- **Avoid opaque composite scores.** Prefer deterministic rules, explicit
  thresholds, stable ordering, and inspectable reasons.
- **Preserve provenance end to end.** Issuing authority, authority class,
  evidence role, domains, URL, version, effective period, geography, content
  hash, and acquisition timestamp should survive normalization and chunking
  when available.
- **Diagnostics are first-class output.** Retrieval traces must explain what
  entered, what was removed, and why.
- **Evidence quantity is not evidence diversity.** Drafts, revisions, filename
  variants, chunks, and repeated document families are not automatically
  independent corroboration.
- **A snapshot is not a trend.** Temporal claims require genuinely temporal or
  multi-year evidence.
- **External requirements, local self-study claims, local practice, and analyst
  inference are distinct.** The reasoning prompt and evidence classifier
  preserve those roles.
- **Backward compatibility is deliberate.** Retrieval and reasoning entry
  points retain their three-value normal and traced return contracts.
- **Unavailable capabilities are shown as unavailable.** Dashboard panels must
  not estimate disconnected operational, financial, enrollment, or scenario
  services.

## 5. Retrieval Pipeline

The current pipeline is implemented primarily in `app/vector_index.py`,
`app/retrieval.py`, `app/document_family.py`, `app/evidence_roles.py`,
`app/evidence.py`, and `app/rag.py`:

1. **Embeddings** — `scripts/embed_chunks.py` encodes chunk text with the
   configured sentence-transformer model. Embeddings are normalized.
2. **Vector search** — FAISS `IndexFlatIP` uses inner product, equivalent to
   cosine similarity for normalized embeddings. Retrieval initially fetches a
   broad candidate pool.
3. **Constitutional fallback** — If the unified pool lacks enough explicitly
   constitutional objects, retrieval performs an object-type-filtered fallback.
   These candidates remain marked and later enter only the constitutional
   quota.
4. **Exact deduplication** — Configurable modes operate on exact normalized
   chunk text, canonical document/path identity, or source path. RAG defaults
   to exact text deduplication so complementary chunks can survive.
5. **Cross-encoder reranking** — When enabled, the configured cross-encoder
   reorders deduplicated candidates. It stores the original FAISS score and the
   reranker logit separately.
6. **Document-family diversity** — Post-rerank family normalization removes
   excess revisions and closely related documents while preserving distinct
   criteria, programs, and reports. The default cap is two per family.
7. **Thresholding** — An optional minimum reranker score can remove candidates.
   It is currently `null`; do not invent calibrated semantics for raw logits.
8. **Constitutional/empirical partition** — Constitutional objects and empirical
   evidence enter independent quotas.
9. **Evidence-role allocation** — Empirical candidates receive a deterministic
   broad role with source and confidence. A soft role cap preserves reranker
   order, allows multiple highly relevant items per role, and considers
   complementary candidates only within a configured score margin. Missing
   expected roles are reported rather than filled with weak evidence.
10. **Evidence construction** — Decision Briefs call `make_evidence()` to assign
    stable citations, evidence classes, claim-safe roles, confidence, and
    rationale. RAG groups the selected results directly into constitutional and
    empirical context.
11. **Reasoning** — `answer_question()` or `generate_decision_brief()` sends the
    governed context to the configured OpenAI-compatible endpoint.

Normal retrieval returns `(results, report, profile)`. With `return_trace=True`
it returns `(results, report, trace, profile)`. RAG returns
`(answer, results, profile)` normally and
`(answer, results, retrieval_report, trace, profile)` in trace mode.

## 6. Knowledge Objects

`KnowledgeObject` is the base normalized semantic unit. It contains a stable
identity, object type, title, text, metadata, source mapping, and normalization
timestamps. `Document` adds filesystem-oriented fields such as source path,
relative path, parser, file type, size, modification time, and content hash.

`ConstitutionalKnowledgeObject` represents identified mission, value, and
strategic commitments. Constitutional objects are built from configured,
already-normalized source documents and are not empirical operating records.

External evidence is normalized through the ordinary parser pipeline, then
enriched with `external_provenance`. Native Python `date` and `datetime` values
are preserved internally and serialized as ISO-8601 strings at JSON boundaries.

Chunking is deterministic and configurable. Each chunk retains its Knowledge
Object identity, character range, citation, parser metadata, and selected
constitutional/external provenance fields. Chunking does not derive final
decision judgments. The current ontology is document-centered; department,
program, course, capability, relationship, and participation contracts exist
in limited areas but do not yet form a complete institutional ontology.

## 7. Configuration

`config/settings.yaml` is the primary runtime configuration. Important areas:

- `project.root` — `/work/brash/dept-llm-assistant` in production.
- `storage` — raw, staged, normalized, constitutional, chunk, embedding,
  vector-index, cache, model, and log locations.
- `llm` — OpenAI-compatible endpoint and model; the repository does not manage
  model-server startup.
- `chunking.chunk_size` / `overlap` — currently `1000` / `200`.
- `embedding.model` / `device` — currently `BAAI/bge-base-en-v1.5` on CUDA.
- `reranking` — cross-encoder model, device, enable flag, and optional minimum
  score.
- `retrieval.fetch_k` — broad candidate pool, currently `200`.
- `retrieval.constitutional_top_k` / `empirical_top_k` — separate final quotas,
  currently `2` and `10`.
- `retrieval.max_per_document_family` — currently `2`.
- `retrieval.max_per_evidence_role` — currently `4`.
- `retrieval.evidence_role_relevance_margin` — currently `0.5`; a candidate
  below the baseline cutoff by more than this amount is not promoted for role
  coverage.
- `normalization_sources` — ordered source roots and source identities.

Other important contracts include `config/external_evidence_sources.yaml`,
`config/institutional_constitution.yaml`, program catalogs, curated-resource
registries, and observer definitions. Do not commit local macOS paths into the
production configuration.

## 8. Engineering Workflow

Use CLI tools as the primary engineering interface. They are reproducible,
scriptable, and expose retrieval behavior without UI state. Use `web_app.py`
for integration validation, panel review, and end-user workflow testing.

Preferred change workflow:

1. Read `AGENTS.md`, this document, and the relevant implementation.
2. Check `git status`; preserve unrelated user changes.
3. Trace contracts and all call sites before editing shared APIs.
4. Make the smallest coherent change in the owning layer.
5. Add focused deterministic tests using fixtures or mocks.
6. Run focused tests, then affected regression groups.
7. Run syntax compilation and `git diff --check`.
8. Run A100 retrieval/index/LLM validation when production dependencies matter.
9. Report limitations precisely; never claim a local placeholder corpus proves
   production behavior.

Representative engineering commands:

```bash
cd /work/brash/dept-llm-assistant

# Grounded RAG with allocation diagnostics
.venv/bin/python -m scripts.ask_rag \
  "What evidence describes current faculty capacity?" \
  --diagnostics

# Retrieval benchmark and one-case analysis
.venv/bin/python -m scripts.run_retrieval_benchmark \
  --benchmark retrieval/v2.yaml
.venv/bin/python -m scripts.analyze_failure \
  --benchmark retrieval/v2.yaml --case CASE_ID --fetch-k 200

# Focused tests
.venv/bin/python -m pytest -q scripts/test_retrieval_evidence_allocation.py
.venv/bin/python -m pytest -q scripts/test_evidence_role_allocation.py
```

## 9. Diagnostics

Use `scripts.ask_rag --diagnostics` or Streamlit Developer Mode.

- **FAISS score** — Cosine-like vector similarity from normalized embeddings.
  It is useful for candidate discovery, not executive confidence.
- **Reranker score** — An uncalibrated cross-encoder logit. Compare ordering
  within one query; do not interpret a negative value as negative evidence or
  compare it with constitutional orientation confidence.
- **Family diversity** — Shows normalized family keys, retained candidates, and
  candidates removed by the per-family cap.
- **Evidence roles** — Distinguish explicit metadata, deterministic inference,
  and low-confidence fallback. Inspect role confidence, counts, concentration,
  whether a result added coverage, and whether allocation changed the baseline.
- **Missing roles** — Expected decision functions for which no sufficiently
  relevant selected evidence exists. Missing does not mean the corpus contains
  no such source; inspect candidates excluded for insufficient relevance.
- **Constitutional allocation** — Constitutional results have a separate quota.
  `constitutional_fallback=true` means the result came from the filtered
  fallback search, not that its score was compared with empirical candidates
  for the same slot.
- **Exclusion reasons** — Distinguish exact dedupe, family cap, role
  concentration, insufficient relevance, and final quota.
- **Retrieval timing** — Separates search, dedupe, rerank, family diversity, and
  threshold time. Model/index cold starts may dominate first-run timing.

## 10. Current Engineering Status

Implemented:

- Filesystem, web, observer, directory, and curated external acquisition
- External staging, validation, duplicate handling, partial-success reporting,
  `live_web` and `corpus_only` modes, and normalized promotion
- Multi-source normalization and provenance-bearing Knowledge Objects
- Constitutional catalog construction and Strategic Compass orientation
- Deterministic chunking and metadata propagation
- Sentence-transformer embeddings and FAISS vector search
- Optional cross-encoder reranking and thresholding
- Exact/path deduplication and document-family normalization
- Evidence-role derivation, concentration control, relevance guardrails, and
  missing-role diagnostics
- Separate constitutional and empirical allocation
- Program resolution, guarded short aliases, question-scope classification,
  and partial topology
- Grounded RAG, governed Decision Briefs, deterministic dashboards, Academic
  Workforce Planning panels, and scope-aware Evidence Fitness

Major remaining work:

- Evolve the Knowledge Object ontology beyond document-centered evidence while
  preserving facts/service boundaries.
- Acquire authoritative Layer 1 evidence for missing workforce, regional,
  comparator, institutional-capacity, financial, enrollment, and dependency
  roles.
- Expand expected-role and domain coverage across decision types.
- Continue calibrating Evidence Fitness scope, role inference, relevance
  margins, and authority treatment without opaque scoring.
- Implement explicit Scenario Modeling services.
- Build the Institutional Digital Twin incrementally from validated entities,
  functions, relationships, constraints, and time-varying facts.

## 11. Engineering Conventions

- Preserve public contracts and constructor defaults where reasonable.
- Prefer additive optional fields to breaking return signatures.
- Keep heavy retrieval/model imports out of dependency-light presentation and
  contract tests when practical.
- Use deterministic services for classification, normalization, allocation,
  and summaries; do not add an LLM call when a transparent rule is sufficient.
- Keep source facts in Knowledge Objects and derived judgments in services.
- Never infer institutional relationships from names alone.
- Preserve explicit Unknown, Missing, Partial, Weak, and Not Assessed states.
- Do not rank departments, faculty, or workforce reductions without an explicit
  scenario model and adequate evidence.
- Treat raw reranker logits as engineering diagnostics, not user-facing scores.
- Keep constitutional and empirical citations stable and distinct.
- Use `rg` for repository search, focused tests for regressions, and
  `git diff --check` before review.
- Do not rebuild large derived artifacts, synchronize drives, commit, push, or
  deploy unless the task explicitly authorizes it.

## 12. Common Entry Points

Run production commands from the canonical A100 checkout:

```bash
cd /work/brash/dept-llm-assistant
```

### Retrieval and diagnostics

```bash
.venv/bin/python -m scripts.ask_rag \
  "What do national enrollment trends show about Health Physics programs?" \
  --diagnostics

.venv/bin/python -m scripts.run_retrieval_benchmark \
  --benchmark retrieval/v2.yaml
```

### Tests and static validation

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app scripts
git diff --check
```

Useful focused suites:

```bash
.venv/bin/python -m pytest -q \
  scripts/test_retrieval_evidence_allocation.py \
  scripts/test_evidence_role_allocation.py \
  scripts/test_ask_rag.py

.venv/bin/python -m pytest -q \
  scripts/test_academic_workforce_dashboard.py \
  scripts/test_academic_workforce_evidence_map.py \
  scripts/test_academic_workforce_participation.py \
  scripts/test_awp_stabilization.py
```

### Web integration

```bash
source .venv/bin/activate
streamlit run web_app.py
```

The configured OpenAI-compatible model server must already be running.

### Ingestion and normalization

```bash
.venv/bin/python -m scripts.inventory_corpus
.venv/bin/python -m scripts.normalize_documents --list-sources
.venv/bin/python -m scripts.normalize_documents --source all --limit 1000000
.venv/bin/python -m scripts.build_constitutional_catalog
```

Review `docs/operations/external_evidence_refresh.md` before external
acquisition. Its dry run is intentionally non-networked; `--execute` retrieves
only explicitly registered resources.

### Rebuild chunks, embeddings, and FAISS

```bash
.venv/bin/python -m scripts.chunk_documents --limit 1000000
.venv/bin/python -m scripts.embed_chunks \
  --limit 1000000 --embedding-context title_path
.venv/bin/python -m scripts.build_vector_index
```

Promotion into `storage/normalized` does not automatically rebuild chunks,
embeddings, or FAISS. Newly acquired evidence cannot participate in retrieval
until all three derived stages complete. Stop or restart long-lived processes
after rebuilding so they do not retain the old in-memory index.

For destructive cache/output clearing, Google Drive synchronization, external
acquisition, and production monitoring, follow the reviewed commands in
`docs/operations/a100.md` and `docs/operations/external_evidence_refresh.md`
rather than improvising.
