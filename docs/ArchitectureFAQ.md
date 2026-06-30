
# Architecture FAQ (Addendum)

## Why build a benchmark framework?

Because retrieval quality should be measured rather than judged anecdotally.

The benchmark framework enables repeatable experiments across retrieval
algorithms and architectural changes.

**Design Principle**

> Engineering decisions should be benchmark-driven.

---

## Why expose retrieval diagnostics?

Every stage of retrieval is inspectable:

- raw vector candidates
- deduplicated candidates
- reranked candidates
- final LLM context

This makes retrieval failures explainable rather than mysterious.

**Design Principle**

> Make every transformation observable.

---

## Why categorize benchmark questions?

Different document types behave differently.

Policies, spreadsheets, course catalogs, PowerPoint presentations, and
historical documents each present distinct retrieval challenges.

Category summaries reveal where architectural improvements are helping—or hurting.

**Design Principle**

> Measure performance by document class, not only overall accuracy.

---

## Why treat the Department Knowledge Assistant as a research platform?

Because the long-term goal is larger than departmental question answering.

The assistant provides a controlled environment in which retrieval techniques,
evaluation methodologies, and architectural ideas can be developed before being
applied to institution-scale problems such as strategic planning, enrollment
forecasting, and administrative decision support.

**Design Principle**

> The application validates the framework; the framework outlives the application.
