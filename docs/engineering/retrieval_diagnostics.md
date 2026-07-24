# Retrieval Diagnostics

Retrieval diagnostics make the Evidence Layer inspectable. They are engineering artifacts, not executive evidence grades.

## Current stages

1. **Raw FAISS candidates** — vector similarity results, plus constitutional fallback candidates when needed.
2. **After exact deduplication** — text, source-path, or cross-format relative-path duplicates removed according to `dedupe_by`.
3. **After reranking** — optional cross-encoder order with original FAISS score retained in metadata.
4. **After document-family diversity** — ranked family maximum applied.
5. **Removed by document-family diversity** — excluded candidates with inspectable family keys.
6. **After threshold** — optional minimum reranker logit applied.
7. **Final results** — separately quota-limited constitutional and empirical evidence sent downstream.

## Contracts

`RetrievalTrace` preserves candidate lists for each stage. `RetrievalReport` records counts and configuration. `RetrievalProfile` records stage timings. New family fields have backward-compatible defaults.

Important report values include:

- `num_candidates`;
- `num_after_dedup`;
- `num_after_rerank`;
- `num_after_family_diversity`;
- `num_removed_by_family_diversity`;
- `num_after_threshold`;
- `num_results`; and
- `max_per_document_family`.

## Score interpretation

- The raw result score is FAISS similarity before reranking.
- With reranking enabled, `metadata.faiss_score` preserves that value and `metadata.rerank_score` stores the cross-encoder output.
- Cross-encoder outputs may be negative. They are uncalibrated logits, not percentages, confidence, evidence strength, or decision readiness.
- Normal executive source labels omit these values. Developer Mode and failure-analysis tools retain them.

## Document-family diagnostics

Every post-rerank candidate receives `document_family_key`. Family normalization accounts for obvious revisions and selected accreditation naming conventions. Review removed paths and keys when:

- one document package dominates final evidence;
- distinct criteria appear incorrectly merged;
- program-specific self-studies lose program identity; or
- revisions still appear as independent support.

Family diversity cannot create evidence roles or source diversity that retrieval did not find.

## Diagnosing a failure

1. Confirm the expected source exists in normalized objects, chunks, embeddings, and the FAISS index.
2. Locate its rank in raw candidates.
3. Check exact deduplication and its canonical path key.
4. Check reranker displacement and both scores.
5. Check family key and removal status.
6. Check threshold behavior.
7. Check constitutional/empirical quota selection.
8. Inspect its evidence class and evidence role after selection.
9. Compare the retrieved support with Evidence Fitness; retrieval presence alone is not fitness.

## Tools

- Streamlit Developer Mode: complete interactive trace.
- `scripts/analyze_failure.py`: one configured benchmark case.
- `scripts/run_retrieval_benchmark.py`: benchmark suite and JSON log.
- `scripts/search_chunks.py`: direct search inspection.

Current A100 commands are in [A100 Operations](../operations/a100.md).
