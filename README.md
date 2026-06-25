# Department LLM Assistant

An open-source platform for deploying and evaluating local Large Language Models
for departmental knowledge management.

## Goals

- Deploy open-source LLMs on an NVIDIA A100 server
- Build a Retrieval-Augmented Generation (RAG) pipeline
- Index departmental documents from Google Drive
- Provide citation-aware responses
- Establish reusable AI infrastructure for future applications

## Repository Structure

- app/           User-facing application
- ingestion/     Document synchronization and parsing
- rag/           Embeddings, vector database, retrieval
- evals/         Evaluation datasets and benchmarks
- docker/        Container deployment
- docs/          Documentation
- scripts/       Utility scripts
