#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  source .venv/bin/activate
fi

ADMIN_WORKBOOK="${1:-${ADMIN_SCH_WORKBOOK:-}}"
if [[ -z "$ADMIN_WORKBOOK" ]]; then
  mapfile -t CANDIDATES < <(
    find data/acquisition storage/imports storage/governed \
      -type f \( -iname '*.xlsx' -o -iname '*.xlsm' \) 2>/dev/null \
      | sort
  )
  if [[ "${#CANDIDATES[@]}" -eq 1 ]]; then
    ADMIN_WORKBOOK="${CANDIDATES[0]}"
  else
    echo "Pass the administration workbook as the first argument or set ADMIN_SCH_WORKBOOK." >&2
    echo "Candidate workbook count: ${#CANDIDATES[@]}" >&2
    exit 2
  fi
fi
[[ -f "$ADMIN_WORKBOOK" ]] || {
  echo "Administration workbook not found: $ADMIN_WORKBOOK" >&2
  exit 2
}

RUN_ROOT="storage/logs/admin_sch_reconciliation_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUN_ROOT"/{workforce,profiles,timeline,reconciliation_1,reconciliation_2}

PYTHONPATH="$PWD" pytest -q \
  scripts/test_administration_sch_reconciliation.py \
  scripts/test_department_sch_timeline.py \
  scripts/test_department_profiles.py

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

for run in 1 2; do
  PYTHONPATH="$PWD" python scripts/reconcile_administration_sch.py \
    --admin-workbook "$ADMIN_WORKBOOK" \
    --timeline "$RUN_ROOT/timeline/department_sch_timeline.json" \
    --normalized-root storage/normalized \
    --workforce-output "$RUN_ROOT/workforce" \
    --profiles-output "$RUN_ROOT/profiles" \
    --output-dir "$RUN_ROOT/reconciliation_$run" \
    >"$RUN_ROOT/reconciliation_$run.log"
done

diff -qr "$RUN_ROOT/reconciliation_1" "$RUN_ROOT/reconciliation_2"
jq '{
  academic_years,
  average_formula,
  iso_llc_definition,
  summary,
  largest_sch_differences: (.rows[:10] | map({
    department,
    faculty_difference,
    sch_difference,
    sch_percent_difference,
    llc_sch_difference,
    llc_percent_difference,
    explanation_categories
  })),
  deterministic_fingerprint
}' "$RUN_ROOT/reconciliation_1/department_reconciliation_summary.json"

echo "Reports: $RUN_ROOT/reconciliation_1"
