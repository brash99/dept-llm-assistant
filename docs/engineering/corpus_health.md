# Corpus Health

> A healthy retrieval system begins with a healthy corpus.

---

# Introduction

Retrieval-Augmented Generation (RAG) systems are often evaluated primarily by the quality of their embedding models, retrieval algorithms, rerankers, or language models.

While these components are undeniably important, they all operate on a common foundation:

**the corpus itself.**

The Institutional Knowledge Framework treats corpus quality as a first-class engineering concern.

Rather than viewing the corpus as static input, we regard it as a continuously evolving semantic ecosystem whose health directly determines retrieval quality, explainability, and ultimately the quality of AI-assisted decision making.

---

# Why Corpus Health Matters

A retrieval system cannot retrieve useful information that does not exist.

Likewise, even an excellent retrieval algorithm can perform poorly when presented with an unhealthy corpus.

Examples include:

- obsolete documents dominating retrieval
- duplicated information
- pathological documents producing enormous numbers of chunks
- poorly parsed files
- missing metadata
- imbalanced document distributions

Corpus engineering therefore complements retrieval engineering.

The objective is not merely to increase the size of the corpus, but to maximize its usefulness.

---

# Corpus Engineering

Corpus engineering is the continuous process of monitoring, evaluating, and improving the institutional knowledge base.

Typical activities include:

- refining corpus policy
- excluding low-value documents
- improving parsers
- identifying pathological documents
- monitoring parser coverage
- tracking corpus growth
- measuring semantic balance

Rather than treating preprocessing as a one-time task, corpus engineering is an ongoing component of the system architecture.

---

# Corpus Policy

Corpus policy determines which documents become part of the institutional knowledge base.

The policy exists to ensure that computational resources are devoted to information that contributes meaningfully to retrieval.

Current policy excludes, where appropriate:

- temporary files
- hidden files
- unsupported formats
- generated artifacts
- selected archival material
- low-value transactional datasets

Corpus policy is expected to evolve as the corpus evolves.

---

# Corpus Health Metrics

The framework continuously monitors a variety of corpus-level statistics.

Current metrics include:

- total documents
- total chunks
- mean chunks per document
- median chunks per document
- parser usage
- file-type distribution
- folder distribution
- largest documents
- chunk dominance
- Gini coefficient

These metrics provide quantitative evidence describing the current state of the corpus.

---

# Detecting Pathological Documents

One objective of corpus engineering is identifying documents that disproportionately influence retrieval.

Examples include:

- corrupted documents
- parser failures
- extremely large spreadsheets
- duplicated archives
- machine-generated reports

Such documents may generate thousands of semantically redundant chunks while contributing little useful information.

Removing a single pathological document can significantly improve retrieval quality while reducing computational cost.

---

# Chunk Dominance

Chunk generation should be reasonably well distributed across the corpus.

If a small number of documents generate a disproportionate fraction of all chunks, they may dominate semantic retrieval.

Dominance metrics help identify these cases.

The goal is not perfect uniformity, but the early detection of documents whose influence is inconsistent with their informational value.

---

# Corpus Inequality

The framework summarizes chunk inequality using the Gini coefficient.

High inequality indicates that relatively few documents contribute a large fraction of the corpus.

Moderate inequality is expected in institutional repositories.

Extreme inequality often signals opportunities for corpus refinement.

The Gini coefficient therefore provides a compact summary of corpus balance over time.

---

# The Semantic Ecosystem

The corpus can be viewed as a semantic ecosystem.

Within this ecosystem:

- important policies become keystone documents;
- obsolete material becomes semantic clutter;
- redundant documents compete for retrieval attention;
- pathological files behave like invasive species;
- parser improvements improve ecosystem health.

This perspective emphasizes that retrieval quality depends upon maintaining a healthy balance rather than simply increasing corpus size.

---

# Continuous Improvement

Corpus health is monitored throughout the lifetime of the framework.

As new documents are added and existing material evolves, corpus policy, parser behavior, and engineering metrics are continually refined.

Corpus engineering is therefore not a preprocessing stage.

It is a permanent architectural responsibility.

---

# Guiding Principle

The objective is not to build the largest possible corpus.

The objective is to build the healthiest possible semantic ecosystem.
