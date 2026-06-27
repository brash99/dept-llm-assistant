# Session 4 — Discovering the Object Model

*Project Design History*

---

**Date**

June 2026

---

# Introduction

By the end of Session 3, the framework could reliably synchronize, inventory, and characterize the institutional corpus.

A much more interesting question now emerged.

> *What exactly is a document?*

At first, the answer appeared obvious.

A document was simply a PDF, Word file, HTML page, or text file.

The more the project evolved, however, the less satisfying this definition became.

A PDF is not knowledge.

A Word document is not knowledge.

They are merely storage formats.

The framework therefore needed a representation that captured the semantic content of a document while remaining independent of the format in which it had originally been stored.

This realization became the turning point of the project.

---

# Objectives

The goals of this session were:

1. Define the canonical representation of institutional knowledge.

2. Separate parsing from normalization.

3. Introduce reusable software abstractions.

4. Prepare the framework for multiple document formats.

5. Begin thinking in terms of knowledge rather than files.

This session established the conceptual foundation upon which the remainder of the framework would be built.

---

# The Canonical Representation

One of the most important architectural discussions of the project centered on a deceptively simple question.

> *What object should downstream components consume?*

Several possibilities were considered.

Should chunking operate directly on PDFs?

Should embeddings be generated directly from Word documents?

Should every parser implement its own downstream logic?

The answer gradually became clear.

Every supported file format should first be transformed into a common representation.

That representation became the **Document**.

```text
PDF
DOCX
HTML
TEXT
   │
   ▼
Document
```

From that point onward, every downstream stage would operate exclusively on Document objects.

The original file format became an implementation detail.

---

# Beyond Documents

Even as the Document abstraction was taking shape, another realization emerged.

Documents were unlikely to be the only objects the framework would eventually represent.

Future applications might include:

- email messages
- meetings
- calendar events
- policies
- research datasets
- faculty
- students
- organizations

The framework therefore introduced a more general abstraction.

```text
KnowledgeObject
        │
        ▼
    Document
```

Although Document was initially the only concrete implementation, the existence of a common base class fundamentally changed the architecture.

The framework was no longer about processing documents.

It was about representing knowledge.

---

# Separating Parsing from Normalization

Another important discussion concerned responsibility.

Originally, parsing and normalization appeared to be closely related.

On closer examination, they served different purposes.

A parser understands a specific file format.

Normalization constructs a canonical Document.

These responsibilities should remain independent.

The architecture therefore became:

```text
Raw File
     │
     ▼
 Parser
     │
     ▼
Document
```

This separation greatly simplified both testing and future extensibility.

Adding support for a new document format would require only a new parser.

The remainder of the framework would remain unchanged.

---

# The Parser Registry

Once multiple parsers became inevitable, another design question naturally followed.

How should the framework decide which parser to use?

Rather than embedding conditional logic throughout the codebase, parser selection became the responsibility of a dedicated registry.

```text
          Raw File
               │
               ▼
      Parser Registry
               │
     ┌─────────┴─────────┐
     ▼                   ▼
 PDFParser         TextParser
```

The Parser Registry became responsible for discovering and selecting parser implementations based upon file type.

This decision significantly reduced coupling between the ingestion pipeline and individual parsers.

More importantly, it established a pattern that would later reappear throughout the framework.

Registries select implementations.

Implementations perform work.

---

# Framework Before Implementation

One of the recurring themes throughout the project became particularly visible during this session.

Whenever a new capability was introduced, the first question was not

> *How should we implement this?*

Instead, the question became

> *What is the correct abstraction?*

Only after agreeing upon the abstraction did implementation begin.

This philosophy often slowed development slightly in the short term.

In the long term, however, it consistently produced cleaner and more extensible software.

---

# Lessons Learned

This session fundamentally changed the nature of the project.

The framework was no longer organized around file formats.

It was organized around semantic objects.

Several important architectural principles emerged.

- Knowledge should have a canonical representation.

- Parsing and normalization are separate responsibilities.

- Frameworks should be designed around abstractions rather than implementations.

- Registries reduce coupling and improve extensibility.

Looking back, these principles would influence nearly every subsequent component of the system.

---

# Looking Ahead

With a canonical Document representation established, the next challenge became straightforward.

The framework now needed to transform thousands of institutional documents into this new representation.

The following session would focus on generalizing the normalization pipeline, introducing reusable processing functions capable of operating on both individual files and entire document collections.

For the first time, the framework would begin producing a persistent knowledge base rather than simply processing raw files.
