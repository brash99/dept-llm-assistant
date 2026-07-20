# Architecture Overview

This is the authoritative architecture description for the Institutional Semantic Observatory. ISO uses six permanent layers. Acquisition, normalization, retrieval, dashboards, and topology are subsystems within these layers—not additional layers or replacement phase models.

> Knowledge Objects store facts. Services derive meaning.

## 1. Evidence Layer

The Evidence Layer preserves observations and makes relevant evidence retrievable.

### Implemented

- governed acquisition services and append-oriented source manifests;
- parser registry and multi-source normalization;
- Knowledge Objects with content, source identity, provenance, and metadata;
- Constitutional Knowledge Objects built from identified normalized sources;
- chunking of normalized and constitutional objects;
- sentence-transformer embeddings and FAISS indexing;
- vector retrieval, exact/path deduplication, cross-encoder reranking, optional thresholds, and constitutional/empirical quotas;
- deterministic document-family keys and post-rerank family diversity; and
- retrieval traces retaining raw FAISS and reranker diagnostics.

Document-family diversity is distinct from exact deduplication. Exact deduplication removes identical/path-equivalent representations. Family diversity limits drafts, revisions, self-study packages, and naming variants after ranking so they do not masquerade as independent evidence.

### Partial

- family identity is metadata/filename-based rather than semantic;
- corpus coverage is broad but incomplete and uneven across institutional domains; and
- production data exists on the A100, not in the repository’s placeholder storage directories.

## 2. Semantic Layer

The Semantic Layer identifies institutional meaning without deciding the answer.

### Implemented

- program catalog and ProgramResolver;
- guarded high-risk aliases requiring case, token boundaries, and academic context;
- deterministic question scope: single entity, multi-entity, institution-wide, or unresolved;
- institutional and constitutional orientation before retrieval;
- evidence classes and claim-safe evidence roles;
- separation of institutional self-studies, formal external standards, external comparators, planning documents, operating records, and constitutional evidence; and
- a small institutional topology with directionally accurate relationship summaries.

For institution-wide Academic Workforce Planning, contextual entities do not become the selected unit. The question remains a comparative multi-unit request.

### Partial

- program and topology catalogs are curated and incomplete;
- evidence-role classification uses deterministic metadata/path/title heuristics; and
- topology does not encode the complete course, program, Liberal Learning Core, facility, personnel, partnership, or governance network.

## 3. Reasoning Layer

The Reasoning Layer organizes evidence and derived service outputs into explainable knowledge products.

### Implemented

- grounded question answering;
- Decision Brief generation through an OpenAI-compatible local LLM endpoint;
- stable constitutional and empirical citation namespaces;
- governed prompt instructions for evidence authority, planning language, self-study claims, external requirements, comparators, uncertainty, and topology inference;
- deterministic Dashboard V2 panels assembled with narrative synthesis; and
- explicit refusal to infer unsupported relationships or recommendations.

The LLM synthesizes supplied evidence. It does not create Evidence Fitness grades, topology relationships, question scope, document families, or participation facts.

### Partial

- generated prose still requires human review;
- arbitrary prose cannot be completely guaranteed by prompt tests; and
- the Decision Brief data model retains several legacy empty summary fields while `raw_markdown` is the primary rendered product.

## 4. Evidence Fitness

Evidence Fitness asks whether the retrieved evidence is adequate for the classified decision—not merely whether keywords are present.

### Implemented

- deterministic decision-type classification;
- canonical evidence-domain profiles;
- graded Strong, Partial, Weak, and Missing support;
- topic coverage, authority fit, evidence-role fit, strengths, limitations, and acquisition recommendations;
- Academic Workforce Planning qualification for directness, institutional scope, authority/role, coverage breadth, and independent document families;
- explicit distinction between evidence presence and decision sufficiency;
- temporal requirements for Enrollment Trends; and
- consistent propagation into dashboards and prompt guidance.

A departmental self-study may provide direct evidence about one unit without providing institution-wide comparative fitness. A formal standard may establish a constraint without establishing local compliance or staffing margin. Financial vocabulary is not a decision-specific cost model.

## 5. Scenario Modeling

### Planned

Scenario Modeling will compare explicit alternatives and assumptions. It is required for credible workforce-change analysis but is not implemented as a production service.

Planned inputs include unit staffing, instructional demand, enrollment trajectories, service dependencies, accreditation constraints, financial assumptions, one-line-loss effects, institutional capabilities, and function-level alternative providers.

The current system does not calculate which departments should lose positions.

## 6. Institutional Digital Twin

### Aspirational

The long-term Institutional Digital Twin would be a temporal, evidence-backed representation of entities, capabilities, dependencies, constraints, and change. It is not a single vector database, dashboard, topology graph, or LLM.

Current foundations include Knowledge Objects, observation manifests, semantic orientation, topology contracts, and the Institutional Participation Profile. These are precursors, not a completed twin.

## End-to-end Decision Brief flow

```text
User question
  → deterministic institutional and constitutional orientation
  → deterministic question-scope classification
  → FAISS candidate retrieval and constitutional fallback
  → exact/path deduplication
  → cross-encoder reranking
  → document-family diversification
  → optional threshold
  → constitutional/empirical selection
  → evidence class and evidence-role assignment
  → Decision Readiness domain evaluation
  → scope-aware Evidence Fitness
  → topology resolution only when scope permits one entity
  → governed LLM synthesis
  → deterministic Dashboard V2 and topology rendering
  → final Decision Brief Markdown
```

Raw reranker logits remain diagnostics and are omitted from the executive source list.

## Architectural boundaries

- Knowledge Objects store asserted observations and provenance.
- Services classify, compare, assess, and derive meaning.
- Presentation components render supplied contracts and deterministic explanatory metadata.
- Constitutional values and empirical facts remain separate semantic spaces.
- Missing evidence is reported as Missing, Weak, Partial, Unknown, Unavailable, or Not Assessed—not invented as zero or treated as proof of absence.
- Scenario and Digital Twin aspirations must not be described as current production capability.
