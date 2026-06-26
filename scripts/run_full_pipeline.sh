#!/bin/bash

set -euo pipefail

echo "============================================================"
echo "Running FULL Department LLM Assistant pipeline"
echo "============================================================"

echo
echo "1. Inventory"
python3 -m scripts.inventory_corpus

echo
echo "2. Clear previous derived outputs"
rm -f storage/normalized/*.json
rm -f storage/chunks/*.json
rm -f storage/embeddings/*.json
rm -f storage/vector_db/*

echo
echo "3. Normalize all supported documents"
python3 -m scripts.normalize_documents --limit 1000000

echo
echo "4. Chunk all normalized documents"
python3 -m scripts.chunk_documents --limit 1000000

echo
echo "5. Embed all chunks"
python3 -m scripts.embed_chunks --limit 1000000

echo
echo "6. Build FAISS vector index"
python3 -m scripts.build_vector_index

echo
echo "7. Verify vector database"
jq . storage/vector_db/metadata.json

echo
echo "============================================================"
echo "FULL pipeline complete"
echo "============================================================"
