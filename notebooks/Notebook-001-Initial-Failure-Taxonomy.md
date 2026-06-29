# Notebook-001 — Initial Failure Taxonomy

**Project:** Department LLM Assistant / Semantic Observatory
**Date:** 2026-06-29

## Purpose

The objective of this notebook is not simply to record benchmark failures, but to understand why retrieval systems fail. The long-term goal is to develop a taxonomy of semantic retrieval failure modes.

## Current Benchmark

- Cases: 30
- Required Top-1: 23 / 30
- Required Top-5: 25 / 30

Four distinct retrieval failures have been identified.

---

## Failure 1 — Faculty Travel Procedures

**Diagnosis:** Metadata ambiguity

Multiple travel-related policy documents discuss reimbursement, per diem, lodging, and procedures. The retriever correctly finds semantically similar documents but cannot reliably distinguish document identity from document topic.

Potential mitigations:

- Richer metadata
- Title weighting
- Directory-aware ranking
- Document-type priors

---

## Failure 2 — SERC March Events

**Diagnosis:** Lexical hijacking

FAISS retrieves the correct spreadsheet near the top, but the reranker promotes course syllabi due to lexical overlap.

Potential mitigations:

- Metadata-aware reranking
- Document-type features
- Confidence thresholds
- Directory priors

---

## Failure 3 — CS Machine Learning Physics Recommendation

**Diagnosis:** Semantic overshadowing

Large ABET documents satisfy much of the query while missing the critical advising intent.

Potential mitigations:

- Hybrid retrieval
- Intent-aware reranking
- Structured metadata
- Multi-stage retrieval

---

## Failure 4 — Travel Vehicle Policy

Investigation pending.

---

# Emerging Failure Taxonomy

## Class I — Metadata Ambiguity

## Class II — Lexical Hijacking

## Class III — Semantic Overshadowing

## Class IV — Pipeline Robustness

---

# Research Direction

Rather than merely measuring Recall@k, this project seeks to classify recurring semantic retrieval pathologies. Each benchmark failure becomes an observational specimen.

---

# Next Steps

1. Complete remaining failure investigations.
2. Expand the taxonomy.
3. Build an observatory dashboard.
4. Compare failure distributions across embedding models.
5. Study how architectural changes alter ecosystem behavior.
