# Bounded Repository Cleanup

Date: 2026-07-23

This housekeeping change does not alter ISO architecture, ontology, evidence
or semantic models, registries, observables, APIs, or runtime behavior.

## Reviewed staged deletion

`faculty_semantic_inspection.txt` was a 20,771-line generated inspection dump
from production normalized evidence. It was added by commit `f82d54ae`, was
not referenced by repository code or documentation, contained machine-specific
A100 paths, and duplicated evidence retained elsewhere. Its previously staged
deletion is retained.

## Files removed

- 55 unreferenced source snapshots matching `*.bak`, `*.pre_*`,
  `*.before_*`, or `*.sprint*.bak`
- `structure.txt`, an obsolete manually maintained phase/sprint diagram with
  no generator or active reference

Git history and repository tags retain the historical source states represented
by the deleted snapshots.

## Files moved

- `Department_LLM_Assistant_Phase_II_Context.txt` moved from the repository
  root to `docs/archive/development_context/`. It remains useful as historical
  development context but is explicitly non-operational.
- Nine July 2026 major/capstone experiment outputs moved from the repository
  root to `reports/baselines/2026-07-major-capstone-experiment/`.
- A README in the baseline directory records the producing commit,
  reproduction commands, purpose, and limitations.

## Ignore rules added

The following source/editor snapshot patterns are now ignored:

```text
*~
*.bak
*.old
*.orig
*.rej
*.pre_*
*.before_*
*.sprint*.bak
```

## Broken-reference review

The removed backup files and generated faculty inspection had no active
references. Documentation was updated to point to the archived Phase II
context location.

## Deferred recommendations

The following higher-risk changes remain deliberately out of scope:

- decide whether the large normalized-evidence corpus should remain tracked;
- review generated site-map artifacts and experiment benchmarks;
- reorganize tests currently located under `scripts/`;
- classify and reorganize operational, audit, migration, and forensic scripts;
- establish a general retention policy for generated baseline reports;
- remove ignored local caches, reports, and runtime artifacts;
- review older reports and session notes for archival retention.
