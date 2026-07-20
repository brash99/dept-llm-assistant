# Institutional Semantic Observatory (ISO)

> **Status:** Evidence Layer design note. Listed observer types include implemented, planned, and aspirational examples; see [Current Status](../status.md).

## Distributed Institutional Observation

**Version 0.1**

---

# Introduction

Every scientific observatory begins with observation.

Astronomical observatories observe the sky.

Weather observatories observe the atmosphere.

Particle physics experiments observe collisions.

Likewise, the Institutional Semantic Observatory begins by observing institutions.

Rather than assuming institutional knowledge already exists in a single repository, ISO recognizes that institutional knowledge is inherently distributed across many independent systems.

Distributed Institutional Observation provides a unified architectural framework for acquiring those observations while preserving their provenance.

---

# Institutions Are Distributed Systems

Modern institutions generate information through many independent processes.

Examples include:

- shared file systems
- Google Drive
- institutional websites
- databases
- enterprise applications
- accreditation repositories
- learning management systems
- student information systems
- finance systems
- APIs
- public datasets

Each system captures a different aspect of institutional reality.

No single repository contains the complete institutional memory.

Observation therefore becomes a distributed activity.

---

# Observers

An observer is an autonomous component responsible for acquiring observations from a single governed source.

Examples include:

- Filesystem Observer
- Google Drive Observer
- Website Observer
- Database Observer
- Banner Observer
- Canvas Observer
- Workday Observer
- API Observer

Each observer understands only one source.

Observers do not interpret information.

They simply observe.

---

# Responsibilities of an Observer

Every observer performs the same fundamental tasks.

It must:

- discover observations
- determine whether observations have changed
- preserve provenance
- assign authority
- record acquisition metadata
- detect duplicate content
- produce canonical SourceDocuments

An observer never reasons about institutional meaning.

Interpretation occurs later within the observatory.

---

# SourceDocuments

Every observation produces a SourceDocument.

A SourceDocument represents an observation of institutional reality at a particular moment in time.

It records:

- content
- provenance
- acquisition method
- acquisition timestamp
- authority
- source organization
- source URL or source path
- content hash

A SourceDocument is therefore an observation rather than merely a document.

---

# Observations Through Time

Institutions evolve continuously.

Policies change.

Budgets change.

Catalogs change.

Faculty change.

Enrollment changes.

Webpages change.

Consequently, institutional observations are inherently temporal.

Each SourceDocument represents what was true when the observation occurred.

ISO intentionally preserves this temporal perspective rather than overwriting previous observations.

Institutional memory therefore becomes a historical record rather than a snapshot.

---

# Provenance

Every observation retains complete provenance.

Examples include:

Filesystem observations:

- source path
- relative path

Website observations:

- URL
- acquisition time
- crawl depth

Database observations:

- table
- primary key
- transaction timestamp

API observations:

- endpoint
- query parameters
- response metadata

Provenance is preserved throughout the lifetime of the observation.

---

# Authority

Not every observation has equal authority.

ISO explicitly records authority rather than assuming all observations are equivalent.

Examples include:

- institutional_primary
- institutional_secondary
- departmental
- external_standard
- public_reference

Authority influences later reasoning but never alters the original observation.

---

# Distributed Observation Network

An institution may have dozens or hundreds of observers.

Conceptually:

                    Institutional Semantic Observatory

                                  │

        ┌───────────────┬───────────────┬───────────────┐
        │               │               │               │

 Filesystem      Google Drive      Website        Databases

        │               │               │               │

        └───────────────┴───────────────┴───────────────┘

                           Institutional Memory

Each observer contributes observations independently.

Institutional Memory unifies them.

---

# Continuous Observation

Observation is not a one-time activity.

Observers may execute:

- hourly
- daily
- weekly
- continuously
- event driven

Each execution contributes additional observations to institutional memory.

The observatory therefore evolves with the institution.

---

# Why Observation Matters

Most retrieval systems begin after documents already exist.

ISO begins much earlier.

It explicitly models the process by which institutional knowledge is acquired.

This distinction enables:

- provenance preservation
- temporal analysis
- authority tracking
- duplicate detection
- observation scheduling
- future observation planning

Observation becomes a first-class architectural concept.

---

# Future Directions

Distributed Institutional Observation naturally supports future capabilities.

Examples include:

- automated observation scheduling
- observation prioritization
- anomaly detection
- change detection
- institutional monitoring
- semantic drift analysis
- observation forecasting

These capabilities emerge naturally because observation is explicitly represented within the architecture.

---

# Closing Statement

Distributed Institutional Observation recognizes a simple truth:

**Institutions are observed, not downloaded.**

By modeling observation as an explicit architectural layer, ISO transforms institutional knowledge acquisition from a collection of import scripts into a governed, explainable, and continuously evolving scientific process.
