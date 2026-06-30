# Retrieval Benchmarking

> Engineering retrieval systems through measurement rather than intuition.

---

# Introduction

Retrieval-Augmented Generation (RAG) systems are often evaluated using anecdotal examples.

A handful of successful queries may demonstrate that a system works, but they provide little evidence that architectural changes actually improve retrieval quality.

The Institutional Knowledge Framework adopts a different philosophy.

Retrieval quality should be measured systematically using repeatable benchmark experiments.

Every significant architectural modification—including embedding models, chunking strategies, rerankers, retrieval thresholds, and corpus policy—is evaluated against a stable benchmark suite.

Benchmarking therefore serves as the primary engineering tool for guiding development.

---

# Why Benchmark?

Modern retrieval systems contain numerous configurable components.

Examples include:

- embedding models
- chunk sizes
- overlap strategies
- vector databases
- rerankers
- retrieval thresholds
- prompt construction

Without a benchmark, evaluating these choices becomes subjective.

A benchmark transforms architectural development into an experimental science.

Rather than asking

> "Does this seem better?"

the project asks

> "Does the benchmark demonstrate improvement?"

---

# Engineering Philosophy

Several principles guide benchmark development.

## Measure before modifying

Architectural changes should be evaluated rather than assumed to be improvements.

---

## Optimize the system

Benchmarks evaluate the complete retrieval pipeline.

Performance depends upon the interaction between multiple components rather than any individual algorithm.

---

## Measure retrieval—not language generation

The benchmark evaluates evidence retrieval.

Language-model performance is considered separately.

This distinction helps isolate failures originating in retrieval from those originating in reasoning.

---

## Failures are informative

Poor benchmark performance is valuable.

Failures often reveal opportunities for improving:

- retrieval
- corpus policy
- parser behavior
- benchmark design

---

# Benchmark Construction

Each benchmark question consists of several components.

## Question

A representative institutional question.

---

## Required Documents

Documents that should appear among the retrieved results.

These represent the primary evidence supporting the answer.

---

## Acceptable Documents

Alternative documents containing substantially equivalent information.

These acknowledge that institutional knowledge is often redundant.

---

## Undesirable Documents

Documents that should not dominate retrieval.

Including undesirable documents helps identify misleading retrieval behavior.

---

## Category

Each benchmark belongs to one or more categories.

Examples include:

- advising
- curriculum
- policy
- operations
- astronomy
- ABET
- administration

Category summaries reveal strengths and weaknesses across different portions of the corpus.

---

# Retrieval Diagnostics

The benchmark records every stage of retrieval.

Current diagnostics include:

- vector search candidates
- post-deduplication candidates
- reranked candidates
- final language-model context
- retrieval latency

These diagnostics make retrieval failures explainable.

---

# Interpreting Results

Benchmark scores should not be interpreted as absolute measures of system quality.

Instead, they provide a stable reference against which architectural modifications can be compared.

Examples include:

- comparing embedding models
- evaluating rerankers
- testing chunking strategies
- measuring corpus policy changes

The benchmark therefore serves as an engineering instrument rather than a performance contest.

---

# Current Baseline

The current benchmark consists of:

- 30 representative questions
- multiple institutional domains
- category-level summaries
- retrieval diagnostics
- timing instrumentation

Current retrieval performance:

- Top-1: 23 / 30
- Top-5: 26 / 30

This baseline establishes the reference point for future experimentation.

---

# Benchmark Evolution

The benchmark is expected to grow continuously.

Future additions may include:

- more institutional domains
- decision-support questions
- multi-document synthesis tasks
- temporal reasoning
- quantitative reasoning
- scenario-analysis questions

As the framework evolves, the benchmark should evolve alongside it.

---

# Relationship to Corpus Engineering

Benchmarking and corpus engineering are complementary disciplines.

Corpus engineering improves the semantic ecosystem.

Benchmarking measures the effects of those improvements.

Neither discipline is sufficient in isolation.

Together they provide a rigorous methodology for engineering institutional retrieval systems.

---

# Guiding Principle

The objective is not to maximize benchmark scores.

The objective is to build an explainable retrieval system whose improvements can be demonstrated through reproducible experiments.
