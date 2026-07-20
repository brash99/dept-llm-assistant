# Benchmarking

Benchmarks are regression instruments for retrieval and decision-support behavior. They do not prove factual correctness or institutional decision readiness.

## Retrieval benchmarks

Current benchmark definitions live under:

```text
benchmarks/retrieval/v1.yaml
benchmarks/retrieval/v2.yaml
```

Run the current suite on the A100 production index:

```bash
cd /work/brash/dept-llm-assistant
.venv/bin/python -m scripts.run_retrieval_benchmark --benchmark retrieval/v2.yaml
```

The argument is relative to `benchmarks/`; the script’s legacy default filename does not match the current subdirectory layout, so pass it explicitly.

Inspect one case:

```bash
.venv/bin/python -m scripts.analyze_failure \
  --benchmark retrieval/v2.yaml \
  --case CASE_ID \
  --fetch-k 200
```

Benchmark output records required-source ranks, acceptable and bad results, reranker displacement, stage top results, timing, and the retrieval report. JSON logs are written under `storage/logs/`.

## Academic Workforce Planning regression

The canonical benchmark concerns reducing approximately 275 full-time faculty positions to approximately 250 and asks which departments should supply reductions. A safe result must:

- classify Academic Workforce Planning;
- classify institution-wide scope;
- avoid resolving lowercase `is` as Information Science;
- avoid selecting one academic unit or LLC node;
- treat self-studies as local institutional evidence rather than formal standards;
- prevent document-family repetition from inflating confidence;
- reject snapshots as Enrollment Trends;
- expose missing institution-wide staffing, demand, finance, and dependency evidence; and
- refuse departmental recommendations when evidence is insufficient.

Focused deterministic tests are listed in [Testing](../operations/testing.md).

## What to compare

For retrieval changes compare:

- raw, exact-deduped, reranked, diversified, thresholded, and final counts;
- required-source rank at each stage;
- document-family keys and removals;
- constitutional/empirical composition;
- evidence classes and roles; and
- latency by stage.

For Evidence Fitness changes compare:

- decision type and scope;
- eight canonical workforce domain grades;
- support score, source count, keyword breadth, and unique families;
- directness, scope, authority role, and coverage breadth;
- explicit limitations; and
- consistency between deterministic panels and narrative guidance.

## Interpretation

- A higher source count is not automatically better.
- Multiple files in one family are not independent evidence.
- A reranker improvement can still produce a poor evidence-role mix.
- A retrieved external standard can establish a constraint without establishing local compliance.
- One unit’s report cannot establish institution-wide comparative fitness.
- Full production validation requires the A100 environment, installed retrieval dependencies, and populated index.
