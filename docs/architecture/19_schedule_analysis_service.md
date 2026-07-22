# Deterministic Schedule Analysis

## Purpose

Vector retrieval finds a small set of relevant evidence. It cannot establish an
exact aggregate over the entire schedule corpus. `ScheduleAnalysisService` is
the first ISO Reasoning Layer service that computes directly from normalized
Knowledge Objects:

```text
normalized schedule Knowledge Objects
                 ↓
deterministic full-corpus computation
                 ↓
provenance-bearing ScheduleAggregationResult
                 ↓
explanation by a later consumer
```

The service does not use embeddings, FAISS, a reranker, or an LLM. It currently
supports distinct-instructor and course-offering counts grouped by academic
term and normalized Instructor Type. Those metrics remain distinct: one person
teaching five sections contributes one distinct instructor and five offerings.

## Uncertainty

The service consumes the schedule repair assertion without converting it into
a timeless faculty fact. It reports Full Time, Adjunct, Unresolved Conflict,
Missing Instructor, and Unknown Instructor Type separately. A resolved source
conflict remains counted in the uncertainty summary as a repaired assertion.

## Query routing

`ReasoningRouter` deterministically distinguishes selective retrieval,
structured aggregation, comparison, trend analysis, scenario modeling, and
unsupported requests. Schedule aggregation, comparison, and trend requests
route to the schedule analysis service. Bounded factual lookups still route to
retrieval. Scenario requests are identified but are not executed by this
service.

Constitutional evidence is eligible only when the question contains explicit
normative or constitutional language. Descriptive schedule lookups and
aggregations receive a zero constitutional quota at the RAG and Decision Brief
entry points.

## Result contract and provenance

`ScheduleAggregationResult` records the request, metric, grouping, totals,
grouped values, uncertainty, source/included/excluded object counts,
provenance, and a deterministic SHA-256 fingerprint. Source paths presented in
new chunks and analytical results are repository-relative when the evidence is
inside the repository, so artifacts do not expose Mac or A100 absolute paths.

Run locally or on the A100 after pulling the reviewed commit:

```bash
PYTHONPATH="$PWD" python3 scripts/analyze_schedule.py \
  "How many adjunct instructors taught each term?"

PYTHONPATH="$PWD" python3 scripts/analyze_schedule.py \
  "How many course offerings were taught each term?" \
  --metric course_offerings --json
```

## Boundary

This implementation does not assign instructors to departments, compute
workload or student credit hours, resolve identities beyond formatting for a
single aggregate, or recommend staffing actions. Comparisons and trends can be
routed to this service, but richer derived measures and Scenario Modeling need
separate governed implementations.
