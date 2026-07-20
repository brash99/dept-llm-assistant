# Testing and Validation

## Standard checks

Run from the repository root with the active environment’s Python interpreter:

```bash
python3 -m compileall -q app scripts
python3 -m pytest -q
git diff --check
```

On the A100, use `.venv/bin/python` instead of `python3` to guarantee the production environment.

## Academic Workforce Planning

Focused dashboard, evidence-map, participation, and stabilization coverage:

```bash
python3 -m pytest -q \
  scripts/test_academic_workforce_dashboard.py \
  scripts/test_academic_workforce_evidence_map.py \
  scripts/test_academic_workforce_participation.py \
  scripts/test_awp_stabilization.py
```

Decision-type and taxonomy executable:

```bash
python3 scripts/test_academic_workforce_planning.py
```

Related Semantic Control Plane and readiness coverage:

```bash
python3 -m pytest -q \
  scripts/test_institutional_orientation.py \
  scripts/test_dual_semantic_control_plane.py \
  scripts/test_decision_readiness_framework.py
```

The stabilization tests cover short-alias safety, institution-wide scope, document-family grouping, evidence roles, scope-aware Evidence Fitness, enrollment-trend semantics, topology summaries, prompt claim safety, and executive source labels.

## Dependency interpretation

- A test that exercises FAISS search, sentence-transformer embeddings, or cross-encoder reranking must run with those real modules before production deployment.
- Conditional test stubs allow deterministic presentation/contract coverage on a machine without optional GPU dependencies; they do not prove the production retrieval stack works.
- A local checkout with placeholder `storage/` files cannot validate the production index.

Never report the full suite as passing when only a focused subset ran.
