# Architecture FAQ

> *Frequently Asked Questions about the design philosophy of the Institutional Knowledge Framework.*

---

# Why doesn't the LLM simply read all of the documents?

Because retrieval and reasoning are fundamentally different problems.

Retrieval answers the question:

> *Which information is relevant?*

Reasoning answers the question:

> *Given the relevant information, what conclusion should be drawn?*

Modern language models are excellent reasoning engines, but they are inefficient knowledge retrieval systems. The framework therefore separates these responsibilities.

**Design Principle**

> Retrieval and reasoning should remain independent.

---

# Why not simply embed the PDF files?

Because a PDF is a file format, not a semantic representation.

The framework first transforms every supported file into a canonical `Document` object.

Embeddings are then derived from the normalized document rather than from the original file.

This allows:

- multiple parsers
- multiple embedding models
- improved provenance
- stable downstream processing

**Design Principle**

> Documents are canonical. Embeddings are derived.

---

# Why normalize documents?

Parsing is expensive.

Normalization performs that work exactly once.

After normalization, every downstream component operates on the same representation regardless of whether the source was a PDF, DOCX, HTML document, plain text file, email, or another supported format.

Normalization therefore separates file handling from knowledge processing.

**Design Principle**

> Convert many input formats into one canonical representation.

---

# Why introduce a KnowledgeObject base class?

Because documents are only one kind of knowledge.

Today the framework contains:

- Document
- Chunk

Future implementations may include:

- Email
- CalendarEvent
- Person
- Dataset
- Policy
- Meeting
- Organization

The framework represents knowledge rather than files.

**Design Principle**

> Design for concepts, not file formats.

---

# Why preserve provenance?

Institutional systems require trust.

Every answer should be traceable back to its supporting evidence.

The framework therefore records provenance throughout the pipeline, including:

- source document
- parser
- timestamps
- metadata
- content hashes
- parent relationships

This enables:

- verification
- auditing
- debugging
- reproducibility

**Design Principle**

> Every derived object should know where it came from.

---

# Why chunk documents?

Modern embedding models and language models have finite context windows.

Large documents therefore need to be divided into smaller semantic units.

Chunking also improves retrieval accuracy because individual sections of a document often address different topics.

A future version of the framework may support multiple chunking strategies, including semantic chunking.

**Design Principle**

> Chunking creates units of reasoning.

---

# Why use embeddings?

Embeddings map semantic meaning into a high-dimensional vector space.

The embedding is **not** the document.

Instead, it is a mathematical representation of the document's meaning.

Semantic similarity becomes geometric proximity.

This allows retrieval of conceptually similar information even when different words are used.

**Design Principle**

> Meaning becomes geometry.

---

# Why use a vector database?

Traditional databases retrieve exact matches.

Vector databases retrieve semantic neighbors.

Instead of asking

> "Which document contains these words?"

the framework asks

> "Which knowledge objects are closest in semantic space?"

This produces much more flexible retrieval.

**Design Principle**

> Retrieval should operate on meaning rather than keywords.

---

# Why use a cross-encoder after vector search?

Vector search is fast.

Cross-encoders are accurate.

The framework combines both.

1. Vector search rapidly finds candidate chunks.
2. The cross-encoder jointly evaluates the question and each candidate.
3. The best candidates are passed to the language model.

This two-stage approach balances efficiency and quality.

**Design Principle**

> Fast retrieval followed by careful ranking.

---

# Why separate retrieval from reasoning?

Because they evolve independently.

Different projects may wish to substitute:

- embedding models
- vector databases
- rerankers
- language models

without changing the remainder of the architecture.

This modularity also simplifies experimentation.

**Design Principle**

> Independent components are easier to improve.

---

# Why separate the framework from the application?

The Department Knowledge Assistant is only the first application.

The same architecture should eventually support:

- enrollment forecasting
- strategic planning
- institutional analytics
- research knowledge management
- administrative decision support

Applications should build upon the framework rather than embedding architectural decisions within themselves.

**Design Principle**

> Framework before application.

---

# Why build this from first principles instead of using LangChain?

Frameworks such as LangChain provide useful abstractions and integrations.

However, this project has a different objective.

The goal is to understand the architectural principles underlying Retrieval-Augmented Generation systems rather than simply assemble existing components.

By implementing each stage directly, the architecture remains transparent, understandable, and adaptable.

The resulting framework is intentionally educational as well as practical.

**Design Principle**

> Understand the architecture before abstracting it.

---

# Why is the language model the final stage?

The language model is the reasoning engine.

Everything before it exists to improve the quality of the information supplied to that reasoning engine.

A better prompt is usually the result of:

- better retrieval
- better provenance
- better normalization
- better chunking

rather than a larger language model.

**Design Principle**

> Better knowledge is more valuable than a larger model.

---

# Is this project about chatbots?

No.

A chatbot is simply one possible interface.

The framework is fundamentally about representing, organizing, retrieving, and reasoning over institutional knowledge.

The Department Knowledge Assistant is the first reference implementation of that broader architecture.

**Design Principle**

> The objective is not conversation.

> The objective is institutional reasoning.

---

# What have we learned?

Throughout the development of the framework, several architectural principles have emerged repeatedly.

1. Documents are canonical.
2. Embeddings are derived representations.
3. Provenance should never be discarded.
4. Every stage should have a single responsibility.
5. Retrieval and reasoning are separate problems.
6. Frameworks should outlive today's models and libraries.
7. Good abstractions are more valuable than clever implementations.

These principles are expected to remain stable even as parsers, embedding models, vector databases, rerankers, and language models continue to evolve.
