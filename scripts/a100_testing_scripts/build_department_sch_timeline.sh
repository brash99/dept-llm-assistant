#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  source .venv/bin/activate
fi

RUN_ROOT="storage/logs/department_sch_timeline_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUN_ROOT"/{workforce,profiles,timeline_1,timeline_2}

PYTHONPATH="$PWD" pytest -q \
  scripts/test_department_sch_timeline.py \
  scripts/test_department_profiles.py \
  scripts/test_sch_completeness.py

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
    --output-dir "$RUN_ROOT/timeline_$run" \
    >"$RUN_ROOT/timeline_$run.log"
done

diff -qr "$RUN_ROOT/timeline_1" "$RUN_ROOT/timeline_2"

python - "$RUN_ROOT" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
payload = json.loads(
    (root / "timeline_1/department_sch_timeline.json").read_text()
)
if payload["department_count"] != 18:
    raise SystemExit("Expected 18 department timelines")
for department in payload["departments"]:
    terms = department["terms"]
    years = department["academic_years"]
    grand = department["grand_total"]
    if sum(item["sections"] for item in terms) != grand["sections"]:
        raise SystemExit(f"Term section mismatch: {department['department_name']}")
    if sum(item["sch"] for item in years) != grand["sch"]:
        raise SystemExit(f"Academic-year SCH mismatch: {department['department_name']}")
summary = {
    "status": "passed",
    "department_count": payload["department_count"],
    "term_count": len(payload["terms"]),
    "first_term": payload["terms"][0],
    "last_term": payload["terms"][-1],
    "academic_years": payload["academic_years"],
    "deterministic_fingerprint": payload["deterministic_fingerprint"],
}
(root / "validation_summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n"
)
print(json.dumps(summary, indent=2, sort_keys=True))
PY

echo "Reports: $RUN_ROOT/timeline_1"
