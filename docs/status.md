# Current Implementation Status

> **Status:** Authoritative current-state inventory, synchronized July 23,
> 2026. Historical sessions, design proposals, presentations, and dated audits
> are not implementation-status sources.

ISO uses the permanent six-layer architecture:

1. Evidence Layer
2. Semantic Layer
3. Reasoning Layer
4. Evidence Fitness
5. Scenario Modeling
6. Institutional Digital Twin

> Knowledge objects store facts. Services derive meaning.

ISO does not model institutional reports as reality. ISO models the
institution. Reports are evidence about that model and may be explained,
validated, or reproduced as consequences of the underlying institutional
structure.

## Status vocabulary

- **Implemented** means the code, governed configuration, and deterministic
  tests exist.
- **Validated** means an implemented capability has also been exercised
  against the available production evidence and its invariants checked.
- **Partially estimable** means a governed method can produce an explicit
  subset or proxy while preserving exclusions and limitations.
- **Unresolved** means evidence or institutional governance is insufficient
  for a safe result.
- **Not yet implemented** means no production service should claim the
  capability.

## Evidence Layer

### Implemented

- Filesystem, directory, web, and curated-resource acquisition with manifests
  and provenance.
- Deterministic normalization into typed Knowledge Objects under
  `storage/normalized`.
- Governed faculty-directory, catalog, department-roster, and schedule
  observations.
- Explicit schedule facts including term, section, instructor, enrollment,
  credits, status, and published LLC designation text.
- Constitutional Knowledge Objects from configured institutional sources.
- Chunking, sentence-transformer embeddings, FAISS indexing, retrieval,
  reranking, evidence quotas, exact deduplication, document-family diversity,
  and trace diagnostics.
- Curated external-evidence acquisition with quarantine, validation, and
  provenance-preserving promotion.

### Environment boundary

Governed normalized evidence may exist and be tracked in the Mac checkout.
That checkout must not automatically be assumed identical to the current A100
production state. Evidence inventories and deterministic fingerprints must be
verified before production conclusions are reported.

## Semantic Layer

### Implemented and validated

- A governed institutional-unit registry with stable identifiers, formal unit
  types, current and historical units, aliases, parent relationships where
  supported, analytical roles, and eligibility dimensions.
- Governed subject-prefix ownership, distinct from institutional-unit
  definitions. Published schedule prefixes remain source facts; services map
  them to governed curriculum owners.
- Catalog-derived subject-ownership evidence and discrepancy auditing that
  cannot silently promote candidates into governance.
- Deterministic institutional-label normalization with exact names, governed
  aliases, bounded contamination cleanup, explicit ambiguity, and no fuzzy or
  LLM matching.
- Governed program, administrative-unit, historical-unit, and current-unit
  distinctions.
- Deterministic Faculty Identity across directory, catalog, roster, and
  schedule observations. Reviewed aliases are governed facts; uncertain
  matches remain separate.
- Faculty Appointment Observation, Administrative Appointment Observation,
  and Employment Status Observation as distinct evidence objects.
- A governed LLC designation policy. Published `llc_area_raw` remains source
  evidence; effective-dated policy determines which tokens are LLC
  designations.
- A governed Undergraduate Major Registry with stable identities,
  source-specific ownership assertions, aliases, degree facts, status,
  provenance, and unresolved conflicts.
- A separate governed Major → Capstone Registry with catalog provenance and
  explicit relationship types.

### Partially implemented

- Institutional topology is governed for the academic units and relationships
  required by current workforce analysis, but it is not a complete university
  relationship graph.
- Generic-document semantic routing covers reviewed high-value source
  families; unsupported document families abstain.
- Semantic Identity propagation into normalized generic documents is
  implemented. Existing production retrieval artifacts may require a separately
  reviewed rebuild before those fields become available to retrieval filters.

## Reasoning Layer

### Faculty and workforce

- The Authoritative Faculty Roster contract supports deterministic future
  ingestion of effective-dated HR or Academic Affairs evidence. No
  authoritative production roster is asserted to exist.
- The governed Analytical Workforce Builder starts from current
  faculty-directory identities and reasons separately about workforce
  membership and department assignment.
- Institutional review is complete for the current production baseline:
  **282 included analytical-workforce identities**, with zero remaining
  workforce-membership or department-assignment review decisions.
- The 282-person population is a governed analytical baseline, not an
  authoritative HR roster, legal employment assertion, or inferred FTE
  population.

### Department profiles and instructional activity

- Department Profiles aggregate every included analytical-workforce identity
  exactly once into its governed home department.
- Faculty home and instructional delivery are separate relationships.
- Profiles report workforce membership, titles and ranks, administrative roles,
  teaching history, governed subject activity, enrollment, SCH, cross-unit
  instruction, provenance, Evidence Fitness, and limitations.
- Production validation reconciles 282 workforce identities across 18 current
  department profiles.

### SCH

- SCH is implemented as a deterministic derived metric for sections with
  explicit enrollment and explicit scalar credits.
- SCH completeness auditing preserves missing-input reasons and never invents
  enrollment or credits.
- The current production Department Profiles validate complete SCH input
  coverage for all 18 profiles over the available governed schedule evidence.
- **Curriculum-owned SCH** assigns a section to the governed owner of its
  subject prefix. This is the canonical curriculum-ownership metric.
- **Workforce-attributed SCH** assigns a section to the governed analytical
  home of an active analytical-workforce instructor; when no eligible home is
  available, it uses the governed prefix owner as an explicit
  `prefix_owner_fallback`. This decision-specific metric does not change
  curriculum ownership.
- Timeline and fall-only reporting expose term and academic-year SCH without
  changing the underlying attribution semantics.

### LLC SCH

- LLC section inclusion is governed by effective-dated designation tokens,
  not by a nonblank-string heuristic.
- A section with one or more governed LLC tokens contributes SCH once while
  retaining all matched tokens and categories.
- Unknown LLC tokens are reported rather than interpreted.
- LLC SCH can be reported with the same curriculum-owned and
  workforce-attributed distinctions where the corresponding service applies
  them.

### Majors, capstones, and estimated graduates

- The Undergraduate Major Registry is implemented and validated independently
  of administrative completion totals.
- The Major → Capstone Registry is implemented for every governed current
  undergraduate major and distinguishes single capstones, sequences, multiple
  requirements, alternatives, thesis/seminar pathways, shared capstones,
  unresolved pathways, and no identifiable capstone.
- Estimated Graduates by Major is implemented as an independent,
  deterministic capstone-enrollment proxy.
- The observable uses only governed majors, governed capstone relationships,
  and schedule enrollment. Quentin’s completion totals are held-out validation
  evidence, not an input or optimization target.
- The observable is **partially estimable**: shared capstones, unresolved
  pathways, no identifiable capstone, and unobserved terminal sections remain
  explicit exclusions or unavailable results. A held-out comparison covered
  approximately 72% of institution-wide completions; that dated result is
  evidence about fitness, not a universal accuracy claim.
- Absence of an observed capstone section is not interpreted as zero
  graduates.

### Other implemented reasoning

- Deterministic schedule aggregation and trend analysis.
- Semantic discrepancy analysis.
- Grounded question answering through a configured OpenAI-compatible endpoint.
- Decision Brief synthesis with stable citations, evidence-role separation,
  claim-safety rules, and deterministic readiness panels.

## Evidence Fitness

### Implemented

- Decision-type classification and domain-level Strong, Partial, Weak, or
  Missing support.
- Scope, authority, directness, coverage, temporal fitness, source-family
  independence, and missing-evidence reporting.
- Distinct readiness labels for the reviewed analytical workforce and the
  unavailable authoritative HR denominator.
- Categorical limitations for SCH completeness, workforce attribution,
  capstone estimation, identity linkage, and temporal scope.

### Important current limitations

- Rank is not appointment FTE.
- Schedule instruction is not proof of a full-time appointment.
- Public-directory presence is not an authoritative effective-dated HR record.
- Capstone enrollment is not a graduation record.
- Administrative reports may use reporting ownership, definitions, time
  windows, or exclusions that differ from ISO’s governed semantic metrics.

## Scenario Modeling

### Not yet implemented

- No production engine ranks departments for reductions.
- No service currently recommends which positions should be removed.
- No governed scenario model yet combines faculty capacity, instructional
  demand, curriculum dependencies, finances, accreditation, service teaching,
  and institutional priorities into comparable reduction alternatives.

The current workforce, department profiles, SCH metrics, LLC semantics, and
graduate proxy provide important scenario inputs. They do not by themselves
justify a reduction recommendation.

## Institutional Digital Twin

### Aspirational

ISO has governed entities, observations, identities, relationships, temporal
evidence, and derived institutional profiles. It does not yet provide a
complete temporal university graph, live operational twin, probabilistic
forecast, or autonomous decision system.

## August workforce-planning readiness

Quentin’s benchmark asks:

> If CNU reduces full-time instructional faculty from approximately 275 to
> approximately 250, which departments should lose positions?

ISO can now inspect a reviewed analytical workforce, faculty home, curriculum
ownership, instructional delivery, SCH, LLC activity, majors, capstones, and a
partial graduate proxy. It can reproduce or explain many report-like metrics
from governed institutional structure.

A responsible reduction recommendation still requires governed scenario
assumptions and evidence not fully represented, including authoritative
effective-dated appointment/FTE confirmation, financial effects, vacancies and
retirements, course and program dependencies, accreditation constraints,
advising and governance responsibilities, facilities, research obligations,
and feasible substitution or consolidation choices.

Until Scenario Modeling incorporates those inputs, ISO should explain the
evidence and its fitness, compare transparent alternatives when explicitly
defined, and refuse to manufacture a departmental reduction ranking.
