#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  source .venv/bin/activate
fi

RUN_ROOT="storage/logs/department_sch_fall_only_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUN_ROOT"/{workforce,profiles,timeline_1,timeline_2,three_year_1,three_year_2}

PYTHONPATH="$PWD" pytest -q \
  scripts/test_department_sch_timeline.py \
  scripts/test_department_three_year_sch.py \
  scripts/test_department_profiles.py

PYTHONPATH="$PWD" python scripts/build_analytical_workforce.py \
  --normalized-root storage/normalized \
  --output-dir "$RUN_ROOT/workforce" >/dev/null

PYTHONPATH="$PWD" python scripts/build_department_profiles.py \
  --normalized-root storage/normalized \
  --workforce-output "$RUN_ROOT/workforce" \
  --output-dir "$RUN_ROOT/profiles" >/dev/null

for run in 1 2; do
  PYTHONPATH="$PWD" python scripts/build_department_sch_timeline.py \
    --normalized-root storage/normalized \
    --workforce-output "$RUN_ROOT/workforce" \
    --profiles-output "$RUN_ROOT/profiles" \
    --fall-only \
    --output-dir "$RUN_ROOT/timeline_$run" \
    >"$RUN_ROOT/timeline_$run.log"
  PYTHONPATH="$PWD" python scripts/build_department_three_year_sch.py \
    --timeline "$RUN_ROOT/timeline_$run/department_sch_timeline.json" \
    --output-dir "$RUN_ROOT/three_year_$run" \
    >"$RUN_ROOT/three_year_$run.log"
done

diff -qr "$RUN_ROOT/timeline_1" "$RUN_ROOT/timeline_2"
diff -qr "$RUN_ROOT/three_year_1" "$RUN_ROOT/three_year_2"

python - "$RUN_ROOT" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
timeline = json.loads(
    (root / "timeline_1/department_sch_timeline.json").read_text()
)
three_year = json.loads(
    (root / "three_year_1/department_three_year_sch.json").read_text()
)
if timeline["reporting_scope"] != "fall_only":
    raise SystemExit("Fall-only reporting scope was not preserved")
if any(item["academic_term"].split("_", 1)[1] != "fall" for item in timeline["terms"]):
    raise SystemExit("A non-fall term entered the fall-only timeline")
for department in timeline["departments"]:
    by_term = {item["academic_year"]: item["sch"] for item in department["terms"]}
    by_year = {item["academic_year"]: item["sch"] for item in department["academic_years"]}
    if by_term != by_year:
        raise SystemExit(
            f"Fall term/year mismatch: {department['department_name']}"
        )
summary = {
    "status": "passed",
    "reporting_scope": timeline["reporting_scope"],
    "department_count": timeline["department_count"],
    "fall_terms": [item["term_label"] for item in timeline["terms"]],
    "academic_years": timeline["academic_years"],
    "timeline_fingerprint": timeline["deterministic_fingerprint"],
    "three_year_fingerprint": three_year["deterministic_fingerprint"],
    "timeline_output": str(root / "timeline_1"),
    "three_year_output": str(root / "three_year_1"),
}
(root / "validation_summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n"
)
print(json.dumps(summary, indent=2, sort_keys=True))
PY

echo "Fall-only timeline reports: $RUN_ROOT/timeline_1"
echo "Fall-only three-year reports: $RUN_ROOT/three_year_1"
