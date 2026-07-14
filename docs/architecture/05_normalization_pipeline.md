# Institutional Semantic Observatory (ISO)

## Normalization Pipeline

**Version 0.1**

---

# Introduction

Observation acquires institutional information.

Normalization transforms those observations into canonical institutional memory.

The Normalization Pipeline is therefore the bridge between Distributed Institutional Observation and Institutional Memory.

Its purpose is not to interpret information.

Its purpose is to represent information consistently.

---

# Why Normalize?

Institutions store information in many forms.

Examples include:

- PDF
- Word
- PowerPoint
- Excel
- HTML
- Markdown
- CSV
- XML
- Plain Text

Each format stores information differently.

Higher layers of ISO should not need to understand these differences.

Normalization converts every supported format into a common semantic representation.

---

# Canonical Output

Every normalized observation becomes a Knowledge Object.

Regardless of source format, every normalized object contains:

- identifier
- title
- text
- metadata
- provenance
- timestamps
- authority
- acquisition metadata

After normalization, downstream services operate on a consistent representation.

---

# Parser Architecture

Normalization is parser-driven.

Each parser understands one document format.

Examples include:

- PDFParser
- DOCXParser
- PPTXParser
- XLSXParser
- HTMLParser
- TextParser
- LegacyOfficeParser

Parsers are registered through the Parser Registry.

The registry determines which parser should process each observation.

---

# Parser Responsibilities

A parser is responsible for:

- reading the source
- extracting text
- extracting metadata
- assigning a title
- preserving provenance
- producing a canonical Knowledge Object

A parser is not responsible for:

- chunking
- embeddings
- semantic analysis
- classification
- retrieval

Those belong to later architectural layers.

---

# Parser Registry

The Parser Registry provides a single abstraction for format discovery.

Given an observation, it selects the appropriate parser.

This design allows new parsers to be added without modifying the normalization pipeline itself.

Consequently, ISO is open for extension while remaining closed for modification.

---

# Multi-Source Normalization

Normalization is independent of acquisition source.

Examples include:

Filesystem Observer

Website Observer

Google Drive Observer

Future Database Observer

Future Banner Observer

Future Canvas Observer

Each observer contributes SourceDocuments.

Normalization treats them identically.

Only provenance differs.

---

# Provenance Preservation

Normalization never discards provenance.

Information such as:

- source URL
- filesystem path
- observer
- acquisition method
- authority
- timestamps

is preserved inside the resulting Knowledge Object.

This enables complete traceability throughout the observatory.

---

# Source Independence

After normalization, higher layers no longer distinguish between:

a PDF downloaded from a website,

a document acquired from Google Drive,

or

a report obtained from a database.

Each becomes a canonical Knowledge Object.

Institutional meaning is independent of storage technology.

---

# Duplicate Observations

Normalization preserves observations.

It does not attempt semantic deduplication.

Two different observations may legitimately contain identical content.

Later services determine how those relationships should be interpreted.

Normalization simply records what was observed.

---

# Relationship to Institutional Memory

Normalization is the point at which observations become institutional memory.

Before normalization:

information belongs to an external system.

After normalization:

the observation becomes part of ISO.

This architectural boundary is intentionally explicit.

---

# Relationship to Later Stages

Normalization precedes:

- chunking
- embeddings
- vector indexing
- retrieval
- observatory analysis

Every downstream service relies upon normalized Knowledge Objects.

Because normalization produces canonical objects, later services remain independent of acquisition technology.

---

# Looking Ahead

Future normalization capabilities may include:

- OCR integration
- speech transcription
- video transcription
- structured database extraction
- semantic metadata extraction
- multilingual normalization
- image understanding

These capabilities extend normalization without changing the architectural contract.

---

# Closing Statement

Normalization performs one essential task:

**It transforms institutional observations into canonical institutional memory.**

By separating acquisition from normalization, ISO creates a stable semantic foundation upon which every higher-level capability of the observatory is built.

