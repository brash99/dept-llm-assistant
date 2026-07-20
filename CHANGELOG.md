# Institutional Semantic Observatory Changelog

This changelog records significant implemented milestones. Planned work belongs in `docs/status.md` or `docs/ResearchAgenda.md`, not in completed entries.

## July 2026 — Academic Workforce Planning stabilization

- Added the `academic_workforce_planning` decision type and eight canonical evidence domains.
- Added the Executive Workforce Decision Framework, Academic Workforce Evidence Map, and Institutional Participation Profile.
- Added deterministic institution-wide and multi-entity question scope.
- Guarded high-risk program aliases so lowercase `is` cannot resolve to Information Science.
- Prevented institution-wide questions from being forced into one topology entity.
- Added scope-aware Evidence Fitness dimensions for directness, institutional scope, authority/role, coverage breadth, and document-family independence.
- Required genuine temporal evidence for Enrollment Trends.
- Distinguished institutional ABET self-studies and local criterion responses from formal external standards and external comparators.
- Added post-rerank document-family diversity and related diagnostics.
- Corrected topology narratives for incoming-only relationships.
- Removed raw reranker logits from executive source labels while preserving engineering diagnostics.
- Added evidence-role serialization and self-study claim-safety rules to the Decision Brief prompt.
- Confirmed that the canonical workforce benchmark refuses departmental reduction recommendations when institution-wide evidence is insufficient.

## July 2026 — Integrated Decision Brief Dashboard V2

- Added deterministic Decision Readiness, Observatory Status, and Knowledge Ecosystem panels.
- Connected Evidence Fitness assessments to rendered Decision Briefs.
- Added stable empirical and constitutional citation namespaces.
- Added authoritative topology context and scope notices.
- Separated presentation imports from heavy FAISS and sentence-transformer dependencies.

## June–July 2026 — Evidence and Semantic foundations

- Added governed acquisition manifests, parser registry, multi-source normalization, chunking, embeddings, and FAISS indexing.
- Added constitutional catalog building and Strategic Compass orientation.
- Added the Semantic Control Plane, program catalog, proposed-concept extraction, and semantic program neighbors.
- Added evidence classes, evidence landscape metrics, retrieval tracing, cross-encoder reranking, and benchmark tooling.

## Current status boundary

Scenario Modeling remains planned. The Institutional Digital Twin remains aspirational. Neither is a completed production capability.
