# Constitutional Reasoning

## Motivation

Institutions do not make decisions from facts alone.

They make decisions by interpreting empirical evidence through the lens of institutional values.

Traditional retrieval systems retrieve documents.

ISO retrieves two distinct forms of institutional knowledge:

- empirical observations
- institutional values

These are intentionally preserved as separate semantic spaces.

---

# Two Semantic Spaces

## Empirical Space

Empirical Knowledge Objects describe the institution as it currently exists.

Examples include:

- enrollment
- budgets
- faculty
- facilities
- curricula
- assessment
- accreditation evidence
- research output

These objects answer the question:

> What is true?

---

## Constitutional Space

Constitutional Knowledge Objects describe the institution's declared values and long-term objectives.

Examples include:

- Mission Statement
- Vision Statement
- Strategic Compass
- Strategic Plan
- Academic Master Plan
- Board Priorities
- Institutional Learning Outcomes

These objects answer the question:

> What does the institution value?

---

# Prime Directive

ISO shall never substitute its own values for those of the institution it is observing.

ISO faithfully preserves:

- empirical observations
- institutional values

Decision Services derive meaning transparently from both.

Human decision-makers remain responsible for institutional decisions.

---

# Architectural Principle

Knowledge Objects store facts.

Constitutional Knowledge Objects store values.

Decision Services derive meaning by reasoning over both.

---

# Architectural Model

                    Decision Services
                  (derive meaning)
                         ▲
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼
 Knowledge Objects      Constitutional Knowledge Objects
      (facts)                      (values)

---

# Future Implementation

The Constitutional Reasoning extension will introduce:

- ConstitutionalKnowledgeObject
- Constitutional Observer
- Constitutional Retrieval
- Constitutional Alignment sections within Decision Briefs
- Dual-orientation Semantic Control Plane

No existing Knowledge Object behavior changes.

This is an architectural extension, not a redesign.
