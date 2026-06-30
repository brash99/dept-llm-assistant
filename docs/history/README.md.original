
# Institutional Knowledge Framework (IKF)

> A modular framework for representing, retrieving, and reasoning over institutional knowledge.

## Vision

The Institutional Knowledge Framework (IKF) is **not** a chatbot project.

It is a reusable software architecture for transforming heterogeneous institutional
information into structured knowledge that can be searched, retrieved, evaluated,
and reasoned over by modern AI systems.

The Department Knowledge Assistant is the first reference implementation and serves
as the experimental platform for developing the framework.

## Current Status

The framework currently includes:

- Google Drive synchronization (`rclone`)
- Corpus inventory and corpus policy
- Canonical `Document` normalization
- Configurable parser registry
- Chunk generation
- SentenceTransformer embeddings
- FAISS vector database
- Cross-encoder reranking
- Local inference using vLLM + Qwen
- Streamlit interface
- Rich retrieval diagnostics
- Configurable retrieval benchmark framework
- Category-level benchmark reporting
- Retrieval timing instrumentation

## Architecture

Google Drive
→ Normalized Documents
→ Chunks
→ Embeddings
→ FAISS Retrieval
→ Cross-Encoder Reranker
→ Prompt Builder
→ Local LLM
→ Grounded Answer

## Recent Milestone

The project has entered a new phase.

The initial objective was to build a working RAG system.

The current objective is to build a **retrieval engineering platform** that enables
systematic experimentation with:

- embedding models
- chunking strategies
- rerankers
- retrieval thresholds
- hybrid retrieval
- heterogeneous retrieval pipelines

Every architectural change is evaluated against a growing benchmark suite rather
than isolated example queries.

## Roadmap

Near-term work includes:

1. Expand retrieval benchmark corpus.
2. Compare embedding models (BGE-small, BGE-base, BGE-large).
3. Evaluate alternative rerankers.
4. Investigate hybrid dense/BM25 retrieval.
5. Introduce document-type-specific retrieval pipelines.
6. Extend the framework toward institution-scale decision support.

## Guiding Principle

The primary deliverable is **not** a chatbot.

The primary deliverable is a principled, measurable, and reusable architecture for
institutional knowledge systems.
