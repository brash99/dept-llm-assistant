# Decision Briefs

> The primary output of the Institutional Knowledge Framework.

---

# Introduction

Traditional Retrieval-Augmented Generation (RAG) systems answer questions.

The Institutional Knowledge Framework is evolving toward a different objective.

Rather than generating isolated answers, the framework will produce **Decision Briefs** that synthesize institutional evidence relevant to a strategic question.

A Decision Brief is intended to support—not replace—human decision making.

It organizes evidence, identifies uncertainty, highlights missing information, and provides a transparent foundation upon which institutional leaders can exercise their own judgment.

---

# Motivation

Many important institutional questions cannot be answered by a single document.

For example,

- Should a retiring faculty member be replaced?
- Should a new academic program be introduced?
- How would a proposed curriculum change affect other departments?
- What facilities are required for a new laboratory?
- Which strategic initiatives are best aligned with institutional priorities?

Answering these questions requires integrating evidence from numerous sources.

The objective is therefore not information retrieval.

The objective is evidence synthesis.

---

# Design Principles

Every Decision Brief should satisfy five fundamental principles.

## Evidence-Based

Every statement should be supported by retrieved institutional evidence whenever possible.

---

## Explainable

Every conclusion should be traceable to one or more supporting documents.

---

## Transparent

The system should distinguish clearly between:

- retrieved evidence
- synthesized observations
- inferred conclusions
- recommendations

---

## Honest About Uncertainty

Missing information should be identified explicitly rather than hidden.

The system should acknowledge when evidence is incomplete or conflicting.

---

## Human-Centered

Decision Briefs support institutional leaders.

They do not make decisions on their behalf.

---

# Proposed Structure

Each Decision Brief should contain the following sections.

---

## Executive Summary

A concise overview of the question being considered together with the principal findings.

This section should be understandable without reading the remainder of the report.

---

## Institutional Question

The question posed by the user.

Examples include:

- What resources would be required to launch a Mechanical Engineering major?

- Should Department X replace a retiring faculty member?

---

## Evidence Summary

A synthesis of the information retrieved from the institutional knowledge base.

Rather than listing documents individually, this section organizes evidence into coherent themes.

---

## Supporting Evidence

Evidence grouped by topic.

Typical categories might include:

- curriculum
- faculty expertise
- accreditation
- facilities
- laboratory equipment
- staffing
- strategic planning
- historical precedent
- budget
- enrollment

Each section should include citations to supporting documents.

---

## Areas of Agreement

Institutional evidence frequently converges.

This section summarizes conclusions that are consistently supported across multiple sources.

---

## Areas of Uncertainty

Institutional evidence is rarely complete.

This section identifies:

- conflicting information
- ambiguous documents
- outdated policies
- missing records

Understanding uncertainty is often as valuable as understanding certainty.

---

## Missing Information

Some questions cannot be answered from the available corpus.

Examples include:

- unavailable budget information
- missing facilities inventories
- absent accreditation documents
- incomplete historical records

Rather than speculating, the framework should identify what additional information would improve the analysis.

---

## Strategic Considerations

Institutional decisions frequently involve considerations extending beyond factual evidence.

Examples include:

- alignment with institutional mission
- long-term sustainability
- interdisciplinary opportunities
- strategic priorities
- potential risks

These observations should be presented as considerations rather than recommendations.

---

## Possible Scenarios

Where appropriate, the framework should summarize multiple plausible outcomes.

For example:

- replacing a faculty member
- delaying replacement
- creating a new position
- restructuring responsibilities

The objective is to support scenario analysis rather than prescribe a single course of action.

---

## Recommended Follow-Up

Decision Briefs should conclude by suggesting additional investigations that would improve confidence.

Examples include:

- collecting missing data
- consulting specific committees
- obtaining updated enrollment projections
- reviewing accreditation requirements
- conducting financial analysis

---

## Sources

Every Decision Brief concludes with complete citations to all supporting documents.

Transparency is essential.

---

# Future Enhancements

Future versions of Decision Briefs may incorporate:

- probabilistic forecasting
- scenario simulation
- confidence estimates
- interactive evidence exploration
- semantic relationship graphs
- quantitative decision metrics

These capabilities will build upon the same explainable evidence foundation.

---

# Relationship to Question Answering

Question answering remains an important capability.

However, it becomes only one component of a larger reasoning process.

```
Institutional Question
           │
           ▼
Evidence Retrieval
           │
           ▼
Evidence Clustering
           │
           ▼
Evidence Synthesis
           │
           ▼
Decision Brief
           │
           ▼
Human Judgment
```

Question answering retrieves information.

Decision Briefs organize institutional knowledge.

---

# Guiding Principle

The objective is not to tell university leaders what decision to make.

The objective is to ensure that every important decision begins with the best available institutional evidence.
