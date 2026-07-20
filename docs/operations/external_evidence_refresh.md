# External Evidence Refresh Runbook

This is the standard manual workflow for refreshing curated external evidence
until an automated pipeline is intentionally implemented. Run it on the A100
server from the canonical checkout:

```bash
cd /work/brash/dept-llm-assistant
mkdir -p storage/logs
```

The Health Physics pilot uses 13 explicit registry resources across ABET,
ORISE, BLS, O*NET, NRC, DOE, and SCHEV. It performs no search or crawling.

## 1. Review the deterministic plan

```bash
.venv/bin/python scripts/acquire_external_evidence.py \
  --decision-type academic_program \
  --decision-label "Health Physics" \
  --missing-domain Curriculum \
  --missing-domain Faculty \
  --missing-domain Facilities \
  --missing-domain Equipment \
  --missing-domain Accreditation \
  --missing-domain Budget \
  --missing-domain "Enrollment / Demand" \
  --missing-domain "Strategic Planning" \
  --missing-domain "Historical Precedent" \
  | tee storage/logs/health_physics_external_acquisition_dry_run.log
```

Confirm that every domain is mapped, the authority list is expected, and the
report says `Validation Status: Pending`. This command performs no retrieval.

## 2. Execute acquisition, validation, and promotion

```bash
.venv/bin/python scripts/acquire_external_evidence.py \
  --decision-type academic_program \
  --decision-label "Health Physics" \
  --missing-domain Curriculum \
  --missing-domain Faculty \
  --missing-domain Facilities \
  --missing-domain Equipment \
  --missing-domain Accreditation \
  --missing-domain Budget \
  --missing-domain "Enrollment / Demand" \
  --missing-domain "Strategic Planning" \
  --missing-domain "Historical Precedent" \
  --execute \
  | tee storage/logs/health_physics_external_acquisition.log
```

The CLI report is stdout; `tee` above is the persisted acquisition report.
Inspect it with:

```bash
less storage/logs/health_physics_external_acquisition.log
```

Review `Staged`, `Validated`, `Promoted`, and every `INVALID` line. A repeated
unchanged acquisition is intentionally not promoted again.

## 3. Inspect staging and provenance

```bash
find storage/external_staging -type f \
  ! -name '*.provenance.json' \
  ! -name 'external_manifest.jsonl' \
  -print | sort

find storage/external_staging -type f \
  -name '*.provenance.json' -print | sort
```

The manifest is JSON Lines. Inspect each record with:

```bash
while IFS= read -r record; do
  printf '%s\n' "$record" | .venv/bin/python -m json.tool
done < storage/external_staging/external_manifest.jsonl
```

Inspect all provenance sidecars:

```bash
find storage/external_staging -type f -name '*.provenance.json' \
  -exec .venv/bin/python -m json.tool {} \;
```

## 4. Inspect promoted Knowledge Objects

```bash
rg -l '"kind": "curated_external"' storage/normalized/*.json | sort

rg -l '"kind": "curated_external"' storage/normalized/*.json | wc -l
```

Inspect one or all promoted objects:

```bash
rg -l '"kind": "curated_external"' storage/normalized/*.json \
  | while IFS= read -r object; do
      .venv/bin/python -m json.tool "$object"
    done
```

Confirm `external_provenance`, `authority_class`, `evidence_role`,
`evidence_domains`, `canonical_url`, version, effective period, and retrieval
timestamp.

## 5. Clear derived outputs for a complete rebuild

Promotion changes `storage/normalized` only. Chunk, embedding, and vector-index
rebuilds are manual. Newly promoted evidence cannot participate in retrieval
until all three have completed.

Chunk and embedding scripts overwrite current files but do not remove outputs
belonging to superseded Knowledge Object IDs. Clear only these derived outputs:

```bash
mkdir -p storage/chunks storage/embeddings storage/vector_db
find storage/chunks -maxdepth 1 -type f -name '*.json' -delete
find storage/embeddings -maxdepth 1 -type f -name '*.json' -delete
find storage/vector_db -maxdepth 1 -type f \
  \( -name 'index.faiss' -o -name 'records.pkl' -o -name 'metadata.json' \) \
  -delete
```

Do **not** clear `storage/normalized`; that would delete the promoted external
Knowledge Objects. No model-download cache needs clearing. Stop any running
Streamlit process before rebuilding so it cannot retain the old in-memory
FAISS index.

## 6. Rebuild chunks

```bash
.venv/bin/python -m scripts.chunk_documents --limit 1000000
```

The command prints the total chunk count and writes a timestamped report under
`storage/logs/chunking_*.json`. Inspect the newest report:

```bash
ls -1t storage/logs/chunking_*.json | head -1
jq . "$(ls -1t storage/logs/chunking_*.json | head -1)"
```

Count chunks carrying external provenance:

```bash
jq -s 'map(map(select(.metadata.external_provenance != null)) | length) | add' \
  storage/chunks/*.json
```

## 7. Rebuild embeddings

```bash
.venv/bin/python -m scripts.embed_chunks \
  --limit 1000000 \
  --embedding-context title_path
```

The command prints embedded chunk count and writes
`storage/logs/embedding_*.json`:

```bash
jq . "$(ls -1t storage/logs/embedding_*.json | head -1)"
```

## 8. Rebuild and inspect the FAISS index

```bash
.venv/bin/python -m scripts.build_vector_index
jq . storage/vector_db/metadata.json
```

`num_vectors` should equal the total successfully embedded chunks. The builder
overwrites the three vector-database files but does not notify already running
processes. Benchmark scripts start a fresh process automatically; restart
Streamlit before interactive validation.

## 9. Run deterministic Health Physics regressions

```bash
.venv/bin/python -m pytest -q scripts/test_external_evidence_acquisition.py
.venv/bin/python -m pytest -q \
  scripts/test_awp_stabilization.py -k health_physics

.venv/bin/python scripts/test_academic_workforce_planning.py
```

These verify contracts and pipeline integration without calling the production
LLM. They are not a substitute for the production benchmark.

## 10. Run the production Health Physics benchmark

The repository currently has no Health Physics benchmark CLI or output-file
serializer. Run it through the implemented Streamlit Decision Brief workflow:

```bash
source .venv/bin/activate
streamlit run web_app.py
```

Open the displayed Streamlit URL, select **Decision Brief**, and submit the
exact `HEALTH_PHYSICS_BENCHMARK` text in
`scripts/test_awp_stabilization.py`. The result is rendered in the browser; it
is not automatically written to disk. Enable Developer Mode to inspect the
retrieval report, stage counts, document-family diversity, final sources, and
timing.

Confirm that newly promoted external sources appear with their explicit
authority and evidence roles, that Constitutional Orientation remains separate,
and that the recommendation strength remains governed by current Evidence
Fitness rather than source quantity alone.
