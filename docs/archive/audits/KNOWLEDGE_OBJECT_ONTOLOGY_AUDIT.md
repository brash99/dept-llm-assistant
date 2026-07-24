# KnowledgeObject Ontology Audit

> **Status:** Dated ontology audit conducted July 20, 2026. It is preserved as
> an audit of that repository state and does not include later faculty,
> workforce, department-profile, LLC, major, capstone, or graduate-estimate
> objects. Use [Current Status](../../status.md) for current capability
> boundaries.

## Scope and method

This audit describes the ontology implemented in the repository as of July 20, 2026. It distinguishes three things that are easy to conflate:

1. persisted `KnowledgeObject` types;
2. factual catalogs and relationship contracts outside the `KnowledgeObject` hierarchy; and
3. service-derived assessments used for retrieval, reasoning, and presentation.

The distinction is architecturally important. ISO currently follows the principle that **Knowledge Objects store facts and services derive meaning**. A Python dataclass is therefore not necessarily a Knowledge Object, and a term appearing in a document is not necessarily an explicit entity in the ontology.

The implementation sources used for this audit include `app/knowledge.py`, `app/constitution/`, `app/control_plane/`, `app/observatory/topology/`, `app/observatory/evidence_fitness.py`, `app/evidence.py`, `app/evidence_roles.py`, `app/acquisition/`, `app/normalize.py`, `app/chunk.py`, `app/vector_index.py`, the Decision Brief services and Dashboard V2 contracts, and the semantic configuration under `config/`.

# 1. Current KnowledgeObject Hierarchy

The persisted hierarchy is deliberately small. Repository-wide inspection finds three classes in the hierarchy: the base class and two concrete subclasses.

## `KnowledgeObject`

**Implementation:** `app/knowledge.py`

**Purpose:** The common normalized unit for facts that can be represented as text plus metadata. Its docstring anticipates documents, database records, course records, budget records, and policies, but the current repository implements only the document and constitutional specializations described below.

**Important fields:**

- `id`: object identity;
- `object_type`: string discriminator used during loading;
- `title` and `text`: searchable human-readable content;
- `metadata`: open-ended attributes;
- `source`: open-ended source information;
- `created_at` and `normalized_at`: optional ISO-formatted timestamps.

**Current usage:** It is the common persistence and chunking interface. `save_knowledge_object()` writes JSON, with `date` and `datetime` values serialized as ISO-8601 strings. `load_knowledge_object()` dispatches recognized `object_type` values and falls back to the base type for unrecognized values.

**Limitations:**

- `metadata` and `source` are unversioned dictionaries rather than validated shared contracts.
- `object_type` is a free string, and deserialization dispatch is centralized in `app/knowledge.py`.
- There is no ontology/schema version on an individual object.
- The base class does not define typed identity, provenance, temporal validity, lineage, or relationships.
- Its broad docstring describes future extensibility, not current concrete object coverage.

## `Document`

**Implementation:** `app/knowledge.py`

**Purpose:** A normalized representation of a filesystem document.

**Important fields:** In addition to the base fields, `Document` stores `source_path`, source-qualified `relative_path`, `file_type`, parser name, byte size, modification time, and content hash.

**Current usage:** Parsers create `Document` objects through `document_from_text()`. Normalization qualifies paths by source, recalculates identity, deduplicates identical content during a normalization run, and persists one JSON object per normalized document. Document identity is derived from the qualified relative path and content hash. External acquisition also promotes parsed external material into this same normalized document corpus, adding curated external provenance to metadata rather than creating a separate external-document subclass.

**Limitations:**

- The object models the publication/container, not the claims, observations, entities, or relationships inside it.
- A changed file produces a new path-and-content-hash identity, but there is no explicit revision, supersession, or version-lineage relationship between editions.
- Source facts are spread across direct fields, `source`, and `metadata`.
- Institutional and external documents share the same class; their distinctions depend on metadata completeness and downstream classification.

## `ConstitutionalKnowledgeObject`

**Implementation:** `app/constitution/objects.py`

**Purpose:** A typed normative observation derived from an authoritative institutional source. It preserves constitutional knowledge separately from empirical evidence and does not itself make an alignment judgment.

**Important fields:**

- `constitutional_type`, constrained by `ConstitutionalType` (`mission`, `vision`, `strategic_compass`, `strategic_plan`, `academic_master_plan`, `board_priority`, `institutional_value`, `learning_outcome`, `governance_principle`, or `other`);
- `principles`;
- `institutional_scope`;
- `effective_from` and `effective_until`;
- `source_knowledge_object_id`, linking the observation to its normalized source object.

**Current usage:** `ConstitutionalObserver` derives these objects from normalized source documents configured in `config/institutional_constitution.yaml`. `ConstitutionalCatalog` loads them from `storage/constitutional`, and constitutional retrieval shares the vector index while preserving a separate constitutional allocation and reasoning channel. The current configuration defines the CNU Strategic Compass and its four principles.

**Limitations:**

- Principles and institutional scope are strings rather than references to shared entities or concept identifiers.
- Effective dates remain optional strings with no common temporal model.
- The source link is an identifier, not a typed relationship object with provenance of the derivation process.
- The constitutional catalog is currently narrow and manually curated.

## Objects adjacent to, but not derived from, `KnowledgeObject`

Several important records participate in the evidence pipeline without being persistent Knowledge Objects:

- `SourceDocument` is an acquisition-layer identity and provenance record. It stores authority, acquisition method, path, content hash, retrieval time, publication date, URL, and media type. It deliberately excludes parsed text and semantic interpretation.
- `Chunk` is a derived searchable segment keyed to `knowledge_object_id`, with character offsets, citation data, and inherited metadata.
- `RetrievalResult` is a runtime projection of an indexed chunk with vector/reranker score information, citation data, and metadata.
- `Evidence`, `EvidenceFitnessAssessment`, and `EvidenceRoleAssessment` are service-derived interpretations, not factual corpus objects.
- `ProgramEntity`, `InstitutionalEntity`, `InstitutionalRelationship`, and the Dashboard V2 participation contracts are typed semantic models, but they are not part of the persisted KnowledgeObject hierarchy.

This separation is generally healthy, but it means the effective ISO ontology is broader than its formal `KnowledgeObject` inheritance tree.

# 2. Existing Semantic Entities

## Explicit persisted entities

### Documents and publications

Normalized files are explicit `Document` objects. They have identity, content, source location, parser facts, timestamps, and a content hash. Curated external publications additionally carry issuing authority, authority class, evidence role, decision types, evidence domains, canonical URL, document type, geographic scope, effective period, version, and refresh metadata through `external_provenance` and copied metadata fields.

### Constitutional observations

Constitutional objects explicitly represent a typed normative source, its principles, institutional scope, effective period, and origin document. The Strategic Compass is the currently configured instance.

## Explicit catalog or contract entities outside persistence

### Academic programs

`ProgramEntity` in `app/control_plane/entities.py` explicitly represents cataloged academic programs with stable IDs, names, aliases, status, degree type, department, school, first catalog year, accreditation labels, and metadata. `config/institutional_programs.yaml` currently supplies Electrical Engineering, Computer Engineering, Computer Science, Information Science, Cybersecurity, and Physics. These are factual catalog entries, not Knowledge Objects.

### Proposed institutional concepts

`InstitutionalConcept` represents a concept mentioned in a question but not asserted to exist. It carries a name, concept type, `asserted=False`, confidence, and extraction method. The control plane recognizes proposed academic programs, concentrations, certificates, tracks, specializations, and pathways. This is a semantic interpretation of a question, not an institutional fact.

### Institutional topology nodes

`InstitutionalEntity` represents topology nodes with an ID, name, `EntityType`, and metadata. Supported types are department, program, college, curriculum, strategic goal, accreditor, facility, institution, and other. The current bootstrap catalog instantiates a limited set of departments, programs, and curricular functions. It is explicitly a curated architecture-validation model rather than a complete institutional inventory.

### Acquisition authorities and resources

The acquisition layer explicitly models source authorities, curated source definitions, and individual external resources. `SourceAuthority` distinguishes institutional primary, state, federal, accreditation, peer-institution, external-secondary, user-supplied, and unknown authority. The external registry also represents acquisition mode, supported decisions/domains, refresh policy, extraction method, document type, version, effective period, URL, and geographic scope.

### Institutional participation functions

Dashboard V2 has presentation-level contracts for an `InstitutionalParticipationProfile`, `ParticipationFunction`, and `ParticipationRelationship`. They can represent an academic unit, organizational facts, instructional functions, institutional capabilities, evidence status, missing evidence, named alternative providers, and function-level substitutability status. These contracts are deterministic inputs to presentation; no persistent collection of unit profiles currently exists.

## Explicit service vocabularies

The following are modeled explicitly but are classifications or assessments rather than institutional entities:

- `DecisionType`, including academic program, academic workforce planning, enrollment planning, budget/finance, state policy, accreditation, strategic planning, and general institutional questions;
- `QuestionScope`: single entity, multiple entities, institution-wide, or unresolved;
- `EvidenceClass`: constitutional, institutional, planning, historical, external standard, external comparator, or background;
- derived `EvidenceRole`: external trends, workforce demand, regulatory/accreditation, institutional capacity, institutional enrollment/outcomes, institutional planning/context, comparator, financial, regional demand, contextual, or unknown;
- Evidence Fitness domain vocabularies, including the academic-program domains and the eight canonical Academic Workforce Planning domains;
- LLC Core Requirements, Areas of Inquiry, participation evidence states, and function-level substitutability states in the Dashboard V2 presentation contract.

These vocabularies derive meaning from evidence or constrain presentation. They should not be mistaken for facts stored in Knowledge Objects.

## Concepts currently implicit in document text or metadata

The corpus may mention many institutional concepts that are not modeled as independently identified objects:

- courses, sections, prerequisites, and course-to-program mappings;
- program requirements and LLC course designations;
- faculty members, faculty positions, qualifications, workloads, and line assignments;
- enrollments, completions, applications, retention, and other time-series observations;
- budgets, compensation, costs, revenues, savings assumptions, and allocations;
- facilities, laboratories, equipment, capacity, and space assignments;
- accreditation requirements, local compliance status, and compliance margin;
- partnerships, employers, research centers, advisory groups, and comparator institutions;
- institutional capabilities such as advising, research supervision, governance, community engagement, and cross-program instruction;
- claims, measurements, assumptions, recommendations, and the temporal or organizational scope of individual statements.

Some of these concepts appear as strings in metadata, topic taxonomies, topology nodes, or presentation contracts. That does not yet make them canonical corpus entities.

# 3. Existing Relationships

## Explicit relationships

### `source_knowledge_object_id` / derived-from source

`ConstitutionalKnowledgeObject.source_knowledge_object_id` explicitly links a constitutional observation to the normalized source Knowledge Object. `ConstitutionalObserver` also records `derived_from_knowledge_object_id` in metadata. Semantically this is a **derived from** relationship, although the repository does not define a general relationship type for it.

### Chunk membership

Every `Chunk` carries a `knowledge_object_id`, chunk index, and character offsets. This explicitly means that the chunk is **derived from / contained by** one Knowledge Object. Embedding and vector-index records preserve that identifier. The relation is implemented as foreign-key-like data, not an ontology edge.

### Topology relationships

`InstitutionalRelationship` is the only general typed entity-to-entity relationship contract. It represents a directed edge with `source_id`, `target_id`, relationship type, confidence, rationale, optional evidence references, and metadata. Implemented relationship types are:

- `supports`;
- `requires`;
- `contributes_to`;
- `depends_on`;
- `accredits`;
- `shares_resources_with`.

The query layer preserves direction, provides incoming and outgoing traversal, and derives inverse views such as supported-by and contributed-to-by. `EvidenceReference` can cite a supporting source ID, label, locator, and note. The bootstrap graph currently uses mainly `supports` and `contributes_to`; the existence of an enum value does not establish that a corresponding relationship is populated.

### Participation relationships

`ParticipationRelationship` represents `source` — `relationship` — `target`, plus string evidence references. `ParticipationFunction` associates a named institutional function with evidence, missing evidence, substitutability status, and alternative providers. These are explicit within a supplied participation profile, but are presentation-level contracts and do not share IDs or relationship types with the topology.

## Partly explicit or string-valued relationships

- `ProgramEntity.department` and `.school` express **belongs to**, but the targets are strings rather than entity references.
- `ProgramEntity.accreditation` associates a program with accreditor labels, but not with an `InstitutionalEntity` or a specific accreditation requirement.
- external source and resource definitions associate authorities with supported decision types and evidence domains.
- external-document metadata connects a normalized document to its authority and registry provenance.
- Evidence Fitness `topic_support` associates retrieved evidence with decision domains through counts, grades, scope, directness, and limitations; this is a derived assessment rather than a persisted evidentiary edge.
- Decision Brief evidence groups and citation numbers associate evidence with topics and narrative claims operationally, but there is no durable claim-to-source relationship object.

## Relationships not currently explicit

The implementation does not yet provide canonical relations for course ownership, prerequisite chains, courses satisfying LLC requirements, faculty assigned to programs, budgets allocated to units, facilities used by functions, observations measured for entities over time, document revision/supersession, or claims supported/contradicted by evidence. These may be discussed in source text or rendered as unknowns, but they are not represented in the normalized ontology.

# 4. Current Strengths

## Clear facts-versus-meaning boundary

The repository consistently treats acquisition provenance and normalized text as facts while placing decision type, scope, evidence class, role allocation, fitness, topology impact, and readiness in services. This prevents retrieval-time judgments from silently becoming permanent institutional facts.

## Strong provenance foundation

The combination of `SourceDocument`, append-only acquisition manifests, content hashes, canonical URLs, authority classification, retrieval timestamps, extraction methods, source-qualified paths, and external provenance provides a strong basis for auditability. Provenance fields survive normalization and chunking into retrieval records.

## Constitutional and empirical separation

Constitutional objects are typed, separately cataloged, separately allocated, and separately presented. Institutional values inform reasoning without being treated as empirical proof. This is one of the ontology's strongest and most deliberate distinctions.

## Deterministic identity and derivation

Documents and chunks receive reproducible hash-based identities. Chunks preserve their parent object ID and exact character range. Constitutional objects preserve their source object ID. These choices make evidence traceable back toward original material.

## Explicit authority semantics

Authority is asserted at acquisition rather than inferred solely from text. The acquisition registry distinguishes the relevance of an authority from its acquisition mode, and it records document type, geographic scope, version, and effective period.

## Evidence-backed topology contract

Topology relationships are directed, typed, confidence-bearing, and capable of carrying evidence references. Query services distinguish incoming from outgoing edges and preserve an absence-of-evidence caveat. This is a sound starting contract even though the populated graph is small.

## Honest unknown states

Evidence Fitness and participation presentation use Missing, Weak, Partial, Not Yet Available, Not Assessed, and Insufficient Evidence rather than converting absent facts to zero or inventing relationships. That epistemic discipline is essential for future ontology growth.

# 5. Current Weaknesses

## The persisted ontology is still document-centric

Only documents and constitutional observations are concrete Knowledge Objects. Most institutional facts remain embedded in prose, spreadsheets, or open metadata. ISO can retrieve relevant passages, but it cannot yet reliably query a canonical roster of units, courses, requirements, capacities, or observations.

## Entity identity is fragmented

An academic program can appear as:

- a `ProgramEntity` with an ID such as `program.physics`;
- a topology `InstitutionalEntity` with a different identifier convention such as `program:mechanical_engineering`;
- an unasserted `InstitutionalConcept` extracted from a question;
- a string in document metadata, evidence domains, or a participation relationship.

Departments and colleges similarly occur as topology nodes, program fields, participation-profile strings, or prose. There is no shared identity authority across these representations.

## Relationship models are duplicated and disconnected

The topology has typed, ID-based relationships; the participation profile has string-based relationships and function associations; program membership is stored in string fields; and derivation is encoded in special ID fields. These models serve different layers, but there is no common relation identity or clear interoperability boundary.

## Provenance is rich but distributed

Source identity and provenance are split among `SourceDocument`, acquisition manifests, `Document` fields, `source`, `metadata`, nested `external_provenance`, chunk citations, chunk metadata, retrieval results, and topology `EvidenceReference`. Consumers often check multiple locations for the same logical property. This increases the risk of inconsistent authority, title, path, date, or role interpretation.

## Evidence terminology overlaps

`EvidenceClass`, source `evidence_role`, derived `EvidenceRole`, `SourceAuthority`, external `document_type`, Evidence Fitness topics, and decision-readiness domains are related but non-equivalent vocabularies. Their separation can be appropriate, but their boundaries are not represented by a single explicit semantic contract. The same phrase, especially “evidence role,” can mean a curated source label or a derived decision function.

## Temporal representation is incomplete

Acquisition time and publication date are typed on `SourceDocument`, while normalized objects commonly store ISO strings. Constitutional validity, external effective period, version, document modification, and question-time relevance use different fields and levels of precision. There is no common distinction among observed-at, valid-from/to, published-at, acquired-at, and superseded-at.

## No first-class claims or observations

The system cannot persistently distinguish a source's assertion from an observed institutional measurement, a formal external requirement, a local implementation practice, or an analyst inference at statement granularity. Evidence classification partially addresses this during reasoning, but the ontology does not represent individual claims and their scopes.

## Limited schema governance and migration support

The constitutional configuration has a schema version and the external registry is structured, but individual Knowledge Objects have no schema version, vocabulary version, validation registry, or migration path. Unknown `object_type` values fall back to the permissive base object.

## Curated topology can be mistaken for institutional completeness

The bootstrap topology contains useful illustrative institutional relationships, but it is manually encoded and intentionally incomplete. Several relationships have rationale and confidence but no `EvidenceReference`. It must not be treated as a comprehensive digital twin or as evidence that unrepresented relationships do not exist.

## Derived runtime metadata mutates retrieval projections

Evidence construction adds classes, roles, citation labels, and rationales to `RetrievalResult.metadata`. This does not mutate canonical Knowledge Objects, which preserves the facts/meaning boundary, but it means the same metadata mapping carries both inherited source facts and ephemeral service judgments. Consumers must know which keys are factual and which are derived.

# 6. Candidate First-Class Objects

The following concepts recur across configuration, documents, services, missing-evidence reports, and presentation. They are candidates for future first-class representation, not recommendations for immediate new classes.

## Institutional structure

- **Institution** — the organizational root and scope authority.
- **Academic Unit** — a common identity for college, school, department, and similar organizational units.
- **Academic Program or Program Offering** — alignment of the control-plane program catalog with topology and future factual program records.
- **Course and Section** — course identity, offering, ownership, capacity, and delivery period.
- **Curricular Requirement** — program requirements, prerequisites, and LLC Core Requirement or Area of Inquiry designations.

## Institutional operations and observations

- **Enrollment / Outcome Observation** — time-bounded enrollment, completions, applications, retention, yield, or demand measurements with unit and population scope.
- **Faculty Position / Workforce Capacity Observation** — positions, FTE, qualifications, workload, vacancies, and capacity without evaluative faculty ranking.
- **Financial Observation / Allocation** — budget, compensation, cost, revenue, savings, and resource allocation with period and organizational scope.
- **Facility and Equipment Resource** — laboratories, space, instruments, capacity, ownership, and supported functions.
- **Institutional Capability or Function** — teaching, advising, research supervision, accreditation support, governance, partnership, and community functions already recurring in AWP-4.

## Constraints and external context

- **Accreditation or Regulatory Requirement** — the formal requirement separately from local self-study assertions, implementation practices, compliance observations, and inferred risk.
- **External Authority / Publication** — consolidation of authority identity and publication/version facts currently distributed across registry and document metadata.
- **Partner, Employer, or Comparator Institution** — evidence-backed external relationships and comparisons.

## Evidence semantics and lineage

- **Observation or Claim** — a source-bounded assertion with subject, scope, time, and provenance.
- **Evidence Reference / Support Relation** — a reusable link from a claim, topology relation, or decision domain to exact source material.
- **Document Version / Supersession Relation** — lineage among drafts, editions, reporting years, and replaced sources.
- **Decision Context, Assumption, and Scenario** — explicit inputs for later Scenario Modeling, kept separate from institutional facts and recommendations.

These candidates should be prioritized by demonstrated query and evidence needs, not by a desire to make every noun an object.

# 7. Architectural Opportunities

## Richer Semantic Layer

A shared identity spine for institution, academic units, programs, courses, curricular requirements, authorities, and resources would let the control plane resolve concepts against the same factual entities used by topology and retrieval. It would also make “existing entity” versus “proposed concept” a stable semantic distinction across services.

## More precise Evidence Fitness

Entity-, time-, authority-, and scope-aware observations would allow fitness services to distinguish document presence from decision fitness without relying heavily on keywords and document-level metadata. Coverage could be assessed against explicit units, periods, measures, and constraints while remaining deterministic and inspectable.

## Scenario Modeling inputs

First-class functions, capacities, requirements, costs, and dependencies would expose the inputs that scenario services need. Scenario results should remain derived meaning: the ontology would supply facts and assumptions, not encode recommendations or department rankings.

## Institutional Digital Twin

The existing topology supplies the beginnings of a directed institutional network. A future twin could connect stable institutional entities to time-bounded observations and evidence-backed relationships. The present bootstrap graph should evolve through provenance-preserving additions, not be treated as a complete twin today.

## Unified provenance without loss of source detail

The current provenance data can support a common provenance vocabulary linking acquisition artifacts, normalized publications, chunks, claims, observations, and derived constitutional objects. This would reduce duplicated lookup logic while preserving exact original paths, URLs, hashes, timestamps, and extraction methods.

## Explicit vocabulary boundaries

Documenting and eventually formalizing the distinction among authority class, evidence class, curated source role, derived decision role, evidence domain, and decision-readiness domain would make both code and diagnostics easier to interpret. Generalization should preserve these different semantic purposes rather than collapse them into one opaque category.

# 8. Recommended Evolution Path

## Low-risk improvements

1. **Publish a canonical inventory of object types and vocabularies.** Treat the current hierarchy, catalogs, relation types, evidence classifications, and identifier conventions as an explicit baseline before adding types.
2. **Separate factual and derived metadata namespaces conceptually.** Identify which current metadata fields come from acquisition/normalization and which are added by retrieval or reasoning services.
3. **Standardize provenance and temporal terminology.** Define the meanings of source identity, publication date, effective period, observed period, acquisition time, and derivation without changing existing persistence contracts prematurely.
4. **Establish crosswalks among existing identities.** Document correspondences among program catalog IDs, topology IDs, display names, and source metadata before selecting a canonical identifier strategy.
5. **Add schema validation at boundaries incrementally.** Validate newly produced objects and metadata while retaining backward-compatible loading of the existing normalized corpus.

## Medium-term changes

1. **Promote the highest-value recurring facts first.** Academic units, programs, courses/curricular requirements, and time-bounded enrollment or workforce observations have immediate value for the Semantic Layer and Evidence Fitness.
2. **Introduce reusable, evidence-backed relationship semantics.** Align topology, participation, membership, derivation, and support links without forcing presentation contracts or service assessments into persistence.
3. **Represent statement scope and role explicitly where provenance supports it.** Preserve the difference among formal requirements, institutional self-study assertions, operating records, and analyst inference.
4. **Add version and lineage semantics.** Connect revisions and effective periods rather than relying only on family normalization during retrieval.
5. **Use adapters and dual reads during migration.** Existing documents, chunks, vector records, Decision Briefs, and public retrieval contracts should continue to function while richer objects are introduced.

## Long-term vision

The mature ontology can serve as the factual substrate for an evidence-backed, temporal Institutional Digital Twin: stable entities connected by provenance-bearing relationships and time-bounded observations. The Semantic Layer can resolve questions into that substrate; Evidence Fitness can assess coverage and applicability; and Scenario Modeling can derive consequences from explicit facts and assumptions. Constitutional knowledge should remain a distinct normative channel throughout.

This evolution should remain incremental. The current normalized document corpus is valuable and should continue to coexist with structured objects. New structure should be introduced only where it improves traceability, semantic resolution, evidence fitness, or scenario inputs—and never by converting uncertain text into asserted institutional fact without provenance and validation.
