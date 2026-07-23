#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  source .venv/bin/activate
fi

RUN_ROOT="storage/logs/department_three_year_sch_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUN_ROOT"/{workforce,profiles,timeline,three_year}

PYTHONPATH="$PWD" pytest -q \
  scripts/test_department_three_year_sch.py \
  scripts/test_department_sch_timeline.py

PYTHONPATH="$PWD" python scripts/build_analytical_workforce.py \
  --normalized-root storage/normalized \
  --output-dir "$RUN_ROOT/workforce" >/dev/null

PYTHONPATH="$PWD" python scripts/build_department_profiles.py \
  --normalized-root storage/normalized \
  --workforce-output "$RUN_ROOT/workforce" \
  --output-dir "$RUN_ROOT/profiles" >/dev/null

PYTHONPATH="$PWD" python scripts/build_department_sch_timeline.py \
  --normalized-root storage/normalized \
  --workforce-output "$RUN_ROOT/workforce" \
  --profiles-output "$RUN_ROOT/profiles" \
  --output-dir "$RUN_ROOT/timeline" >/dev/null

PYTHONPATH="$PWD" python scripts/build_department_three_year_sch.py \
  --timeline "$RUN_ROOT/timeline/department_sch_timeline.json" \
  --output-dir "$RUN_ROOT/three_year"

echo "CSV: $RUN_ROOT/three_year/department_three_year_sch.csv"
echo "Reports: $RUN_ROOT/three_year"
