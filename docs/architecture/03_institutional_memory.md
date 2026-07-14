# Institutional Semantic Observatory (ISO)

## Institutional Memory

**Version 0.1**

---

# Introduction

Observation alone is insufficient.

Observations must be preserved.

The purpose of Institutional Memory is to provide a permanent, provenance-preserving record of everything the observatory has ever observed.

Institutional Memory is therefore the foundation upon which every higher-level capability within ISO is built.

---

# Beyond Document Collections

Traditional document repositories answer a simple question:

> Where is the document?

Institutional Memory answers a different question:

> What has the institution observed?

This distinction is fundamental.

Institutional Memory is not organized around files.

It is organized around observations.

---

# SourceDocuments

Every observation becomes a SourceDocument.

A SourceDocument is the canonical representation of an institutional observation.

It records:

- observed content
- provenance
- acquisition method
- authority
- acquisition timestamp
- publication timestamp (when known)
- content hash
- source organization

A SourceDocument is immutable.

It represents exactly what the observatory observed.

---

# An Observation

A SourceDocument should not be thought of merely as a document.

It is an observation made at a particular moment in time.

For example:

A university catalog published in 2022 is an observation of the institution as it existed in 2022.

A revised catalog published in 2025 is a different observation.

Neither observation is "more correct."

Each accurately represents institutional reality at the time it was published.

Institutional Memory preserves both.

---

# Time Matters

Institutions evolve.

Programs are created.

Departments merge.

Policies change.

Budgets grow.

Websites are revised.

Enrollment rises and falls.

Consequently, institutional memory must preserve history rather than overwrite it.

ISO treats time as a first-class property of institutional knowledge.

---

# Immutable Observations

SourceDocuments are intentionally immutable.

Later processing may derive:

- chunks
- embeddings
- summaries
- classifications
- semantic labels

None of these modify the original observation.

The canonical observation remains unchanged.

Derived products can always be regenerated.

---

# Provenance Never Disappears

Every SourceDocument permanently records its origin.

Questions such as:

- Where did this information originate?
- Who published it?
- When was it acquired?
- How was it obtained?

must remain answerable throughout the lifetime of the observatory.

Provenance is never discarded.

---

# Authority

Institutional Memory distinguishes between observations of different authority.

Examples include:

- official university publications
- departmental documents
- accreditation reports
- external standards
- public references

Authority is metadata.

It does not alter the observation itself.

Later services may incorporate authority into reasoning.

---

# Multiple Observations

The same institutional fact may be observed many times.

For example:

A policy may appear:

- on a website
- in a PDF handbook
- in a faculty manual
- inside a committee report

Each represents an independent observation.

Institutional Memory preserves each observation independently while allowing later services to identify semantic relationships between them.

---

# Duplicate Content

Different observations sometimes contain identical content.

ISO distinguishes between:

duplicate observations

and

duplicate content.

Two independent observations with identical content remain valuable because they represent multiple institutional witnesses to the same information.

The observatory records both.

---

# Institutional Memory Is Not a Vector Database

Vector databases are optimized for retrieval.

Institutional Memory is optimized for preservation.

Embeddings may be regenerated.

Indexes may be rebuilt.

Retrieval algorithms may evolve.

Institutional Memory remains stable.

---

# A Living Historical Record

Institutional Memory should be viewed as a continuously growing historical archive.

Every observation extends the institution's recorded history.

Rather than replacing previous knowledge, new observations enrich institutional understanding through time.

---

# Foundation for Temporal Reasoning

Because observations are preserved historically, ISO can eventually answer questions such as:

"What is the current undergraduate catalog?"

"What did the undergraduate catalog contain in 2018?"

"How has the curriculum evolved over the past decade?"

"When did this policy first appear?"

"When was this requirement removed?"

These questions become possible because Institutional Memory preserves observations rather than snapshots.

---

# Relationship to the Observatory

Institutional Memory provides the raw material from which the observatory constructs understanding.

Observatory services evaluate:

- coverage
- uncertainty
- semantic diversity
- evidence quality
- temporal evolution

None of these services modify Institutional Memory itself.

Memory stores observations.

The observatory derives meaning.

---

# Looking Ahead

Future versions of Institutional Memory may support:

- observation version graphs
- semantic evolution tracking
- observation lineage
- confidence propagation
- historical reconstruction
- institutional timelines
- temporal evidence retrieval

The current architecture is intentionally designed so these capabilities can be added without changing existing observations.

---

# Closing Statement

Institutional Memory is founded on a simple principle:

**Institutions should remember what they observed, not merely what they currently believe.**

By preserving observations together with provenance, authority, and time, ISO creates a durable institutional memory capable of supporting both present-day decision making and historical understanding.

