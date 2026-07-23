#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  source .venv/bin/activate
fi

if [[ "$(git branch --show-current)" != "sprint/academic-workforce-planning" ]]; then
  echo "ERROR: expected sprint/academic-workforce-planning" >&2
  exit 2
fi

RUN_ROOT="storage/logs/faculty_identity_governance_precedence_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p \
  "$RUN_ROOT/identity_1" \
  "$RUN_ROOT/identity_2" \
  "$RUN_ROOT/appointments_1" \
  "$RUN_ROOT/appointments_2" \
  "$RUN_ROOT/metric_readiness" \
  "$RUN_ROOT/roster_readiness"

PYTHONPATH="$PWD" pytest -q \
  scripts/test_faculty_identity.py \
  scripts/test_faculty_appointments.py \
  scripts/test_authoritative_faculty_roster.py \
  >"$RUN_ROOT/focused_tests.log"

PYTHONPATH="$PWD" python scripts/audit_faculty_identity.py \
  --normalized-root storage/normalized \
  --output-dir "$RUN_ROOT/identity_1" \
  >"$RUN_ROOT/identity_1.log"
PYTHONPATH="$PWD" python scripts/audit_faculty_identity.py \
  --normalized-root storage/normalized \
  --output-dir "$RUN_ROOT/identity_2" \
  >"$RUN_ROOT/identity_2.log"

PYTHONPATH="$PWD" python scripts/audit_faculty_appointments.py \
  --normalized-root storage/normalized \
  --output-dir "$RUN_ROOT/appointments_1" \
  >"$RUN_ROOT/appointments_1.log"
PYTHONPATH="$PWD" python scripts/audit_faculty_appointments.py \
  --normalized-root storage/normalized \
  --output-dir "$RUN_ROOT/appointments_2" \
  >"$RUN_ROOT/appointments_2.log"

PYTHONPATH="$PWD" python scripts/audit_metric_readiness.py \
  --normalized-root storage/normalized \
  --output-dir "$RUN_ROOT/metric_readiness" \
  >"$RUN_ROOT/metric_readiness.log"
PYTHONPATH="$PWD" python scripts/audit_faculty_roster_readiness.py \
  --output-dir "$RUN_ROOT/roster_readiness" \
  >"$RUN_ROOT/roster_readiness.log"

PYTHONPATH="$PWD" python \
  scripts/a100_testing_scripts/validate_faculty_identity_governance_precedence.py \
  --run-root "$RUN_ROOT"

echo "Reports: $RUN_ROOT"
