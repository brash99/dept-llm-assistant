# Institutional Knowledge Framework (IKF)

> An explainable semantic layer for AI-assisted institutional decision support.

---

## Vision

The Institutional Knowledge Framework (IKF) is **not** a chatbot project.

It is a software architecture for transforming institutional information into a structured semantic ecosystem that can be searched, evaluated, synthesized, and ultimately used to support evidence-based administrative decision making.

The Department Knowledge Assistant is the first reference implementation of the framework.

Our long-term vision is an **institutional semantic digital twin** capable of assisting university leaders with complex planning and policy questions while ensuring that every recommendation remains transparent, explainable, and grounded in institutional evidence.

> **The AI should assist human decision makers—not replace them.**

---

# Current Status

The project has completed **Phase I** and is now entering **Phase II**.

## Phase I — Building the Semantic Layer

Completed:

- Google Drive synchronization
- Corpus inventory
- Corpus policy
- Parser framework
- Canonical document model
- Document normalization
- Chunk generation
- SentenceTransformer embeddings
- FAISS vector database
- Cross-encoder reranking
- Local LLM inference (vLLM + Qwen)
- Explainable citations
- Retrieval diagnostics
- Performance profiling
- Retrieval benchmarking
- Corpus Observatory

Current benchmark performance:

- Top-1: **23 / 30**
- Top-5: **26 / 30**

Current corpus:

- **15,398 documents**
- **310,097 chunks**
- Mean chunks/document: **20.1**
- Median chunks/document: **7**
- Gini coefficient: **0.7596**

---

# Current Architecture

```
Google Drive
      │
      ▼
Corpus Policy
      │
      ▼
Normalization
      │
      ▼
Canonical Documents
      │
      ▼
Chunk Generation
      │
      ▼
Embeddings (BGE)
      │
      ▼
FAISS Retrieval
      │
      ▼
Cross Encoder Reranking
      │
      ▼
Evidence Selection
      │
      ▼
Local LLM
      │
      ▼
Grounded Answer
```

Every answer is traceable back to retrieved institutional evidence.

---

# Engineering Philosophy

The project is intentionally engineered from first principles rather than relying on monolithic RAG frameworks.

Several ideas guide the architecture.

## Everything should be measurable.

Architectural decisions are benchmark-driven rather than anecdotal.

---

## Everything should be explainable.

Every retrieval stage is observable:

- vector retrieval
- deduplication
- reranking
- prompt construction
- citations

---

## Corpus quality matters.

Retrieval systems cannot outperform their corpus.

Corpus health is therefore treated as a first-class engineering concern.

---

## Modular architecture.

Every major component is independently replaceable.

Examples include:

- embedding models
- rerankers
- parsers
- chunking strategies
- retrieval algorithms
- language models

---

# Corpus Observatory

The framework includes an interactive developer interface for monitoring corpus health.

Current diagnostics include:

- parser usage
- chunk distributions
- document distributions
- folder distributions
- dominance metrics
- largest documents
- Gini coefficient
- benchmark summaries
- retrieval timing

The Observatory treats corpus engineering as an ongoing architectural discipline rather than a preprocessing step.

---

# Phase II — Institutional Decision Support

The project is now evolving beyond question answering.

The next objective is the generation of **Decision Briefs**.

Representative questions include:

- What resources would be required to launch a Mechanical Engineering major?

- What are the implications of replacing—or not replacing—a retiring faculty member?

- Which departments become most vulnerable under a projected enrollment scenario?

Rather than producing answers, the framework will synthesize evidence across:

- curriculum
- faculty expertise
- facilities
- laboratory equipment
- accreditation
- strategic planning
- budgets
- historical documents

Every recommendation will remain fully explainable through citations to the supporting evidence.

---

# Long-Term Vision

The long-term objective is the creation of an institutional semantic digital twin.

Future capabilities include:

- scenario analysis
- strategic planning
- enrollment forecasting
- hiring analysis
- curriculum planning
- resource optimization
- probabilistic institutional modeling

The emphasis remains on augmenting human judgment through transparent, evidence-based AI.

---

# Documentation

The repository documentation is organized into three complementary perspectives.

## Sessions

Chronological design history describing the evolution of the architecture.

```
docs/sessions/
```

---

## Architecture

Descriptions of the current framework.

```
docs/architecture/
```

---

## Engineering

Benchmarking, corpus health, retrieval diagnostics, and performance.

```
docs/engineering/
```

---

# Guiding Principle

The primary deliverable is **not** a chatbot.

The primary deliverable is an explainable, measurable, and reusable architecture for institutional knowledge systems capable of supporting evidence-based decision making.
