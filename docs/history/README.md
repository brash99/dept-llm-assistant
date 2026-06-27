# Institutional Knowledge Framework

> *A reusable software framework for transforming institutional information into structured knowledge that can be searched, retrieved, and reasoned over by modern AI systems.*

---

## Vision

Large Language Models (LLMs) are powerful reasoning engines, but they are not institutional knowledge systems. Their usefulness depends on the quality, organization, provenance, and retrieval of the information supplied to them.

The **Institutional Knowledge Framework (IKF)** is a modular architecture for building Retrieval-Augmented Generation (RAG) systems over institutional data.

Rather than viewing an LLM as the application itself, IKF treats it as the **final reasoning component** of a much larger information-processing pipeline.

The first reference implementation is a Department Knowledge Assistant built over a shared Google Drive document repository. The long-term vision is much broader: a reusable framework capable of supporting strategic planning, enrollment forecasting, institutional analytics, research knowledge management, and administrative decision support.

---

# Design Philosophy

The framework is built around several guiding principles.

## Documents are Canonical

Institutional documents remain the authoritative representation of knowledge.

The framework **does not transform documents into embeddings**. Instead, progressively richer semantic representations are derived from a stable canonical document.

```text
Raw Document
      │
      ▼
   Document
      │
      ▼
    Chunk
      │
      ▼
  Embedding
```

Documents preserve meaning and provenance.

Embeddings provide a mathematical representation of that meaning for semantic retrieval.

---

## Every Stage Has One Responsibility

Each stage performs a single transformation.

| Stage | Responsibility |
|--------|----------------|
| Acquisition | Synchronize source data |
| Inventory | Characterize the corpus |
| Parsing | Extract text and metadata |
| Normalization | Produce canonical Documents |
| Chunking | Create semantic reasoning units |
| Embedding | Map semantics into vector space |
| Retrieval | Locate relevant knowledge |
| Re-ranking | Improve retrieval quality |
| Reasoning | Generate grounded answers |

Because each stage has a well-defined responsibility, components can evolve independently.

---

## Provenance First

Every object produced by the framework records:

- source location
- parser
- timestamps
- metadata
- content hashes

Every generated answer can therefore be traced back to the original institutional document.

---

## Framework Before Application

Applications consume the framework.

The framework itself should remain independent of any particular institution, deployment, or user interface.

---

# Architecture

```text
                     User
                       │
                       ▼
                Streamlit UI
                       │
                       ▼
              Application Layer
                       │
                       ▼
                 Retrieval Engine
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
   Vector Database              Local LLM
         ▲                           ▲
         │                           │
     Embeddings                 Prompt Builder
         ▲
         │
      Chunks
         ▲
         │
    Documents
         ▲
         │
      Parsers
         ▲
         │
 Google Drive Mirror
```

---

# Processing Pipeline

```text
Google Shared Drive
        │
        ▼
   rclone Mirror
        │
        ▼
storage/raw_drive
        │
        ▼
 Corpus Inventory
        │
        ▼
 Parser Registry
        │
        ▼
Document Normalization
        │
        ▼
 Chunk Generation
        │
        ▼
Embedding Generation
        │
        ▼
 FAISS Vector Index
        │
        ▼
 Semantic Retrieval
        │
        ▼
Cross-Encoder Re-ranking
        │
        ▼
 Prompt Construction
        │
        ▼
 Local Qwen LLM
        │
        ▼
 Grounded Answer
```

Every intermediate representation is preserved and can be inspected independently.

---

# Core Abstractions

The framework is built around a small number of stable abstractions.

| Abstraction | Purpose |
|-------------|---------|
| `KnowledgeObject` | Base semantic object |
| `Document` | Canonical normalized document |
| `Chunk` | Unit of semantic retrieval |
| `Parser` | Converts raw files into Documents |
| `ParserRegistry` | Discovers parser implementations |
| `Embedder` | Produces semantic vectors |
| `Retriever` | Performs semantic search |
| `Reasoner` | Uses retrieved context to answer questions |

Implementations may change over time; these abstractions should remain stable.

---

# Current Capabilities

The current implementation includes:

- Google Drive synchronization using `rclone`
- Corpus inventory and statistics
- Configurable corpus policy
- PDF parsing
- Plain-text parsing
- Canonical document normalization
- Chunk generation
- SentenceTransformer embeddings
- FAISS vector indexing
- Semantic retrieval
- Cross-encoder re-ranking
- Local inference using vLLM
- Qwen reasoning model
- Streamlit web interface

The framework is capable of answering natural-language questions over a departmental corpus while providing citations to the supporting source documents.

---

# Repository Layout

```text
app/
    Core framework

scripts/
    Command-line utilities

config/
    Configuration

storage/
    Runtime data (ignored by Git)

docs/
    Documentation

tests/
    Unit tests
```

The runtime storage hierarchy currently consists of:

```text
storage/
│
├── raw_drive/
├── normalized/
├── chunks/
├── embeddings/
├── vector_db/
├── cache/
├── logs/
└── models/
```

---

# Documentation

Project documentation is divided into two parts.

**Design History**

```
docs/history/
```

Documents the evolution of the framework and the reasoning behind major architectural decisions.

**Field Guide** *(planned)*

A concept-oriented guide describing the mature architecture independent of the project's historical development.

---

# Long-Term Direction

The Department Knowledge Assistant is intended to be the first validation of a more general architecture.

Future applications include:

- Enrollment forecasting
- Strategic planning
- Institutional resource modeling
- Faculty analytics
- Research knowledge management
- Administrative decision support

The long-term objective is to build a reusable framework for institutional knowledge systems rather than a single application.

---

# Guiding Principle

> **The purpose of this project is not to build a chatbot.**
>
> **The purpose of this project is to develop a principled architecture for representing, retrieving, and reasoning over institutional knowledge.**

The language model is simply the final reasoning component of that architecture.

---

# Acknowledgments

The Institutional Knowledge Framework is being developed by Edward Brash as an exploration of knowledge representation, retrieval-augmented generation, and institutional AI systems.

The architectural design and documentation have been developed collaboratively through iterative engineering discussions with ChatGPT, emphasizing first-principles reasoning, modular software architecture, and long-term maintainability.
