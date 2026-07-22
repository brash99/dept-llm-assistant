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

- Deterministic schedule analysis operates directly over normalized schedule
  Knowledge Objects for distinct-instructor counts, course-offering counts, and
  explicit offering-share denominators by term, Instructor Type, subject, and
  governed academic unit. It preserves unresolved, repaired, unknown, and
  missing-status categories and produces provenance-bearing fingerprints.
- Governed schedule subject ownership is separated from organizational-unit
  definitions: `config/subject_ownership.yaml` records prefix ownership while
  `config/institutional_units.yaml` remains authoritative for units, formal
  types, relationships, and operational roles. Mapping is implemented with explicit mapped,
  intentionally grouped, ambiguous, unmapped, and unsupported outcomes. The
  reviewed records roll six SEC instructional subject codes—PHYS, CPSC, CYBR,
  CPEN, EENG, and PCSE—into SEC as a
  department-equivalent workforce unit without representing SEC as a formal
  department or inventing specialty departments. Other subjects remain
  unmapped pending reviewed crosswalks.
- The subject ownership registry carries mapping method, typed evidence
  (including explicitly reviewed institutional-expert evidence for PCSE),
  authority, source type, confidence, effective terms, review status, and
  notes. Registry auditing detects conflicts, invalid targets/types/roles,
  missing evidence, overlapping effective ranges, and deprecated targets.
  Production inventory and report-comparison tooling operate directly over
  normalized schedules without retrieval or LLM dependencies. No additional
  subject mappings were added because the Mac-accessible catalog ontology does
  not publish a governed course-prefix-to-unit crosswalk.
- Catalog-derived subject-ownership evidence tooling now selects catalog
  editions by academic year, extracts anchored course-description headers,
  resolves exact governed section aliases, emits typed exceptions and
  reviewable candidates, and compares catalog, schedule, and governed prefix
  sets. Candidates cannot automatically modify governance. IS is intentionally
  absent from subject ownership while the Information Science/BSIS academic
  program remains governed in the program registry.
- Deterministic semantic discrepancy analysis explains catalog, schedule, and
  governance differences with exactly one primary category per investigated
  prefix. Its dashboard reports confidence, engineering review priority, and
  catalog/schedule/governance/parser completeness as Evidence Fitness. It does
  not infer mappings or promote candidates.
- Governed schedule-prefix normalization now resolves 24 operational Music
  prefixes to the Department of Music, Theatre, and Dance while preserving
  their published schedule identities and linking them to the catalog-visible
  MUSC family. MECH, ENVS, NAVS, and HBRW have reviewed ownership mappings;
  ENVS remains distinct from EVST. Prefix reporting now separates source-set
  differences from incomplete institutional mapping and genuine parser or
  catalog-structure limitations.
- Narrow schedule trend analysis uses chronological normalized terms and
  reports endpoint changes, missing terms, zero denominators, and
  comparability limitations. Schedule Evidence Fitness explicitly rejects
  official employment-history, workload/FTE, and staffing-recommendation uses.
- Deterministic execution typing and routing distinguish selective retrieval,
  structured aggregation, comparison, trend analysis, scenario modeling, and
  unsupported requests. `scripts/ask_rag.py` routes supported schedule
  analytics before retrieval and refuses top-k fallback for unsupported
  analytics. Descriptive schedule questions do not request constitutional
  evidence; normative hybrids represent that request separately.
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
