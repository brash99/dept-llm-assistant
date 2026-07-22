# Governed Subject-to-Academic-Unit Crosswalk

> Knowledge Objects store facts. Services derive meaning.
>
> Retrieval identifies which facts matter. Analytical services determine what
> the full body of facts implies.

## Why a subject prefix is not an organizational unit

A schedule subject code identifies the published subject of a course offering.
It does not establish that a department with the same apparent name exists.
Academic programs, interdisciplinary curricula, service subjects, schools, and
university-wide offerings may all publish subject codes. ISO therefore maps a
subject only through an explicit, reviewed registry rule.

Every rule keeps formal organizational classification separate from operational
analytical role. For example, the School of Engineering and Computing is
formally a dependent school and operationally a department-equivalent
workforce unit. Its PHYS, CPSC, CYBR, CPEN, EENG, and PCSE subjects are
intentionally grouped into SEC; they are not converted into fictional
departments.

## Separate governed registries

`config/institutional_units.yaml` stores facts about institutional units.
`config/subject_ownership.yaml` stores facts about instructional subject
ownership. `AcademicUnitMappingService` derives analytical meaning from both.

Subject records include:

- subject code, display name, owning unit, and analytical unit;
- ownership relationship type;
- mapping status and method;
- repository-relative authoritative source and source type;
- rationale and confidence;
- effective starting and ending terms when known;
- review status and notes.

Mapping statuses distinguish direct mappings, department-equivalent grouping,
interdisciplinary classification, service subjects, non-workforce units,
ambiguity, missing mappings, and unsupported inputs. Review status separately
distinguishes governed, provisional, and review-required assertions.

Interdisciplinary, service, and non-workforce classifications improve semantic
coverage but are not department assignments. Provisional rules do not count as
governed workforce coverage. An unmapped subject is safer than an invented
department.

The subject registry references unit IDs rather than copying formal type,
parentage, or operational roles. This prevents organizational facts and subject
ownership from becoming a dual-write architecture.

## Mac-accessible authority inventory and PCSE correction

The initial review inspected only repository-controlled evidence:

| Source | Supported use | Limitation |
|---|---|---|
| `config/institutional_units.yaml` | Formal unit types, parentage, leadership, and operational roles for SEC, Luter, School of the Arts, and their registered subordinate units | It is not a complete CNU unit registry |
| `config/institutional_programs.yaml` | Six named SEC programs and their published aliases/school | It does not govern non-SEC subjects |
| Institutional review `institutional_review:edward_brash:pcse_subject_ownership:2026-07-22` | Governs PCSE ownership by SEC and workforce rollup to SEC | It is explicitly institutional-expert evidence, not a fabricated catalog citation |
| `storage/normalized/catalogs` on the Mac | Five catalog snapshots containing 102 academic-unit observations and 97 faculty-roster observations, including many published department names | Catalog Phase 1 deliberately excluded courses, so these objects do not assert course-prefix-to-unit relationships |
| `app/adapters/catalog_adapter.py` | Provenance and schema interpretation for those catalog objects | It cannot supply relationships that Phase 1 did not extract |

Consequently, the evidence supports six SEC subject records but does not
yet support adding Arts, Business, Nursing, Teacher Preparation, or other
subject mappings. Their prefixes remain unresolved pending an authoritative
course-prefix crosswalk or later catalog-course Semantic Layer increment.

## Audit and production inventory

`SubjectCrosswalkAuditService` validates registry structure without reading the
schedule corpus. It detects missing authority or rationale, invalid types and
roles, unknown or deprecated units, conflicting or duplicate rules, overlapping
effective ranges, and units without mappings. Its deterministic fingerprint
represents the reviewed registry independently of execution time.

`scripts/audit_schedule_subject_mappings.py` reads normalized schedule Knowledge
Objects directly. It does not load chunks, embeddings, FAISS, an LLM, or a
reranker. It reports every observed subject, offering and published-instructor
counts, term coverage, mapping facts, observation and subject coverage, and a
deterministic review queue. The queue prioritizes review effort by evidence
volume, temporal breadth, identity count, and recency; it does not rank academic
importance.

Two JSON audit reports can be compared with `--compare`. The comparison ignores
execution timestamps and reports new mappings, target/status/source changes,
ambiguity changes, coverage changes, and registry-fingerprint changes.

## Review workflow

1. On the A100, run the production inventory into a timestamped log directory.
2. Copy the unmapped review queue and relevant authoritative evidence summary
   into the separate `config/subject_mapping_review_template.yaml` workspace.
3. Review candidate relationships manually. Do not promote a name-based guess.
4. On the Mac, add only approved records to `config/subject_ownership.yaml`.
5. Run the registry audit and synthetic regression tests on the Mac.
6. Commit and push after review.
7. Pull on the A100 and repeat the production inventory.
8. Compare old and new JSON reports and retain both fingerprints.

The review template is never loaded as governed configuration. Promotion is an
explicit human-governed edit.

The governed PCSE record corrects a real coverage omission. PCSE remains a
subject-level identity and rolls up analytically to SEC; it does not establish
a Department of Physics and Computer Science. YAML supplies this relationship,
while production schedule observations supply all offering and instructor
counts.

## Evidence Fitness and architectural boundary

Mapping coverage is an Evidence Fitness property. Schedule analysis reports
workforce-mappable observations separately from interdisciplinary, service,
non-workforce, provisional, ambiguous, and unmapped evidence. Broad analytical
suitability cannot be claimed merely because every subject has some label.

This increment strengthens the Semantic Layer, Reasoning Layer, and Evidence
Fitness. It prepares governed inputs for Scenario Modeling but does not model
workload, FTE, employment history, institutional priority, or staffing cuts.
The permanent architecture remains:

1. Evidence Layer
2. Semantic Layer
3. Reasoning Layer
4. Evidence Fitness
5. Scenario Modeling
6. Institutional Digital Twin
