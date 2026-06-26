#!/bin/bash

set -euo pipefail

LIMIT="${1:-2000}"

echo "============================================================"
echo "Running sample pipeline"
echo "Limit: $LIMIT normalized documents"
echo "============================================================"

echo
echo "1. Inventory"
python3 -m scripts.inventory_corpus

echo
echo "2. Classification"
python3 -m scripts.classify_corpus

echo
echo "3. Clear normalized and chunks"
rm -f storage/normalized/*.json
rm -f storage/chunks/*.json

echo
echo "4. Normalize documents"
python3 -m scripts.normalize_documents --limit "$LIMIT"

echo
echo "5. Chunk documents"
python3 -m scripts.chunk_documents --limit "$LIMIT"

echo
echo "============================================================"
echo "Sample pipeline complete"
echo "============================================================"
