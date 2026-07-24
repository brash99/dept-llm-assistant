# Documentation Synchronization Summary

Date: 2026-07-23

This documentation-only sprint synchronizes the repository narrative with the
current ISO implementation. It does not modify application code, scripts,
configuration, evidence, registries, generated observables, APIs, or runtime
behavior.

## Files changed

### Current entry points

- `README.md`
- `CHANGELOG.md`
- `docs/README.md`
- `docs/status.md`

### Architecture

- `docs/architecture/01_architecture_overview.md`
- `docs/architecture/23_metric_readiness_audit.md`
- `docs/architecture/27_analytical_workforce_builder.md`
- `docs/architecture/28_department_profile_builder.md`
- `docs/architecture/30_llc_designation_governance.md`
- `docs/architecture/31_undergraduate_major_registry.md`
- `docs/architecture/32_undergraduate_major_capstones.md` (new)
- `docs/architecture/33_estimated_graduates.md` (new)
- `docs/architecture/README.md`

### Operations

- `docs/operations/configuration.md`
- `docs/operations/macos.md`
- `docs/operations/testing.md`

### Preserved historical material

- Former top-level Academic Workforce Planning Semantic Model moved to
  `docs/archive/design/ACADEMIC_WORKFORCE_PLANNING_SEMANTIC_MODEL.md`
- Former top-level AI Engineering Context moved to
  `docs/archive/development_context/AI_ENGINEERING_CONTEXT.md`
- Former top-level KnowledgeObject Ontology Audit moved to
  `docs/archive/audits/KNOWLEDGE_OBJECT_ONTOLOGY_AUDIT.md`

Each archived document now has an explicit status banner and remains linked
from the documentation index.

## Contradictions resolved

- Removed claims that SCH, an active analytical population, and a department
  denominator are unimplemented.
- Documented the reviewed 282-person analytical workforce and its distinction
  from an authoritative HR roster.
- Documented 18 reconciled Department Profiles and complete production SCH
  input coverage across those profiles.
- Distinguished curriculum-owned SCH from workforce-attributed SCH and its
  explicit prefix-owner fallback.
- Documented effective-dated LLC designation governance and LLC SCH.
- Replaced the claim that capstone extraction is future work with links to the
  implemented separate capstone registry and estimated-graduate observable.
- Distinguished the partially estimable graduate proxy from authoritative
  completions and recorded the approximately 72% dated held-out coverage
  result.
- Replaced placeholder-only Mac storage language with an evidence-inventory
  and fingerprint verification requirement.
- Reframed the August milestone around implemented institutional modeling
  while preserving the absence of a production reduction-scenario engine.

## New architecture chapters

- **Undergraduate Major Capstones** documents governed Major → Capstone facts,
  relationship types, provenance, alternatives, sequences, shared capstones,
  and unresolved cases.
- **Estimated Graduates by Major** documents the independent
  capstone-enrollment proxy, Evidence Fitness, exclusions, shared-capstone
  allocation limits, and held-out administrative validation.

## Configuration and testing synchronization

The configuration reference now identifies the authoritative role of the
institutional-unit, subject-ownership, faculty-identity, workforce, roster,
LLC, undergraduate-major, and capstone registries.

The testing guide now provides verified focused test commands for:

- units and subject ownership;
- faculty identity and appointments;
- authoritative roster contract;
- analytical workforce;
- Department Profiles, SCH, and attribution;
- LLC governance;
- majors, capstones, and estimated graduates; and
- schedule evidence.

It also documents the durable `scripts/a100_testing_scripts/` workflow and
discourages long pasted Python/heredoc validation cells.

## Remaining known documentation gaps

- Scenario Modeling needs documentation when a governed scenario service is
  implemented.
- No formal ADR series currently records major contract decisions.
- Retrieval-oriented engineering guides predate some semantic workflows and
  should be reviewed when retrieval artifacts are rebuilt.
- The presentation and session archives remain historical milestone material
  and were not substantively audited in this sprint.
- Report-specific user guides for SCH timelines, fall-only comparisons, and
  workforce attribution may be useful later; their semantics are currently
  covered by the Department Profile and status documentation.

## Validation results

- Local Markdown links: passed; zero broken local links.
- Referenced scripts: passed; zero missing script paths.
- Referenced repository paths: passed; zero missing paths.
- `PYTHONPATH="$PWD" python -m compileall -q app scripts`: passed.
- `git diff --check`: passed.
- `git diff --cached --check`: passed.
- Documentation-only scope check: passed; no code, script, configuration,
  evidence, registry, observable, API, or runtime file changed.
