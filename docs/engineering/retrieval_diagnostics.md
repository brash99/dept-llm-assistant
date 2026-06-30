# Retrieval Diagnostics

> Making every stage of retrieval observable.

---

# Introduction

Modern Retrieval-Augmented Generation (RAG) systems often behave as black boxes.

A user submits a question.

The system produces an answer.

Between those two events lies an entire retrieval pipeline whose behavior is frequently hidden from both users and developers.

The Institutional Knowledge Framework adopts a different philosophy.

Every major stage of retrieval should be observable, inspectable, and explainable.

Retrieval diagnostics therefore form a core component of the engineering architecture rather than a debugging utility.

---

# Why Diagnostics Matter

Retrieval failures can originate from many sources.

Examples include:

- poor embeddings
- corpus imbalance
- duplicate documents
- reranker behavior
- chunking strategy
- parser failures
- prompt construction

Without visibility into the retrieval pipeline, identifying the true cause of failure becomes extremely difficult.

Diagnostics transform retrieval engineering from trial-and-error into systematic investigation.

---

# Design Philosophy

The diagnostic system is guided by four principles.

## Every transformation should be observable.

Every stage of retrieval changes the candidate set.

Each transformation should be visible.

---

## Explain intermediate decisions.

The framework should explain not only the final answer, but also how that answer was constructed.

---

## Support engineering.

Diagnostics exist primarily to improve the system.

They are engineering tools rather than user-facing features.

---

## Build trust.

Transparency increases confidence in the retrieval process.

Developers can verify that the system is behaving as intended.

---

# The Retrieval Pipeline

The current retrieval pipeline consists of several distinct stages.

```
User Question
      │
      ▼
Question Embedding
      │
      ▼
FAISS Vector Search
      │
      ▼
Candidate Chunks
      │
      ▼
Deduplication
      │
      ▼
Cross-Encoder Reranking
      │
      ▼
Selected Context
      │
      ▼
Prompt Construction
      │
      ▼
Language Model
      │
      ▼
Grounded Answer
```

Each stage performs a specific function and contributes independently to retrieval quality.

---

# Stage 1 — Vector Search

Semantic retrieval begins by embedding the user's question.

The embedding is compared against the vector database to identify semantically similar chunks.

Diagnostics include:

- retrieved chunk identifiers
- similarity scores
- document provenance
- retrieval latency

This stage prioritizes speed over precision.

---

# Stage 2 — Deduplication

Vector search frequently retrieves multiple chunks from the same document.

Deduplication reduces redundancy while preserving document diversity.

Diagnostics reveal:

- removed duplicates
- retained candidates
- document diversity

This stage helps ensure that later reasoning considers multiple sources rather than repeatedly examining the same document.

---

# Stage 3 — Cross-Encoder Reranking

The reranker jointly evaluates each candidate chunk together with the user's question.

Unlike vector similarity, this stage considers the relationship between question and evidence directly.

Diagnostics include:

- reranker scores
- ranking changes
- promoted candidates
- demoted candidates

This stage generally provides the greatest improvement in retrieval precision.

---

# Stage 4 — Context Selection

Only a subset of reranked chunks can be supplied to the language model.

The context selection stage determines:

- final chunk ordering
- context length
- document diversity
- citation coverage

Diagnostics expose the complete context ultimately provided to the language model.

---

# Stage 5 — Prompt Construction

Prompt construction combines:

- system instructions
- retrieved evidence
- citations
- user question

Although often overlooked, prompt construction significantly influences answer quality.

The framework therefore treats prompt generation as another observable transformation.

---

# Provenance

Every retrieved chunk retains complete provenance.

This includes:

- source document
- document identifier
- parser
- chunk identifier
- retrieval scores

Provenance ensures that every generated statement can be traced back to institutional evidence.

---

# Relationship to Benchmarking

Retrieval diagnostics and benchmarking are closely connected.

When a benchmark question fails, diagnostics reveal where the failure occurred.

Examples include:

- relevant documents never retrieved
- reranker incorrectly reordered candidates
- duplicate suppression removed useful evidence
- context selection excluded important material

This allows engineering effort to focus on the appropriate component.

---

# Relationship to Corpus Engineering

Many retrieval failures originate upstream.

Diagnostics often reveal symptoms of corpus problems such as:

- duplicated documents
- parser failures
- pathological chunk generation
- obsolete material dominating retrieval

Retrieval diagnostics therefore complement corpus engineering by identifying where corpus quality influences retrieval behavior.

---

# Future Directions

Future diagnostic capabilities may include:

- embedding-space visualization
- semantic neighborhood exploration
- retrieval-path visualization
- citation graphs
- evidence clustering
- uncertainty propagation
- Decision Brief evidence traces

These additions will further improve the explainability of institutional reasoning.

---

# Guiding Principle

A retrieval system should never be a black box.

Every stage of retrieval should be understandable, measurable, and explainable.
