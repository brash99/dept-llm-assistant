# Retrieval Pipeline

Retrieval is an Evidence Layer subsystem. It identifies relevant Knowledge Object chunks while preserving source identity, provenance, object type, and engineering diagnostics. It does not answer the institutional question or determine evidence sufficiency.

## Current pipeline

```text
Question
  → FAISS candidate search
  → constitutional fallback when its quota is under-filled
  → exact/text/path deduplication
  → optional cross-encoder reranking
  → document-family diversification
  → optional reranker threshold
  → constitutional and empirical quotas
  → final evidence set
```

Configuration is read from `config/settings.yaml`. The production defaults use a sentence-transformer embedding model, GPU execution, cross-encoder reranking, and separate constitutional/empirical quotas.

## Exact deduplication

`dedupe_by=relative_path` uses a cross-format canonical document key. It removes duplicate representations such as PDF and DOCX versions of the same source path. This behavior remains separate from document-family diversity.

## Reranking

When enabled, a cross-encoder evaluates each `(question, chunk)` pair. The original FAISS score is retained in metadata and the reranker output becomes the ranking value. Cross-encoder logits are uncalibrated engineering values; they are not executive confidence percentages.

## Document-family diversity

After reranking, ISO derives a conservative family key from existing provenance and filenames. Normalization removes obvious version, draft/final, date, punctuation, and duplicated-extension noise. It also groups recognized ABET self-study packages and criterion-response variants while preserving identified programs and distinct criterion numbers.

The configured maximum is applied in ranked order, so the highest-ranked members survive. Removed candidates and their family keys remain visible in retrieval traces.

Family grouping is deliberately heuristic. It does not run an additional embedding model or claim two documents are semantically identical.

## Threshold and evidence allocation

An optional minimum reranker score is applied after family diversification. The final stage selects constitutional and empirical results independently. Constitutional fallback can add constitutional candidates when ordinary vector search does not satisfy the requested constitutional quota.

## Diagnostics

`RetrievalReport`, `RetrievalTrace`, and `RetrievalProfile` expose:

- raw candidate count;
- exact-deduped candidates;
- reranked candidates;
- family-diversified and family-removed candidates;
- thresholded candidates;
- final results;
- family keys and configured maximum;
- FAISS and reranker scores; and
- timing by stage.

Streamlit Developer Mode renders these stages. The executive source list omits raw logits.

## Evidence roles after retrieval

Selected results are classified after retrieval. Important distinctions include:

- Institutional Evidence;
- Institutional Self-Study;
- Planning Document;
- Formal External Standard;
- External Comparator;
- Constitutional Evidence; and
- Contextual Reference.

An ABET self-study or local criterion response is institutional evidence about what a program reports. It is not automatically the formal ABET standard. Conversely, formal criteria do not prove current local compliance.

## Known limitations

- FAISS similarity and cross-encoder relevance do not establish factual truth.
- Filename/metadata family rules cannot detect every semantic duplicate.
- Corpus concentration can still limit evidence diversity when no alternative relevant sources exist.
- Retrieval presence is not Evidence Fitness.
- The current benchmark script does not serialize the family-diversity stage as a separate top-results list, although its report includes the new fields and Streamlit exposes the stage.

Operational commands are maintained in [A100 Operations](../operations/a100.md) and [Benchmarking](../engineering/benchmarking.md).
