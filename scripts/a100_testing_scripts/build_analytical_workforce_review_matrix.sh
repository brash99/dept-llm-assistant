#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"
if [[ -z "${VIRTUAL_ENV:-}" ]]; then source .venv/bin/activate; fi
RUN_ROOT="${1:-}"
if [[ -z "$RUN_ROOT" ]]; then
  RUN_ROOT="$(ls -dt storage/logs/analytical_workforce_builder_* 2>/dev/null | head -1)"
fi
[[ -n "$RUN_ROOT" && -f "$RUN_ROOT/workforce_1/analytical_workforce_population.json" ]] || { echo "No analytical workforce production run found" >&2; exit 2; }
PYTHONPATH="$PWD" python scripts/a100_testing_scripts/build_analytical_workforce_review_matrix.py --run-root "$RUN_ROOT"
