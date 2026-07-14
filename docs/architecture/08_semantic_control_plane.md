# Institutional Semantic Observatory (ISO)

## Semantic Control Plane

**Version 0.1**

---

# Introduction

Before institutional evidence can be retrieved, ISO must first determine what the institution believes a question is about.

This responsibility belongs to the Semantic Control Plane.

Rather than immediately searching Institutional Memory, the Control Plane first establishes institutional orientation.

This separates institutional interpretation from evidence retrieval.

---

# Why a Control Plane?

Traditional retrieval systems immediately perform semantic search.

ISO introduces an intermediate step.

Before searching, the observatory asks:

"What institutional entities does this question refer to?"

This interpretation guides retrieval while remaining completely explainable.

---

# Institutional Orientation

Every institutional question produces an Institutional Orientation.

The orientation summarizes:

- recognized institutional entities
- proposed entities
- semantic neighbors
- organizational context
- interpretation confidence
- orientation notes

Institutional Orientation is an interpretation contract.

It does not answer the question.

---

# Existing Institutional Entities

The Control Plane first determines whether the question refers to existing institutional entities.

Examples include:

- departments
- degree programs
- colleges
- administrative units
- committees
- strategic initiatives

These entities are resolved using institutional catalogs rather than semantic similarity alone.

Institutional facts take precedence over statistical inference.

---

# Proposed Institutional Concepts

Not every question concerns an existing entity.

For example:

"What would a Data Science major require?"

The institution may not currently offer such a major.

Rather than incorrectly resolving this question to Computer Science, the Control Plane represents Data Science as a proposed institutional concept.

This distinction prevents the observatory from confusing hypothetical entities with existing institutional reality.

---

# Semantic Neighborhoods

After identifying institutional entities, the Control Plane constructs a semantic neighborhood.

This neighborhood identifies related institutional concepts.

For example:

Computer Science

may produce neighbors including:

- Cybersecurity
- Information Science
- Software Engineering
- Mathematics

These neighborhoods provide institutional context before retrieval begins.

---

# Institutional Rather Than Linguistic Meaning

Traditional semantic search relies primarily on linguistic similarity.

The Control Plane emphasizes institutional meaning.

For example:

"Physics"

may refer to:

- a department
- a major
- a course
- a research group
- an accreditation unit

Institutional Orientation resolves these possibilities before evidence retrieval.

---

# Confidence

Every orientation includes an explicit confidence estimate.

Confidence reflects the observatory's certainty that it has interpreted the institutional meaning correctly.

Low-confidence orientations remain visible to users.

ISO prefers uncertainty to false certainty.

---

# Explainability

Every component of Institutional Orientation is inspectable.

Users can observe:

- matched entities
- proposed concepts
- semantic neighbors
- confidence
- explanatory notes

Interpretation therefore becomes transparent rather than hidden inside an embedding model.

---

# Relationship to Retrieval

The Control Plane does not retrieve evidence.

Instead, it prepares retrieval.

Its output becomes the institutional context within which retrieval occurs.

Retrieval therefore becomes institution-aware rather than purely semantic.

---

# Relationship to Institutional Memory

The Control Plane never modifies Institutional Memory.

It consumes institutional facts.

Interpretation remains entirely separate from institutional observations.

This preserves the architectural principle:

Knowledge Objects store facts.

Services derive meaning.

---

# Looking Ahead

Future Control Plane capabilities may include:

- organizational ontologies
- policy relationships
- governance structures
- prerequisite graphs
- budget hierarchies
- curriculum dependency networks
- organizational simulations

These additions expand institutional understanding without changing Institutional Memory.

---

# Beyond Conventional RAG

The Semantic Control Plane represents one of the principal architectural differences between ISO and conventional Retrieval-Augmented Generation.

Rather than immediately searching for semantically similar text, ISO first establishes institutional context.

This additional layer enables retrieval to reflect organizational structure rather than language alone.

---

# Closing Statement

The Semantic Control Plane is founded upon a simple idea:

**Institutions possess structure that should influence retrieval.**

By interpreting institutional meaning before evidence retrieval begins, ISO separates organizational understanding from semantic similarity and produces a more explainable foundation for institutional reasoning.

