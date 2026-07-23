#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"
if [[ -z "${VIRTUAL_ENV:-}" ]]; then source .venv/bin/activate; fi

RUN_ROOT="storage/logs/faculty_delivered_sch_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUN_ROOT"/{workforce,profiles,comparison_1,comparison_2}

PYTHONPATH="$PWD" pytest -q \
  scripts/test_faculty_delivered_sch.py \
  scripts/test_department_profiles.py \
  scripts/test_department_sch_timeline.py

PYTHONPATH="$PWD" python scripts/build_analytical_workforce.py \
  --normalized-root storage/normalized \
  --output-dir "$RUN_ROOT/workforce" >/dev/null
PYTHONPATH="$PWD" python scripts/build_department_profiles.py \
  --normalized-root storage/normalized \
  --workforce-output "$RUN_ROOT/workforce" \
  --output-dir "$RUN_ROOT/profiles" >/dev/null

EXTRA_ARGS=()
if [[ -n "${QUENTIN_TABLE:-}" ]]; then
  EXTRA_ARGS+=(--quentin-table "$QUENTIN_TABLE")
fi
for run in 1 2; do
  PYTHONPATH="$PWD" python scripts/build_faculty_delivered_sch.py \
    --normalized-root storage/normalized \
    --workforce-output "$RUN_ROOT/workforce" \
    --profiles-output "$RUN_ROOT/profiles" \
    --output-dir "$RUN_ROOT/comparison_$run" \
    --fall-only \
    "${EXTRA_ARGS[@]}" >"$RUN_ROOT/comparison_$run.log"
done
diff -qr "$RUN_ROOT/comparison_1" "$RUN_ROOT/comparison_2"
echo "Reports: $RUN_ROOT/comparison_1"
if [[ -z "${QUENTIN_TABLE:-}" ]]; then
  echo "Quentin comparison not generated: set QUENTIN_TABLE to a CSV with columns Department,Quentin SCH."
fi
