# ISO Documentation

This directory separates current authoritative guidance from enduring design essays, research plans, examples, and historical records.

## Start here

- [Current status](status.md) — implemented, partial, planned, and aspirational capabilities.
- [Architecture overview](architecture/01_architecture_overview.md) — authoritative six-layer model.
- [A100 operations](operations/a100.md) — server launch, monitoring, ingestion, indexing, and benchmarking.
- [External evidence refresh runbook](operations/external_evidence_refresh.md) — standard curated acquisition and rebuild workflow.
- [macOS development](operations/macos.md) — local editing and lightweight validation.
- [Testing](operations/testing.md) — focused and repository-level checks.
- [Configuration](operations/configuration.md) — current settings and registries.
- [Decision-driven external acquisition](architecture/12_decision_driven_evidence_acquisition.md) — curated Evidence Fitness gap planning and staging.
- [Glossary](reference/glossary.md) — canonical terminology.

## Architecture

The [Architecture Book](architecture/README.md) describes enduring design commitments and subsystem details. Its chapters are not separate architectural layers. The permanent architecture is always:

1. Evidence Layer
2. Semantic Layer
3. Reasoning Layer
4. Evidence Fitness
5. Scenario Modeling
6. Institutional Digital Twin

## Decision support

- [Decision Briefs](decision_support/decision_briefs.md)
- [Decision Brief 001](decision_support/decision_brief_001.md) — historical benchmark specification, not current runtime output.
- [Decision-support vision](decision_support/vision.md) — directional material; consult `status.md` for implementation state.

## Engineering references

- [Benchmarking](engineering/benchmarking.md)
- [Retrieval diagnostics](engineering/retrieval_diagnostics.md)
- [Corpus health](engineering/corpus_health.md)
- [Corpus observatory](engineering/corpus_observatory.md)

## Research and principles

- [ISO Manifesto](ISO_Manifesto.md) — design values, not an implementation-status claim.
- [Research Agenda](ResearchAgenda.md) — planned and aspirational research.
- [Editorial Roadmap](EDITORIAL_ROADMAP.md)

## Historical records

The files under `sessions/`, `experiments/`, and the repository-root `Department_LLM_Assistant_Phase_II_Context.txt` record earlier development states. They may contain superseded phase terminology, commands, paths, or planned capabilities. They are retained as a laboratory notebook and are not operational instructions. See [Session archive](sessions/README.md).

Files under `presentations/` are also milestone artifacts; see the [Presentation Archive](presentations/README.md).
