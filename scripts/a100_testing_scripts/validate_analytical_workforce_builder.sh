#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"
if [[ -z "${VIRTUAL_ENV:-}" ]]; then source .venv/bin/activate; fi
[[ "$(git branch --show-current)" == "sprint/academic-workforce-planning" ]] || { echo "Wrong branch" >&2; exit 2; }
RUN_ROOT="storage/logs/analytical_workforce_builder_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUN_ROOT"/{workforce_1,workforce_2,identity,appointments,metric_readiness,roster_readiness}
PYTHONPATH="$PWD" pytest -q scripts/test_analytical_workforce.py scripts/test_faculty_identity.py scripts/test_faculty_appointments.py scripts/test_authoritative_faculty_roster.py >"$RUN_ROOT/tests.log"
for run in 1 2; do
  PYTHONPATH="$PWD" python scripts/build_analytical_workforce.py --normalized-root storage/normalized --output-dir "$RUN_ROOT/workforce_$run" >"$RUN_ROOT/workforce_$run.log"
done
PYTHONPATH="$PWD" python scripts/audit_faculty_identity.py --normalized-root storage/normalized --output-dir "$RUN_ROOT/identity" >"$RUN_ROOT/identity.log"
PYTHONPATH="$PWD" python scripts/audit_faculty_appointments.py --normalized-root storage/normalized --output-dir "$RUN_ROOT/appointments" >"$RUN_ROOT/appointments.log"
PYTHONPATH="$PWD" python scripts/audit_metric_readiness.py --normalized-root storage/normalized --output-dir "$RUN_ROOT/metric_readiness" >"$RUN_ROOT/metric_readiness.log"
PYTHONPATH="$PWD" python scripts/audit_faculty_roster_readiness.py --output-dir "$RUN_ROOT/roster_readiness" >"$RUN_ROOT/roster_readiness.log"
PYTHONPATH="$PWD" python scripts/a100_testing_scripts/validate_analytical_workforce_builder.py --run-root "$RUN_ROOT"
echo "Reports: $RUN_ROOT"
