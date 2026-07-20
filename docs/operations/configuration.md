# Configuration Reference

The runtime configuration is `config/settings.yaml`. The checked-in file is the A100 configuration and uses:

```yaml
project:
  root: /work/brash/dept-llm-assistant
```

Do not commit a macOS path as the project root.

## Storage

`storage` entries are relative to `project.root` unless a script documents otherwise. Important derived directories are `normalized`, `constitutional`, `chunks`, `embeddings`, `vector_db`, `cache`, and `logs`. Repository storage placeholders are not production data.

## LLM

`llm.base_url` and `llm.model` identify an OpenAI-compatible inference endpoint. The repository consumes this endpoint but does not launch or supervise it.

## Embedding and reranking

`embedding` selects the sentence-transformer model, batch size, and device. `reranking` controls the cross-encoder, device, and optional minimum logit. A null reranker threshold preserves all diversified candidates before quota selection.

Reranker logits are not calibrated confidence scores.

## Retrieval

`retrieval.fetch_k` controls the broad candidate pool. `constitutional_top_k` and `empirical_top_k` control final evidence allocation. Decision Brief retrieval additionally applies its configured/default document-family maximum.

## Chunking

`chunking.chunk_size`, `overlap`, and `max_chunks_per_document` control derived chunks. A null maximum disables truncation. Changing chunking requires rebuilding chunks, embeddings, and the index.

## Normalization sources

`normalization_sources` is an ordered registry. Each entry has a stable key, root, priority, and description. Lower priority numbers are processed first and influence which byte-identical source becomes canonical.

List resolved sources before a large run:

```bash
.venv/bin/python -m scripts.normalize_documents --list-sources
```

## Other registries

- `config/institutional_programs.yaml` — asserted academic programs and aliases.
- `config/institutional_constitution.yaml` — curated constitutional source records and principles.
- `config/observers_v2.yaml` — governed observer definitions.
- `config/web_observers.yaml` — website observer definitions.
- `config/schev_observers.yaml` — SCHEV observer definitions.

These registries store asserted configuration. Resolver, orientation, Evidence Fitness, and presentation services derive meaning from them.
