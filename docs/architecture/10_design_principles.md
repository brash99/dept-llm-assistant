# Institutional Semantic Observatory (ISO)

> **Status:** Enduring design principles. The permanent architecture and current capability boundaries are defined in [Architecture Overview](01_architecture_overview.md) and [Current Status](../status.md).

## Design Principles

**Version 0.1**

---

# Introduction

The Institutional Semantic Observatory is expected to evolve continuously.

Its software, models, retrieval methods, and interfaces will change.

The principles in this chapter define the architectural commitments that should remain stable as implementations evolve.

---

# Principle 1: Knowledge Objects Preserve Observations; Services Derive Meaning

Knowledge Objects preserve observations about the institution.

Services interpret those observations.

A university catalog may establish that a major exists.

Whether that major is healthy, growing, financially sustainable, or strategically important is an interpretation derived from additional evidence and institutional values.

ISO therefore separates facts from meaning.

It should always be possible to identify:

- which observations were used
- which observations were treated as relevant
- how those observations were interpreted
- which assumptions shaped the interpretation
- how the interpretation contributed to a recommendation

Meaning is derived rather than silently stored as fact.

---

# Principle 2: Observation Precedes Reasoning

Reliable reasoning begins with reliable observation.

ISO should not construct conclusions from information that cannot be traced to an institutional or external observation.

Every evidence-backed conclusion should ultimately be connected to observable sources.

---

# Principle 3: Observations Are Temporal

Institutional observations occur at particular moments in time.

A catalog, policy, enrollment report, budget, or webpage describes an institutional state associated with a specific period.

A newer observation does not make an older observation false.

The two observations may represent different institutional states.

ISO must therefore preserve the temporal character of institutional knowledge.

---

# Principle 4: Provenance Is Never Discarded

Every observation must retain its origin.

ISO should always be able to explain:

- where an observation came from
- when it was acquired
- how it was acquired
- who published it
- what authority it carries

Provenance is a permanent property of Institutional Memory.

---

# Principle 5: Institutional Memory Is Append-Only

New observations extend Institutional Memory.

They do not rewrite institutional history.

Corrections, revisions, and replacements should be represented as new observations with appropriate relationships to earlier observations.

This enables historical reconstruction and temporal reasoning.

---

# Principle 6: Canonical Observations and Derived Representations Are Distinct

Original observations are canonical.

Chunks, embeddings, indexes, summaries, classifications, semantic labels, and evidence scores are derived representations.

Derived representations may be regenerated or replaced.

Canonical observations remain preserved.

---

# Principle 7: Retrieval Gathers Evidence; It Does Not Reason

Retrieval identifies observations that may be relevant to a question.

It does not determine what those observations mean.

This separation allows retrieval to remain inspectable, testable, and independent of final interpretation.

---

# Principle 8: Evidence Is Assessed Before Explanation

Before ISO produces an explanation, it should assess the retrieved evidence.

The system should evaluate:

- institutional authority
- evidence balance
- topic coverage
- external dependence
- uncertainty
- missing information
- decision readiness

ISO should not confuse the ability to generate an answer with the possession of adequate evidence.

---

# Principle 9: Institutions Should Be Observable

Institutional information should not remain trapped in disconnected repositories.

Governed observers should allow ISO to examine multiple institutional systems while preserving source boundaries, authorization, and provenance.

Distributed observation produces unified Institutional Memory.

---

# Principle 10: The Health of Institutional Memory Is Observable

Institutional Memory is itself a semantic ecosystem.

Its coverage, diversity, dominance, duplication, fragmentation, and temporal completeness can be measured.

ISO should assess the health of this ecosystem before relying upon it for institutional reasoning.

---

# Principle 11: Interpretations and Values Must Remain Visible

Institutional disagreements often concern:

1. which facts should matter
2. how those facts should be interpreted
3. which institutional values should guide action

ISO should make these distinctions visible.

Values-based decisions are legitimate, but values should not be presented as observations.

Interpretive assumptions should remain open to inspection and challenge.

---

# Principle 12: AI Illuminates Rather Than Decides

ISO supports human judgment.

It does not replace institutional responsibility.

The system may identify evidence, explain uncertainty, compare interpretations, and illuminate consequences.

Final authority remains with human decision-makers.

---

# Principle 13: Explainability Is a Governance Requirement

Explainability is not merely a user-interface feature.

It is necessary for institutional trust and accountability.

ISO should always be able to explain which observations support an interpretation and which interpretations support a recommendation.

---

# Principle 14: Framework Before Application

ISO is a general institutional knowledge architecture.

New applications should consume the common observation, memory, evidence, and reasoning services rather than constructing isolated information pipelines.

The framework should expand without requiring fundamental redesign for each new institutional question.

---

# Closing Statement

These principles are intended to remain stable even as ISO implementations evolve.

**Observe carefully. Preserve faithfully. Interpret transparently. Illuminate responsibly.**
