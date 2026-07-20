# Session 3 — From Files to Knowledge

> **Archive notice:** Historical laboratory note. Current architecture, status, and commands are documented in [the session archive index](README.md).

*Project Design History*

---

**Date**

June 2026

---

# Introduction

By the conclusion of Session 2, the project possessed a reliable software infrastructure and a complete local mirror of the department's shared Google Drive.

The framework could now access the institutional corpus, but it still knew essentially nothing about it.

A directory containing tens of thousands of files is not, by itself, a knowledge base.

The next challenge therefore became understanding the corpus before attempting to process it.

Rather than immediately parsing documents, the project first stepped back and asked a simple question:

> *What exactly are we dealing with?*

This question led naturally to the development of the corpus inventory stage.

---

# Objectives

The primary goals of this session were:

1. Characterize the institutional corpus.

2. Measure the size and composition of the document collection.

3. Establish a repeatable inventory process.

4. Introduce corpus-wide statistics.

5. Begin thinking about documents as knowledge rather than files.

Although no artificial intelligence was yet involved, this session represented the first attempt to understand the structure of the institutional knowledge base.

---

# Inventory Before Processing

An important architectural decision emerged early.

Rather than immediately processing every document, the framework would first perform an inventory pass over the corpus.

This decision was motivated by a simple observation.

Large scientific data sets are rarely analyzed before they are characterized.

Institutional document collections should be treated no differently.

The inventory stage therefore became the equivalent of an exploratory analysis.

Its purpose was not to modify documents but to answer questions such as:

- How many files exist?
- Which file types are present?
- How large is the corpus?
- Which directories dominate the collection?
- Which formats require parser support?

Only after understanding the corpus would the framework begin transforming it.

---

# Building the Inventory

The first inventory utility traversed the mirrored Google Drive and collected summary information describing the corpus.

The resulting report included:

- total number of files
- total storage consumed
- file extension counts
- directory statistics
- largest files
- summary metadata

Importantly, the inventory itself became another generated artifact.

Rather than printing information to the console, the framework stored structured inventory reports as JSON.

```text
Google Drive Mirror
        │
        ▼
Corpus Inventory
        │
        ▼
Inventory Report (JSON)
```

This seemingly minor decision reflected an emerging philosophy.

Whenever practical, intermediate results should become reusable data products rather than transient console output.

---

# The Scale of the Corpus

The first inventory produced an important realization.

The repository contained approximately:

- 24,000 documents
- over 55 GB of information
- dozens of distinct file formats

This confirmed that the framework would need to operate as an automated pipeline.

Manual inspection of individual documents was no longer practical.

Every subsequent stage would need to function at corpus scale.

---

# Corpus Policy

As inventory reports became available, another architectural question naturally emerged.

Should every discovered file become part of the knowledge base?

The answer was clearly "no."

Hidden files, temporary files, unsupported formats, generated artifacts, and various system files contributed little useful information while increasing computational cost.

Rather than embedding filtering logic within each processing stage, the project introduced the concept of a centralized corpus policy.

This policy would eventually govern:

- excluded directories
- ignored file extensions
- hidden files
- supported parsers
- future inclusion rules

The inventory stage therefore became the first consumer of this policy.

Future stages would reuse exactly the same rules.

---

# The First Architectural Shift

Perhaps the most important realization of the session had little to do with software.

The project gradually stopped thinking in terms of files.

Instead, it began thinking in terms of information.

A PDF, Word document, HTML page, or plain text file were simply different containers for institutional knowledge.

The framework should ultimately operate on the knowledge itself rather than the storage format.

Although the necessary abstractions had not yet been introduced, the idea of a canonical representation was beginning to emerge.

This insight would become the central architectural theme of the following sessions.

---

# Lessons Learned

Several important lessons emerged during the inventory stage.

First, understanding a corpus should precede processing it.

Second, institutional repositories evolve over many years and inevitably contain a wide variety of formats and organizational conventions.

Finally, inventory is not merely a debugging tool.

It is an architectural component that enables informed decisions throughout the remainder of the processing pipeline.

By the conclusion of this session, the framework had progressed from simply possessing a collection of files to possessing measurable knowledge about that collection.

---

# Looking Ahead

Inventory answered an important question.

> *What documents exist?*

The next session would address a much deeper one.

> *How should those documents be represented?*

The search for that answer would ultimately lead to the introduction of the framework's first fundamental abstraction:

**KnowledgeObject**.

With it, the project would begin its transition from document processing to knowledge representation.
