# July 2026 Major-Capstone Experiment Baseline

This directory preserves the generated outputs and forensic notes delivered
with the first governed undergraduate-major, major-to-capstone, and
capstone-enrollment graduate-estimate experiment.

## Provenance

- Producing commit:
  `a94f7f3e8fd46dfb5a191677673bd38c1484cae3`
  (`Add governed major capstone graduate estimates`)
- Evidence inputs:
  `config/undergraduate_majors.yaml`,
  `config/undergraduate_major_capstones.yaml`, and the normalized schedule
  evidence available when the commit was produced
- Purpose: preserve the July 2026 baseline as a reviewable milestone artifact;
  these files are not runtime inputs or authoritative graduation records.

## Reproduction

From the repository root with the project environment activated:

```bash
python scripts/audit_undergraduate_major_capstones.py \
  --output-dir reports/baselines/2026-07-major-capstone-experiment

python scripts/build_estimated_graduates.py \
  --normalized-root storage/normalized \
  --output-dir reports/baselines/2026-07-major-capstone-experiment
```

The ownership-forensics files are preserved investigation records. They were
assembled from the governed major registry and catalog evidence and do not
have a standalone generator.
