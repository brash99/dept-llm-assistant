# Current Implementation Status

Status as of July 2026. This file describes the current codebase; research and session notes may describe earlier states or future goals.

## Implemented

### Evidence Layer

- Filesystem, directory, web, and curated-resource acquisition services with manifests and provenance.
- Multi-source normalization into Knowledge Objects.
- One canonical recursive normalized corpus at `storage/normalized`, including
  faculty, catalog, and schedule subtrees; `data/normalized` is no longer an
  active evidence store.
- Curated Constitutional Knowledge Objects built from configured normalized sources.
- Chunking of normalized and constitutional objects.
- Sentence-transformer embeddings and FAISS indexing.
- Retrieval with exact/path deduplication, optional cross-encoder reranking, optional thresholding, constitutional/empirical quotas, and trace diagnostics.
- Conservative document-family normalization and post-rerank diversity limits. ABET self-study revisions and criterion-response filename variants are grouped without merging distinct criteria or identified programs.
- Deterministic evidence classes and finer evidence roles, including Institutional Self-Study, Formal External Standard, Departmental Report, Planning Document, External Comparator, and Constitutional Evidence.
- Decision-driven external evidence acquisition pilot with a seven-authority
  curated registry, deterministic Evidence Fitness gap planning, dry-run
  reports, staged validation, provenance-enriched Knowledge Objects, and
  promotion through the existing normalization path.

### Semantic Layer

- Catalog-backed program orientation and guarded short-alias resolution.
- Deterministic question-scope classification: single entity, multi-entity, institution-wide, or unresolved.
- Constitutional orientation against the Strategic Compass catalog.
- Bootstrap institutional topology with incoming/outgoing impact summaries.
- Institution-wide questions preserve contextual mentions without forcing one selected topology entity.
- Authoritative Semantic Identity contracts, classification proposals, field-level policy, audit sampling, and dry-run corpus population are implemented for structured Knowledge Objects.
- Registry-driven generic-document routing is implemented for curated external evidence, SCHEV, CNU Institutional Research, and reviewed SEC Statistics, Program Review, Annual Report, and Planning families. Source family, document type, institutional role, authority, scope, and temporal scope remain separate assertions; unknown and sensitive families abstain.
- Semantic Document Routing v1 was reviewed and applied to 480 generic documents on July 21, 2026: 162 CNU Institutional Research, 65 SCHEV, 92 SEC Statistics, 70 SEC Program Review, 40 SEC Annual Reports, 41 SEC Planning, and 10 explicitly provenanced curated external documents. Post-application classification is idempotent with zero projected changes, conflicts, reviews, or failures.
- After application, corpus-wide Semantic Identity coverage is 480 source-family values, 418 document types, 480 institutional roles, 237 authority assertions, 8,951 objects with institutional entities, and 8,770 objects with temporal scope. Decision domains and organizational relationships remain unpopulated by document routing.
- Safe derived-data pipeline tooling is implemented in `scripts/semantic_pipeline.py`, with read-only status, mutation-free rebuild preflight, staged chunk/embedding/FAISS construction, backup and rollback protection, durable manifests, structural verification, and exact Semantic Identity propagation checks. It has been validated with temporary synthetic artifacts on macOS; it has not yet rebuilt production chunks, embeddings, or FAISS.

### Reasoning Layer

- Grounded question answering through a configured OpenAI-compatible local endpoint.
- Governed Decision Brief prompt with stable empirical/constitutional citations, evidence-role serialization, and self-study claim-safety instructions.
- Decision Brief Dashboard V2 with deterministic readiness, observatory, workforce framework, evidence map, and participation panels.
- Executive source lists omit uncalibrated reranker logits; engineering diagnostics retain FAISS and reranker values.

### Evidence Fitness

- Deterministic decision-type classification, including Academic Workforce Planning.
- Domain evaluators and graded support: Strong, Partial, Weak, or Missing.
- Scope-aware Academic Workforce Planning qualification for directness, institutional scope, authority/role, coverage breadth, and unique document families.
- Enrollment Trends requires temporal or multi-year evidence; a single-year snapshot is not a trend.
- Evidence Fitness limitations are passed into deterministic panels and the governed narrative prompt.

## Partially implemented

- **Institutional topology:** a small manually curated graph, not a complete institutional relationship model.
- **Institutional Participation Profile:** renders supplied profile contracts or validated department/college topology context; institution-wide unit collections are not yet available.
- **Evidence-role classification:** deterministic path/title/metadata heuristics; it does not inspect source authorship through an LLM.
- **Generic-document semantic coverage:** high-value reviewed families are supported; broad ABET, assessment, curriculum, syllabi, course materials, student work, presentations, archives, and personnel materials intentionally remain unsupported unless explicit curated provenance applies.
- **Derived-data propagation:** the generic chunker is capable of inheriting the complete `semantic_identity`, but the existing chunks, embeddings, and FAISS index predate the applied document identities. The new fields are normalized-object facts until a separately reviewed chunk/embedding/index rebuild is performed; no retrieval or scenario conclusion should be attributed to them yet.
- **Document-family normalization:** deterministic metadata and filename heuristics; no semantic embedding pass is used for family identity.
- **Constitutional reasoning:** Strategic Compass orientation and citation separation are implemented; constitutional alignment is not a final normative judgment.
- **Decision readiness:** evidence sufficiency is assessed, but operational, financial, enrollment, and scenario services shown in the dashboard are not connected.

## Recorded technical debt

- Importing `app.control_plane` eagerly imports `sentence-transformers` through
  semantic-neighbor components, even when callers need only lightweight
  catalog, resolver, or orientation contracts. Dependency-light tests currently
  use a localized optional-dependency fixture. Decoupling that import path is a
  separate change and is intentionally not addressed by the Health Physics
  integration patch.

## Planned

### Scenario Modeling

- Explicit alternative workforce scenarios.
- Function-level capacity and substitution assumptions.
- Financial, enrollment, course-coverage, accreditation, and one-line-loss effects.
- Comparable scenario outputs with transparent assumptions.

No scenario engine currently ranks departments or recommends reductions.

## Aspirational

### Institutional Digital Twin

The long-term objective is a temporal, evidence-backed representation of institutional entities, functions, dependencies, constraints, and changes. The current Knowledge Objects, topology, and participation contracts are foundations only. ISO does not yet provide a complete institutional ontology, graph database, live operational twin, probabilistic forecast, or autonomous decision system.

## Academic Workforce Planning limitations

The canonical benchmark cannot be answered responsibly without institution-wide, unit-level evidence such as:

- faculty headcount/FTE, qualifications, loads, vacancies, retirements, adjuncts, and overloads;
- multi-year enrollment, completions, sections, student-credit hours, and service teaching;
- course-to-program, prerequisite, Liberal Learning Core, laboratory, and accreditation dependencies;
- departmental budgets, compensation, projected savings, replacement costs, revenue effects, and scenario assumptions;
- mission-critical capabilities, advising, research, governance, facilities, and external partnerships; and
- evidence of alternative providers and available capacity for each institutional function.

Until those inputs exist, ISO should report missing evidence and refuse a departmental reduction recommendation.
