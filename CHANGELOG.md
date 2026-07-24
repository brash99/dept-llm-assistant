# Institutional Semantic Observatory Changelog

This changelog records significant implemented milestones. Planned work belongs in `docs/status.md` or `docs/ResearchAgenda.md`, not in completed entries.

## July 2026 — Governed academic semantics

- Added governed institutional units with current, historical, program,
  administrative, college/school, analytical-role, and eligibility
  distinctions.
- Separated subject-prefix ownership from institutional-unit identity and added
  catalog/schedule discrepancy audits.
- Completed reviewed operational prefix governance without collapsing source
  labels or historical units.

## July 2026 — Faculty evidence, identity, and workforce

- Added deterministic Faculty Identity across directory, catalog, roster, and
  schedule observations with governed aliases and human-reviewed match
  decisions.
- Added distinct faculty-appointment, administrative-appointment,
  employment-status, and teaching-assignment evidence.
- Added the authoritative effective-dated faculty-roster ingestion contract
  without asserting that a production HR roster exists.
- Added the governed Analytical Workforce Builder, separated workforce
  membership from department assignment, and completed institutional review of
  the 282-person analytical baseline.

## July 2026 — Department profiles and instructional metrics

- Added 18 reconciled Department Profiles covering the reviewed analytical
  workforce.
- Added deterministic section, enrollment, course-credit, and SCH aggregation
  with completeness and missing-section forensics.
- Repaired schedule normalization and subject-owner linkage until all 18
  profiles had complete SCH input coverage over the available production
  evidence.
- Added term, academic-year, fall-only, and three-year departmental SCH
  products.

## July 2026 — Attribution and LLC governance

- Preserved curriculum-owned SCH as the canonical subject-owner metric.
- Added workforce-attributed SCH using governed instructor home with explicit
  prefix-owner fallback for instructors outside the analytical workforce.
- Added effective-dated LLC designation governance, token-level matching,
  unknown-token reporting, and count-once section semantics.
- Added LLC SCH reporting without changing curriculum ownership.

## July 2026 — Undergraduate majors, capstones, and graduate proxy

- Added the governed Undergraduate Major Registry with stable identifiers,
  source-specific ownership assertions, historical names, provenance, and
  unresolved conflicts.
- Added a separate governed Major → Capstone Registry covering single
  capstones, sequences, multiple requirements, alternatives, thesis/seminar
  pathways, shared capstones, and unresolved cases.
- Added the independently derived Estimated Graduates by Major observable using
  governed capstone relationships and explicit schedule enrollment.
- Preserved administrative completion totals as held-out validation evidence,
  not an input to the proxy.

## July 2026 — Repository cleanup and baseline archival

- Removed unreferenced source snapshots and a generated faculty inspection
  dump already preserved by Git history.
- Archived historical development context under documentation.
- Moved the July major/capstone experiment outputs into a documented baseline
  directory with provenance and reproduction commands.
- Added ignore rules preventing source backup files from returning to the
  active tree.

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
