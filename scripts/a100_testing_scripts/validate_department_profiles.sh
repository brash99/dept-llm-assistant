#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"
if [[ -z "${VIRTUAL_ENV:-}" ]]; then source .venv/bin/activate; fi
[[ "$(git branch --show-current)" == "sprint/academic-workforce-planning" ]] || { echo "Wrong branch" >&2; exit 2; }
RUN_ROOT="storage/logs/department_profiles_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUN_ROOT"/{workforce,profiles_1,profiles_2,coverage,sch_completeness_1,sch_completeness_2,sch_timeline,sch_three_year}
PYTHONPATH="$PWD" pytest -q scripts/test_department_profiles.py scripts/test_department_instructional_coverage.py scripts/test_sch_completeness.py scripts/test_analytical_workforce.py scripts/test_subject_ownership.py scripts/test_institutional_units.py >"$RUN_ROOT/tests.log"
PYTHONPATH="$PWD" python scripts/build_analytical_workforce.py --normalized-root storage/normalized --output-dir "$RUN_ROOT/workforce" >"$RUN_ROOT/workforce.log"
for run in 1 2; do
  PYTHONPATH="$PWD" python scripts/build_department_profiles.py --normalized-root storage/normalized --workforce-output "$RUN_ROOT/workforce" --output-dir "$RUN_ROOT/profiles_$run" >"$RUN_ROOT/profiles_$run.log"
done
PYTHONPATH="$PWD" python scripts/audit_department_instructional_coverage.py --normalized-root storage/normalized --workforce-output "$RUN_ROOT/workforce" --profiles-output "$RUN_ROOT/profiles_1" --output-dir "$RUN_ROOT/coverage" >"$RUN_ROOT/coverage.log"
for run in 1 2; do
  PYTHONPATH="$PWD" python scripts/audit_sch_completeness.py --normalized-root storage/normalized --workforce-output "$RUN_ROOT/workforce" --profiles-output "$RUN_ROOT/profiles_1" --output-dir "$RUN_ROOT/sch_completeness_$run" >"$RUN_ROOT/sch_completeness_$run.log"
done
PYTHONPATH="$PWD" python scripts/build_department_sch_timeline.py --normalized-root storage/normalized --workforce-output "$RUN_ROOT/workforce" --profiles-output "$RUN_ROOT/profiles_1" --output-dir "$RUN_ROOT/sch_timeline" >"$RUN_ROOT/sch_timeline.log"
PYTHONPATH="$PWD" python scripts/build_department_three_year_sch.py --timeline "$RUN_ROOT/sch_timeline/department_sch_timeline.json" --output-dir "$RUN_ROOT/sch_three_year" >"$RUN_ROOT/sch_three_year.log"
PYTHONPATH="$PWD" python scripts/a100_testing_scripts/validate_department_profiles.py --run-root "$RUN_ROOT"
echo "Reports: $RUN_ROOT"
