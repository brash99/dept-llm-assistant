#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OBJECTS_DIR="${1:-storage/semantic/contributions/departments}"

cd "$PROJECT_ROOT"
exec streamlit run scripts/ontology_explorer.py -- \
  --objects-dir "$OBJECTS_DIR"
