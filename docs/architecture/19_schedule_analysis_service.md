# Deterministic Schedule Analysis

> Retrieval identifies which facts matter.
>
> Analytical services determine what the full body of facts implies.

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

The service does not use embeddings, FAISS, a reranker, or an LLM. It supports
distinct-instructor and course-offering counts plus resolved, adjunct,
full-time, and unresolved offering shares. Results can be grouped by academic
term, normalized Instructor Type, subject, or a governed academic workforce
unit. Those metrics remain distinct: one person teaching five sections
contributes one distinct instructor and five offerings.

Adjunct and Full Time shares use only observations resolved to one of those two
section-scoped source categories. Unresolved conflicts, unknown types, and
missing instructors are excluded from that denominator and reported
separately. Resolved and unresolved shares use all included offerings as their
denominator. Every result records its numerator, denominator, and definition.

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

The normal `scripts/ask_rag.py` entry point now performs this routing before it
imports or invokes retrieval. Supported analytical requests produce labeled
deterministic output. Unsupported analytical requests do not silently fall
back to a misleading top-k answer. Selective section lookups retain the
existing RAG path.

Constitutional evidence is eligible only when the question contains explicit
normative or constitutional language. Descriptive schedule lookups and
aggregations receive a zero constitutional quota at the RAG and Decision Brief
entry points.

`HybridReasoningResult` represents the minimum bridge for a question needing
both computed facts and selected context. It keeps the analytical result,
optional retrieved-evidence request, constitutional requirement, response
sections, and unresolved limitations separate. The LLM may later explain the
result but must not recompute its numbers.

## Governed academic-unit mapping

`AcademicUnitMappingService` resolves subject codes only through reviewed rules
in `config/institutional_units.yaml`. Results explicitly distinguish mapped,
intentionally grouped, ambiguous, unmapped, and unsupported subjects. Each
mapped result identifies its registry rule, source, confidence, formal unit
type, and operational roles.

The initial production rules are deliberately narrow. PHYS, CPSC, CYBR, IS,
CPEN, and EENG roll up to the School of Engineering and Computing because the
governed registry identifies SEC as their department-equivalent faculty-home
and workforce-allocation unit. SEC remains formally a dependent school; the
mapping does not create Physics, Computer Science, Engineering, or
Cybersecurity departments. Other subjects remain unmapped until a reviewed
crosswalk is added.

## Trend analysis and Evidence Fitness

Terms are ordered by the normalized institutional sequence: Spring, May,
Summer 1, Extended Summer, Summer 2, and Fall. Malformed or unsupported terms
remain visible and are excluded from endpoint comparisons. Trend results state
endpoint values, absolute change, percentage-point change for shares, missing
terms, zero-denominator conditions, observation counts, and comparability
limits. They do not forecast or claim causation.

Schedule Evidence Fitness reports subject, mapping, instructor-identity,
Instructor Type, conflict, missing-value, and term coverage. It marks the
corpus suitable for descriptive section patterns and conditionally suitable
for comparisons and trends. It explicitly marks official employment history,
workload/FTE inference, and staffing recommendations insufficient.

## Result contract and provenance

`ScheduleAggregationResult` records the request, metric, grouping, totals,
grouped values, uncertainty, source/included/excluded object counts,
provenance, and a deterministic SHA-256 fingerprint. Source paths presented in
new chunks and analytical results are repository-relative when the evidence is
inside the repository, so artifacts do not expose Mac or A100 absolute paths.

Run locally or on the A100 after pulling the reviewed commit:

```bash
PYTHONPATH="$PWD" python3 scripts/analyze_schedule.py \
  "Count offerings by subject and term" \
  --metric course_offerings --group-by subject academic_term

PYTHONPATH="$PWD" python3 scripts/analyze_schedule.py \
  "Show adjunct dependence trends by subject" \
  --metric adjunct_offering_share --group-by subject academic_term \
  --trend --json
```

## Boundary

This implementation advances the Semantic Layer's governed unit mapping, the
Reasoning Layer's deterministic calculations, and Evidence Fitness reporting.
It prepares transparent inputs for Scenario Modeling but does not implement
that layer. It does not assign faculty to majors, compute workload or student
credit hours, establish employment history, or recommend staffing actions.
Those boundaries preserve the permanent architecture:

1. Evidence Layer
2. Semantic Layer
3. Reasoning Layer
4. Evidence Fitness
5. Scenario Modeling
6. Institutional Digital Twin
