# Testing and Validation

> **Status:** Current operational reference, synchronized July 23, 2026.

Run tests in the environment whose behavior is being validated. Mac tests
verify code and bounded checked-in evidence. A100 validation verifies the
current production checkout and production evidence.

## Standard Mac checks

```bash
cd /Users/brash/dept-llm-assistant
source .venv/bin/activate
set -euo pipefail

PYTHONPATH="$PWD" python -m pytest -q
PYTHONPATH="$PWD" python -m compileall -q app scripts
git diff --check
```

Do not report the full suite as passing when only a focused subset ran. FAISS,
sentence-transformer, cross-encoder, GPU, or local-LLM behavior must be tested
with the real production dependencies before deployment.

## Focused semantic and workforce validation

### Institutional units and subject ownership

```bash
PYTHONPATH="$PWD" python -m pytest -q \
  scripts/test_institutional_units.py \
  scripts/test_subject_ownership.py \
  scripts/test_subject_crosswalk_audit.py \
  scripts/test_subject_mapping_inventory.py
```

### Faculty identity and appointments

```bash
PYTHONPATH="$PWD" python -m pytest -q \
  scripts/test_faculty_identity.py \
  scripts/test_faculty_identity_review.py \
  scripts/test_faculty_appointments.py
```

### Authoritative roster contract

```bash
PYTHONPATH="$PWD" python -m pytest -q \
  scripts/test_authoritative_faculty_roster.py
```

This validates the future roster ingestion contract and synthetic fixtures. It
does not assert that an authoritative production roster exists.

### Analytical workforce

```bash
PYTHONPATH="$PWD" python -m pytest -q \
  scripts/test_analytical_workforce.py \
  scripts/test_analytical_workforce_review.py \
  scripts/test_analytical_workforce_review_matrix.py
```

### Department profiles, SCH, and attribution

```bash
PYTHONPATH="$PWD" python -m pytest -q \
  scripts/test_department_profiles.py \
  scripts/test_sch_completeness.py \
  scripts/test_department_sch_timeline.py \
  scripts/test_department_three_year_sch.py \
  scripts/test_faculty_delivered_sch.py
```

### LLC designation governance

```bash
PYTHONPATH="$PWD" python -m pytest -q \
  scripts/test_llc_designations.py
```

### Undergraduate majors, capstones, and estimated graduates

```bash
PYTHONPATH="$PWD" python -m pytest -q \
  scripts/test_undergraduate_majors.py \
  scripts/test_undergraduate_major_capstones.py \
  scripts/test_estimated_graduates.py
```

## Schedule evidence

Schedule ingestion and analysis have separate focused coverage:

```bash
PYTHONPATH="$PWD" python -m pytest -q \
  scripts/test_schedule_adapter.py \
  scripts/test_authoritative_schedule_adapter.py \
  scripts/test_schedule_analysis.py \
  scripts/test_schedule_repair.py
```

Teaching assignments remain distinct from appointment and workforce evidence.
Tests must not silently use schedule participation as proof of employment.

## Durable A100 validation

Substantial production validation logic belongs in committed scripts under
`scripts/a100_testing_scripts/`. Prefer a short invocation of a reviewed script
to pasting a long Python heredoc or thousands of terminal lines into a
conversational interface.

Current durable entry points include:

```bash
bash scripts/a100_testing_scripts/validate_faculty_identity_governance_precedence.sh
bash scripts/a100_testing_scripts/validate_analytical_workforce_builder.sh
bash scripts/a100_testing_scripts/validate_department_profiles.sh
bash scripts/a100_testing_scripts/build_department_sch_timeline.sh
bash scripts/a100_testing_scripts/build_department_sch_fall_only.sh
bash scripts/a100_testing_scripts/build_department_three_year_sch.sh
bash scripts/a100_testing_scripts/build_faculty_delivered_sch.sh
```

The usual A100 sequence is:

```bash
cd /work/brash/dept-llm-assistant
source .venv/bin/activate
git pull --ff-only origin sprint/academic-workforce-planning
bash scripts/a100_testing_scripts/validate_department_profiles.sh
```

Choose the entry point appropriate to the capability under review. Validation
scripts should write timestamped artifacts under `storage/logs`, print compact
summaries, enforce deterministic fingerprints, and fail on broken invariants.

## Interpreting evidence environments

Governed normalized evidence may exist and be tracked on the Mac. It may still
differ from current A100 evidence because of acquisition time, local generated
artifacts, or a branch mismatch.

Before making a production claim, verify:

- branch and commit;
- source and normalized evidence inventories;
- invalid-record counts;
- deterministic fingerprints; and
- the production validator’s invariants.

Local synthetic fixtures prove deterministic behavior, not production counts.
