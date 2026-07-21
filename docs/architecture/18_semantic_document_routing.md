# Semantic Document Routing and High-Value Classification

Generic normalized documents require routing before classification. A PDF, spreadsheet, or webpage may be an operating record, a proposal, a self-study, a formal external standard, student work, or an unrelated artifact. File format and storage location alone do not answer that question.

This Semantic Layer capability therefore uses the following flow:

```text
generic document Knowledge Object
        |
        v
factual DocumentSignalExtractor
        |
        v
reviewed family and publisher registries
        |
        v
ordered DocumentClassificationRouter
        |
        +--> one unambiguous classifier --> field-level policy
        |
        +--> unsupported / sensitive / ambiguous --> abstention
```

Knowledge Objects remain the authoritative factual record. Routing rules and classifiers propose semantic identity; policy determines which assertions may be accepted. Raw evidence, normalized text, deterministic identifiers, chunks, embeddings, and retrieval behavior are unchanged.

## Independent semantic dimensions

- `source_family` records acquisition provenance or custody. It is not authorship or authority.
- `document_type` records what kind of published artifact the evidence supports.
- `institutional_role` records the factual institutional function of that artifact, such as an operating record, planning material, or external reference.
- `authority` identifies a reviewed issuing authority. An official-site or Drive location is not sufficient unless a narrow publisher rule establishes it.
- `institutional_entities` identify the scope explicitly supported by a path or publisher rule. SEC evidence is not promoted to institution-wide CNU evidence.
- `temporal_scope` records an explicit reporting period separately from acquisition, application-authoring, filesystem, publication, and effective dates.
- `decision_domains`, evidence role, and institutional relevance remain separate. V1 does not infer them from generic topic words.

Each field can be absent independently. Partial classification is intentional: a SCHEV source can have a known family and publisher while its subtype and decision eligibility remain unknown.

## Signals and registries

`app/classification/document_signals.py` normalizes path, source, file, title, provenance, URL, and timestamp signals. Year-like strings are candidates only. The extractor never calls a filesystem timestamp a publication date or a reporting period.

`config/document_classification_registry.yaml` contains versioned, inspectable rules consumed by `DocumentFamilyRegistry` and `InstitutionalPublisherRegistry`. Rules use exact source keys and anchored path families. Each rule has an identifier, classifier, version, priority, audit policy, and risk note where useful.

The router records the selected rule in every citation. Equal-priority incompatible routes abstain instead of guessing. Unknown families remain unsupported.

## Supported V1 families

- curated external evidence with complete explicit provenance;
- SCHEV reports and statistical publications;
- the reviewed CNU Institutional Research website path;
- SEC Statistics;
- SEC Program Review;
- SEC Annual Reports; and
- SEC Planning.

Subtyping is deliberately conservative. Program Review distinguishes supporting evidence, feedback, drafts, external reviews, administrative responses, and finals only when path/title evidence is explicit. Planning proposals and drafts are never represented as implemented facts. A one-period enrollment record remains a snapshot, not a trend.

## Intentionally unsupported families

V1 does not broadly classify ABET trees, assessment material, curriculum records, syllabi, course materials, student work, capstones, generic presentations, teaching archives, or personnel records. Only separately curated external ABET objects with complete provenance are eligible. A local self-study is not a formal external standard.

Potentially sensitive custody paths—including student work, exit interviews, transcripts, personnel evaluations, and faculty searches—are flagged before routing and abstain. Reports contain identifiers, paths, policy reasons, and citations; they do not reproduce sensitive document contents.

## Policy and operations

Registered `source_family` assertions may auto-accept. Document type, institutional role, authority, and exact path-derived institutional scope are accepted with audit. Ambiguous subtypes abstain, and competing rules are explicit conflicts or routing abstentions. Policy remains field-level and does not relax thresholds for coverage.

The existing corpus command includes document routing automatically and remains dry-run by default:

```bash
export PYTHONPATH="$PWD"
python3 scripts/classify_knowledge_corpus.py \
  --dry-run \
  --report-dir storage/reports/classification
```

Reports now separate coverage for source family, document type, institutional role, authority, entities, temporal scope, and decision domains, and count results by classifier, registry rule, and abstention reason. Use `--apply` only after reviewing the manifest, conflicts, review queue, abstentions, and audit sample.

The reviewed v1 classification was applied to 480 generic documents on July 21, 2026. A post-application dry-run projected zero further changes. Existing derived chunks and vectors were not rebuilt: although the generic chunker inherits `semantic_identity`, the current retrieval artifacts predate these identities and therefore do not yet expose them to retrieval filtering or Evidence Fitness.

## Evidence Fitness relevance

This routing makes high-value evidence inspectable without converting storage proximity into authority. Future Evidence Fitness can distinguish an institutional operating record from a planning draft, a unit-scoped statistic from institution-wide evidence, and a formal external source from a local self-study. It improves the evidence foundation for Quentin's faculty-allocation question while preserving Missing or Unknown when staffing, demand, service-teaching, financial, or dependency evidence is absent.
