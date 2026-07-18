# Institutional Semantic Observatory (ISO) Changelog

This document records significant architectural and implementation milestones in the development of the Institutional Semantic Observatory. The emphasis is on major capabilities, design decisions, and observatory functionality rather than individual code changes.

---

# August 2026 — Integrated Observatory Milestone

## Overview

This milestone marks the transition of the Institutional Semantic Observatory from a collection of experimental components into an integrated institutional decision-support platform.

The system now performs a complete, explainable workflow:

Question
→ Institutional Orientation
→ Constitutional Orientation
→ Evidence Retrieval
→ Evidence Landscape
→ Evidence Fitness
→ Decision Brief

This represents the first end-to-end implementation of the observatory architecture.

---

## Major Capabilities

### Institutional Orientation

Implemented the Semantic Control Plane that interprets institutional questions before evidence retrieval.

Features include:

- recognition of existing institutional entities
- identification of proposed institutional concepts
- semantic program neighborhood generation
- institutional orientation confidence scoring

Academic program proposal extraction was substantially improved by moving from simple surface-pattern matching toward semantic extraction.

The extractor now correctly recognizes proposal language including:

- program
- major

while avoiding false extraction of surrounding sentence structure (e.g. institution names and proposal verbs).

---

### Constitutional Orientation

Implemented constitutional orientation using Constitutional Knowledge Objects.

The observatory now identifies institutional values that may be relevant to a question before evidence retrieval.

This layer intentionally provides orientation rather than normative judgment.

---

### Evidence Landscape

Introduced deterministic characterization of the retrieved evidence set.

Current metrics include:

- retrieved evidence count
- evidence class composition
- dominant evidence class
- empirical diversity

This layer describes the evidence itself without evaluating its adequacy.

---

### Evidence Fitness

Implemented deterministic question-aware assessment of evidence quality.

Current evaluation dimensions include:

- domain coverage
- authority fit
- evidence-role fit

The system now identifies:

- strong evidence domains
- partially supported domains
- weak domains
- missing evidence

Evidence Fitness calculations were normalized to eliminate inconsistent scoring and ensure percentages remain internally consistent.

---

### Knowledge Ecosystem Observatory

Integrated deterministic ecosystem metrics into the dashboard.

Current metrics include:

- retrieved evidence objects
- covered evidence domains
- identified evidence gaps

Dashboard values are now produced directly from connected services rather than inferred by the renderer.

---

### Decision Classification

Improved semantic decision classification.

Institutional questions such as:

    Should CNU start a Mechanical Engineering major?

are now correctly classified as:

    Academic Program Decision

with high confidence.

---

### Decision Brief

Expanded the decision brief into a structured executive product containing:

- executive summary
- evidence summary
- supporting evidence by domain
- areas of agreement
- areas of uncertainty
- missing information
- strategic considerations
- recommended follow-up
- topology assessment
- evidence provenance

---

## Architectural Principles Reinforced

This milestone further establishes several long-term architectural principles.

### Knowledge Objects store facts.

Services derive meaning.

Knowledge Objects remain immutable factual representations.

Interpretation is performed by deterministic services rather than embedded within stored objects.

---

### Orientation precedes evidence.

Questions are first interpreted institutionally and constitutionally before evidence retrieval begins.

This provides semantic context for the remainder of the observatory pipeline.

---

### Deterministic services should explain themselves.

Each major service now exposes its reasoning in a way that is suitable for dashboard visualization and executive reporting.

---

### Missing evidence is itself evidence.

The observatory explicitly reports absent evidence domains rather than silently proceeding with incomplete information.

---

## Current Observatory Workflow

Institutional Question

↓

Institutional Orientation

↓

Constitutional Orientation

↓

Evidence Retrieval

↓

Evidence Landscape

↓

Evidence Fitness

↓

Decision Brief

---

## Status

This milestone establishes the first integrated version of the Institutional Semantic Observatory suitable for executive demonstration and continued development toward the broader institutional digital twin architecture.

