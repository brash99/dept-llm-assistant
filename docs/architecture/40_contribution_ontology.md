# Institutional Ontology and Explainable Reasoning

> **Design Manifesto**
>
> This document records one of the foundational architectural decisions of the
> Institutional Semantic Observatory (ISO). It describes the philosophical
> distinction between institutional ontology and institutional reasoning and
> explains why ISO separates institutional facts, institutional values,
> institutional contribution, reasoning, and decision-making.
>
> This distinction governs the architecture of the entire system.

---

# Background

This document captures one of the central architectural insights behind the
Institutional Semantic Observatory (ISO).

The discussion began while considering how ISO should answer the Provost's
strategic workforce question:

> If Christopher Newport University must reduce the number of full-time faculty,
> which departments should lose positions?

Initially this appeared to be a problem of metrics, reports, and AI reasoning.

It is not.

It is fundamentally a problem of institutional ontology.

---

# Reports are not the model

One of the guiding principles of ISO is:

> **ISO models the institution. Reports are simply views of that model.**

The purpose of ISO is therefore not to reproduce administrative reports.

Its purpose is to construct a faithful computational representation of the
institution itself.

Reports are products of the model.

They are not the model.

---

# The Semantic Layer models institutional reality

The Semantic Layer exists to model the institutional reality of Christopher
Newport University.

It is entirely ontological in nature.

Its purpose is to answer the question:

> **What is true about the institution?**

This includes several different kinds of institutional facts.

## Descriptive Knowledge Objects

These describe institutional entities.

Examples include

- Departments
- Faculty
- Courses
- Sections
- Programs
- Majors
- Colleges

These answer questions such as

> What exists?

---

## Constitutional Knowledge Objects

These describe the institution's formally adopted mission, values, priorities,
and governing commitments.

They answer questions such as

> What does Christopher Newport University formally value?

These are not opinions.

They are institutional facts.

An individual evaluator may personally disagree with those priorities.

That disagreement is outside the scope of ISO.

ISO models Christopher Newport University as it exists, not as individuals
believe it ought to exist.

---

## Contribution Knowledge Objects

Contribution is itself an ontological property.

Making a contribution is a fact.

Examples include

- Physics provides Natural World LLC instruction.
- Philosophy teaches ethics supporting Business and Pre-Law.
- Religion contributes Arts of Interpretation instruction.
- Engineering supports ABET accreditation.
- Leadership supports the institutional mission through leadership education.

These statements describe real properties of the institution.

They are not recommendations.

They are not evaluations.

They are institutional facts.

Contribution Knowledge Objects therefore become first-class semantic objects.

Examples include

- DepartmentContributionKnowledgeObject
- FacultyContributionKnowledgeObject
- ProgramContributionKnowledgeObject
- CollegeContributionKnowledgeObject

These are deterministic, evidence-backed representations of institutional
contribution.

They are computed from evidence, but computation does not make them any less
ontological.

Computation is a matter of epistemology—how we discover institutional facts.

Ontology concerns what is true about the institution.

---

# Departments are collections of contribution profiles

Departments are not homogeneous entities.

They frequently contain multiple distinct contribution profiles.

For example, within the School of Engineering and Computing:

- physicists,
- computer scientists,
- and engineers

contribute to the university in substantially different ways.

Likewise, Philosophy & Religion contains distinct contribution profiles.

For example,

- Philosophy contributes logical reasoning, ethics, Business support,
  Pre-Law support, and AI ethics.

- Religion contributes Arts of Interpretation, religious studies,
  cultural understanding, and humanities education.

Reducing one philosopher and reducing one religion faculty member remove
different institutional capabilities.

ISO therefore models institutional contribution rather than merely counting
faculty positions.

---

# Ontology versus reasoning

ISO deliberately separates

- institutional facts,
- institutional values,
- reasoning,
- and decisions.

This distinction is fundamental.

Making a contribution is a fact.

Whether that contribution should be valued more highly than another
for a particular decision is a separate question.

The Semantic Layer therefore never performs evaluation.

It only models institutional reality.

---

# The Purpose of the Reasoning Layer

The purpose of the Reasoning Layer is **not** to invent conclusions.

Its purpose is to make explicit the conclusions that follow from accepted
institutional facts.

The Reasoning Layer operates on

- Descriptive Knowledge Objects,
- Constitutional Knowledge Objects,
- Contribution Knowledge Objects,

and produces transparent, explainable arguments about institutional decisions.

Reasoning never alters institutional reality.

It reasons over institutional reality.

---

# Explainable institutional reasoning

The ultimate goal of ISO is not simply to produce recommendations.

Its goal is to produce reasoning that is transparent, reproducible,
and explainable.

ISO therefore aspires to a stronger standard:

> **Any reasonable evaluator who accepts the same institutional facts,
> the same constitutional commitments,
> and the same decision context,
> should arrive at substantially the same conclusion.**

The objective is not to replace human judgment.

The objective is to make institutional reasoning sufficiently explicit that
reasonable decision makers can understand, reproduce, critique, and improve
the argument.

The LLM is therefore **not** the source of institutional knowledge.

Institutional knowledge already exists within the Semantic Layer.

The LLM serves as the reasoning engine that makes the implications of that
knowledge explicit.

Reasoning should never appear as "AI magic."

It should instead resemble a carefully constructed argument whose premises,
logic, and conclusions are all open to inspection.

---

# ISO is a decision-support system, not a decision-making system

ISO does not exist to make institutional decisions.

ISO exists to make institutional decisions explainable.

The system does not determine what Christopher Newport University ought to do.

Instead, it makes explicit the reasoning that follows from

- accepted institutional facts,
- accepted constitutional commitments,
- and a specified decision context.

Decision makers remain responsible for the decision.

ISO makes the reasoning transparent.

---

# Fundamental Design Principle

Knowledge Objects store institutional facts.

Services derive institutional meaning.

The Reasoning Layer makes that meaning explicit through transparent,
reproducible argument.

---

# Guiding Question

Every Contribution Knowledge Object ultimately exists to answer one question:

> **How does this entity contribute to the mission and values of
> Christopher Newport University?**

This question is the organizing principle for reports, reasoning,
scenario modeling, and ultimately the Institutional Digital Twin.
