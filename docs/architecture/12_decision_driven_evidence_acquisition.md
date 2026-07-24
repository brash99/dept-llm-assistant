# Decision-Driven External Evidence Acquisition

## Status

Implemented as a curated Evidence Layer pilot for Academic Program decisions,
including the Health Physics benchmark. It is not a generic crawler and is not
invoked by Decision Brief generation.

## Architectural boundary

The service belongs entirely to the **Evidence Layer**. Evidence Fitness
identifies missing domains and supplies a contract to the planner, but does not
perform acquisition. The Decision Brief pipeline remains a consumer of the
normalized corpus and has no acquisition responsibility.

The permanent architecture remains:

1. Evidence Layer
2. Semantic Layer
3. Reasoning Layer
4. Evidence Fitness
5. Scenario Modeling
6. Institutional Digital Twin

Knowledge Objects store acquired facts and provenance. Deterministic services
derive the acquisition plan, validation result, and promotion status.

## Data flow

```text
EvidenceFitnessAssessment.missing_topics
    -> EvidenceAcquisitionPlanner
    -> ordered AcquisitionPlan
    -> explicit curated URLs only
    -> external staging bytes + provenance sidecar
    -> extraction/provenance/authority/freshness/duplicate validation
    -> existing normalize_single_file path
    -> provenance-enriched normalized Knowledge Object
    -> existing chunk/embed/index workflow
```

Planning occurs before network access. A dry run performs no retrieval.

## Contracts

- `ExternalSourceRegistry` loads ordered authorities and resources from
  `config/external_evidence_sources.yaml`.
- `EvidenceAcquisitionPlanner` accepts any assessment exposing decision type,
  label, and missing topics. It contains no Health Physics prompt matching.
- `ExternalEvidenceAcquisitionService` stages, validates, and promotes only
  resources already present in an `AcquisitionPlan`.
- `StagedExternalDocument` carries authority, evidence role, decision types,
  domains, retrieval timestamp, effective period, version, canonical URL,
  document type, geographic scope, and refresh policy.

Additional decision types can extend the registry with supported domains
without modifying the planner.

## Staging and promotion

The default staging root is `storage/external_staging/`. Each artifact receives
a provenance sidecar. Validation rejects missing provenance, unknown authority,
unparseable or empty content, stale staged observations, and duplicate content.

Promotion calls the existing normalization pipeline. It then attaches the
validated external provenance to the resulting Knowledge Object and saves it in
`storage/normalized/`. Promoted objects become searchable only after the normal
chunk, embedding, and index build steps. Constitutional objects are not read,
modified, or merged into this corpus.

## Operation

Dry run:

```bash
cd /work/brash/dept-llm-assistant
.venv/bin/python scripts/acquire_external_evidence.py \
  --decision-type academic_program \
  --decision-label "Health Physics" \
  --missing-domain Accreditation \
  --missing-domain "Workforce Demand" \
  --missing-domain Facilities \
  --missing-domain Equipment \
  --missing-domain "Historical Precedent"
```

Add `--execute` only after reviewing the emitted plan. Execution performs
network requests to the exact canonical URLs in the registry. After promotion,
run the ordinary chunking, embedding, and vector-index workflows documented in
the A100 operations guide.

## Limitations

- The pilot uses explicit resources from seven authority families; it performs
  no search, link discovery, or comparator-institution crawling.
- Registry metadata must be reviewed as agencies publish new versions.
- Validation confirms extraction and provenance integrity, not the truth of
  every claim in a source.
- Promotion does not automatically rebuild chunks, embeddings, or indexes.
