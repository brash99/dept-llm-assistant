#!/usr/bin/env bash
set -euo pipefail
echo "Step 1:"
echo "python scripts/review_analytical_workforce.py"
echo
echo "Step 2:"
echo "python scripts/apply_analytical_workforce_overrides.py"
echo
echo "Step 3:"
echo "bash scripts/a100_testing_scripts/validate_analytical_workforce_builder.sh"
