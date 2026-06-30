# Session 7 — From Prototype to Engineering

*Project Design History*

---

**Date**

June 2026

---

# Introduction

With the first end-to-end RAG system operational, the emphasis shifted from proving that the
architecture worked to understanding **how well** it worked.

A central realization emerged:

> A retrieval system should be engineered like a scientific instrument.

Rather than evaluating isolated examples, the project began building a repeatable experimental
framework capable of measuring retrieval quality, diagnosing failures, and supporting systematic
optimization.

---

# Major Milestones

- Added retrieval diagnostics exposing every pipeline stage:
  - raw FAISS candidates
  - post-deduplication
  - post-reranking
  - final context sent to the LLM
- Introduced configurable rerank thresholds.
- Tuned chunk size and rebuilt the vector database.
- Profiled retrieval latency and eliminated repeated model-loading overhead, reducing benchmark
  runtime dramatically after the initial warm-up query.
- Built the first retrieval benchmark suite.
- Expanded the benchmark from a handful of examples to thirty representative questions spanning
  policies, advising, astronomy, ABET, operations, and course materials.
- Added category-level benchmark summaries.

---

# From Anecdotes to Experiments

Early tuning naturally focused on individual queries. As the project evolved, this approach was
recognized as insufficient.

Instead, retrieval quality became something that could be measured objectively using benchmark
questions with expected sources, acceptable alternatives, and known undesirable documents.

This marked a philosophical transition from debugging examples to performing controlled experiments.

---

# Benchmarking

The benchmark framework evaluates:

- required documents
- acceptable documents
- undesirable documents
- retrieval rank
- latency
- retrieval-stage diagnostics

The benchmark has become the primary tool for guiding architectural decisions.

---

# Looking Ahead

The benchmark framework enables future work including:

- embedding model comparisons
- reranker evaluation
- hybrid dense/BM25 retrieval
- adaptive retrieval pipelines
- heterogeneous retrieval strategies

The Department Knowledge Assistant has become not only an application, but also a retrieval
research platform.
