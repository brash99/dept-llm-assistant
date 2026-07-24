# Institutional Semantic Observatory

The Institutional Semantic Observatory (ISO) is an evidence-centered
decision-support system for Christopher Newport University. It represents
institutional facts as governed Knowledge Objects and uses deterministic
services to derive identities, relationships, metrics, evidence limitations,
and decision-ready institutional views.

> Knowledge objects store facts. Services derive meaning.

ISO does not model institutional reports as reality. ISO models the
institution. Reports are evidence about that model and may be explained,
validated, or reproduced as consequences of the underlying institutional
structure.

ISO must not manufacture a recommendation when the evidence or governing
assumptions are inadequate.

## Permanent architecture

ISO uses one permanent six-layer architecture:

1. **Evidence Layer** — acquisition, manifests, normalization, Knowledge
   Objects, schedule/catalog/directory observations, constitutional objects,
   chunking, embeddings, indexing, retrieval, and provenance.
2. **Semantic Layer** — governed institutional units, subject ownership,
   identities, aliases, programs, majors, capstones, curriculum policy,
   classification, and institutional relationships.
3. **Reasoning Layer** — analytical workforce decisions, department profiles,
   SCH and LLC aggregation, attribution views, graduate proxies, grounded
   answers, and Decision Briefs.
4. **Evidence Fitness** — directness, authority, scope, coverage, temporal
   fitness, limitations, missing evidence, and decision readiness.
5. **Scenario Modeling** — planned; governed comparison of explicit workforce
   alternatives and assumptions.
6. **Institutional Digital Twin** — aspirational; a temporal, evidence-backed
   representation of institutional state, dependencies, and change.

See [Architecture Overview](docs/architecture/01_architecture_overview.md) and
[Current Status](docs/status.md).

## Current capabilities

The current implementation includes:

- governed current, historical, program, college/school, and administrative
  institutional units;
- governed subject-prefix ownership and catalog/schedule discrepancy auditing;
- deterministic faculty identity across directory, catalog, roster, and
  schedule evidence;
- distinct faculty-appointment, administrative-appointment, employment-status,
  and teaching-assignment observations;
- a reviewed 282-person Current Analytical Workforce with governed department
  assignments;
- 18 reconciled Department Profiles;
- complete production SCH input coverage for those profiles across the
  available governed schedule evidence;
- curriculum-owned SCH and a separate workforce-attributed SCH metric with
  explicit prefix-owner fallback;
- governed LLC designation policy and LLC SCH;
- a governed Undergraduate Major Registry;
- a separate governed Major → Capstone Registry; and
- a partially estimable capstone-enrollment graduate proxy that remains
  independent of administrative graduation reports.

These capabilities are deterministic and inspectable. The 282-person workforce
is an analytical baseline derived from public evidence and institutional
review, not an authoritative effective-dated HR roster.

## August milestone

The primary August workforce-planning question is:

> If CNU reduces full-time instructional faculty from approximately 275 to
> approximately 250, which departments should lose positions?

ISO now has credible foundations for describing current analytical workforce,
faculty home, curriculum ownership, instructional delivery, SCH, LLC
instruction, majors, capstones, and partial completion proxies. It does not yet
have a production Scenario Modeling service that can responsibly rank
departments or recommend reductions.

A reduction decision requires more than one uniform ratio. Departmental
functions differ semantically:

- laboratory and studio instruction may depend on facilities and section
  structure;
- service-teaching departments may deliver substantial curriculum outside
  faculty home;
- accreditation and licensure programs may have externally constrained
  coverage;
- language, performance, research, advising, governance, and administrative
  obligations create different capacity evidence;
- temporary, visiting, adjunct, and externally funded instruction may affect
  structural workforce interpretations differently.

ISO therefore models these institutional relationships explicitly rather than
forcing every department into one spreadsheet definition. Administrative
reports remain valuable evidence for validation and reconciliation, but they do
not define the underlying model.

Until authoritative appointment/FTE evidence, financial effects, curriculum
dependencies, substitutability assumptions, and governed scenario choices are
available, ISO should explain evidence and limitations rather than produce a
false reduction ranking.

## Environments

Mac development checkout:

```text
/Users/brash/dept-llm-assistant
```

Canonical A100 production checkout:

```text
/work/brash/dept-llm-assistant
```

Governed normalized evidence may exist and be tracked on the Mac, but it must
not automatically be assumed identical to the current A100 production state.
Verify the checkout, evidence inventory, and deterministic fingerprints before
drawing production conclusions.

- Use [macOS Development](docs/operations/macos.md) for editing and Mac-safe
  validation.
- Use [A100 Operations](docs/operations/a100.md) for production evidence,
  model-dependent validation, ingestion, and indexing.
- Use committed scripts under `scripts/a100_testing_scripts/` for durable
  production validation workflows.

## Documentation map

- [Documentation index](docs/README.md)
- [Current implementation status](docs/status.md)
- [Architecture Book](docs/architecture/README.md)
- [A100 operations](docs/operations/a100.md)
- [macOS development](docs/operations/macos.md)
- [Testing and validation](docs/operations/testing.md)
- [Configuration reference](docs/operations/configuration.md)
- [Decision Briefs](docs/decision_support/decision_briefs.md)
- [Glossary](docs/reference/glossary.md)

## Safety

Corpus synchronization, clearing derived data, rebuilding embeddings or
indexes, deployment, and Git publication change shared state. Inspect commands
before running them. `scripts/sync_drive.sh` uses `rclone sync`, and
`scripts/run_full_pipeline.sh` clears derived outputs before rebuilding them.
