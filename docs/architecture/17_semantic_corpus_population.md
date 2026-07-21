# Semantic Corpus Population

## Purpose

Semantic classification defines how a classifier proposes factual Semantic
Identity. Corpus population is the separate operational process that applies
that capability consistently to persisted Knowledge Objects.

```text
Configured Knowledge Object roots
        |
        v
recursive deterministic discovery
        |
        v
Semantic Classification
        |
        v
field-level policy evaluation
        |
        +--> review / abstain / conflict queues
        +--> deterministic audit sample
        |
        v
optional atomic application of accepted assertions
        |
        v
manifest and semantic coverage reports
```

This capability operates between the Semantic Layer and its downstream
consumers. It does not change retrieval, chunks, embeddings, vectors, Evidence
Fitness, Scenario Modeling, or the Institutional Digital Twin.

> Knowledge Objects store facts. Services derive meaning.

## Why population is separate from classification

A classifier operates on one Knowledge Object and produces a proposal. Policy
decides each assertion's disposition. Population adds operational concerns that
do not belong in either contract:

- deterministic recursive discovery;
- filtering and bounded runs;
- interruption and resume handling;
- atomic persistence;
- one manifest record per processed Knowledge Object;
- review, conflict, abstention, unsupported, and audit queues;
- aggregate coverage and workload reporting.

Keeping this boundary explicit allows classifiers and policy to be evaluated
without granting them permission to mutate the corpus.

## Inputs

With no `--input`, `scripts/classify_knowledge_corpus.py` reads all configured
normalized Knowledge Object roots from `config/settings.yaml`:

- `storage.normalized`;
- `storage.constitutional`;
- `storage.schedule_observations`;
- `storage.faculty_observations`;
- `storage.catalog_observations`.

An explicit `--input` overrides the defaults and may be repeated. Each input
may be a JSON Knowledge Object or a directory searched recursively. Resolved
paths are deduplicated and processed in stable lexical order.

Generic document objects currently have no deterministic semantic classifier.
They are reported as unsupported abstentions rather than assigned invented
identity. This is expected until an evaluated classifier exists for that
family.

## Dry-run first

Dry-run is the default and should precede every application run:

```bash
cd /work/brash/dept-llm-assistant
export PYTHONPATH="$PWD"

python3 scripts/classify_knowledge_corpus.py \
  --dry-run \
  --report-dir storage/reports/classification/dry-run
```

Dry-run loads and classifies real Knowledge Objects, evaluates policy, creates
an in-memory application preview, and reports whether Semantic Identity would
change. It never writes to the input object files.

Operators should inspect:

```text
classification_report.md
classification_summary.json
classification_manifest.jsonl
review_required.jsonl
conflicts.jsonl
abstentions.jsonl
unsupported_objects.jsonl
audit_sample.jsonl
```

Only after reviewing these outputs should an operator choose a separate apply
report directory and run:

```bash
python3 scripts/classify_knowledge_corpus.py \
  --apply \
  --report-dir storage/reports/classification/apply
```

The tool does not enforce a database-backed approval ceremony. Operational
discipline and preserved reports make the dry-run decision auditable.

## Filters and resume

Useful bounded operations include:

```bash
python3 scripts/classify_knowledge_corpus.py --dry-run --limit 100

python3 scripts/classify_knowledge_corpus.py \
  --dry-run \
  --object-type faculty_observation

python3 scripts/classify_knowledge_corpus.py \
  --dry-run \
  --knowledge-object-id OBJECT_ID

python3 scripts/classify_knowledge_corpus.py \
  --dry-run \
  --input data/normalized/faculty \
  --input data/normalized/schedules
```

`--resume` reads the existing manifest and skips completed Knowledge Object IDs
for the same mode. A dry-run record does not cause a later apply run to skip the
object. Resume appends new records and queue entries; summary metrics describe
the current resumed invocation and include a resumed count.

## Manifest

`classification_manifest.jsonl` contains one deterministic record per
successfully loaded, selected Knowledge Object. Records include:

- Knowledge Object ID and relative path;
- object type before and after;
- accepted, review, abstained, and conflicted assertions;
- audit flags;
- classifier names and versions;
- policy version;
- decision fingerprint;
- whether identity would change and whether application was requested;
- UTC run timestamp.

Ordering and classification content are deterministic for the same corpus,
policy, classifier versions, filters, and clock. Timestamps intentionally
identify the run.

## Review and exception queues

Queue entries contain the Knowledge Object ID, field, classifier, confidence,
reason, citations, and policy disposition.

- `review_required.jsonl` includes `review` and structurally rejected
  assertions requiring rule or evidence correction.
- `conflicts.jsonl` contains incompatible proposed or previously accepted
  factual values.
- `abstentions.jsonl` includes assertion-level and object-level abstentions.
- `unsupported_objects.jsonl` is the subset for which no classifier exists.
- `audit_sample.jsonl` contains deterministic samples of accepted assertions
  and explains each selection flag.

Empty queues are still created so absence is explicit rather than ambiguous.

## Safe application and provenance

Apply mode delegates merging to `ClassificationDecision`, so only
`auto_accept` and `accept_with_audit` assertions can enter Semantic Identity.
Review, abstained, rejected, and conflicted assertions remain unapplied.

Application:

- preserves existing Semantic Identity fields;
- unions multi-value entities, relationships, and decision domains;
- preserves Knowledge Object IDs;
- records accepted assertion values, methods, citations, classifier, and a
  deterministic decision fingerprint in `classification_provenance`;
- writes a temporary JSON file in the destination directory, flushes and
  synchronizes it, and atomically replaces the original;
- leaves no partial destination file when serialization or writing fails;
- is idempotent for an unchanged decision.

Raw acquisition evidence is never an input target and remains unchanged.

## Coverage reporting

The JSON and Markdown reports distinguish processed, classified, changed,
unchanged, unsupported, conflicted, reviewed, abstained, audited, failed, and
resumed counts. They also report:

- field coverage and policy dispositions;
- object-type coverage;
- classifier contribution;
- represented institutional entity types and IDs;
- audit selections and processing failures.

Field coverage is the share of classified objects whose post-policy preview
contains that Semantic Identity field. Zero coverage is reported as zero; it is
not filled with an inference.

## Current boundary

Version 1 runs only the registered deterministic classifiers. It provides no
bulk LLM workflow, generic-document classifier, semantic-membership derivation,
Question Interpreter, retrieval update, or automatic chunk/vector rebuild.
Populated identity will become operational for downstream services only when
those services are intentionally designed to consume it; this runner does not
silently change their behavior.
