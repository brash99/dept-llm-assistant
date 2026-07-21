#!/usr/bin/env bash
set -euo pipefail

# Canonical A100 operator entry point for the bounded derived-data pipeline:
# normalized Knowledge Objects -> chunks -> embeddings -> FAISS -> validation.
# It does not normalize, classify with --apply, acquire evidence, or deploy ISO.

REPOSITORY_ROOT="${ISO_REPOSITORY_ROOT:-/work/brash/dept-llm-assistant}"
MODE="all"
RERANK=1

usage() {
  cat <<'EOF'
Usage: bash scripts/a100_rebuild_semantic_artifacts.sh [options]

Options:
  --dry-run       Run preflight, corpus checks, classification idempotence, and
                  pipeline rebuild preflight without changing derived artifacts.
  --skip-rerank   Skip GPU cross-encoder retrieval smoke tests after validation.
  -h, --help      Show this help.

Environment:
  ISO_REPOSITORY_ROOT  Repository root (default: /work/brash/dept-llm-assistant)
EOF
}

while (($#)); do
  case "$1" in
    --dry-run) MODE="dry-run" ;;
    --skip-rerank) RERANK=0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

cd "$REPOSITORY_ROOT"
if [[ ! -f .venv/bin/activate ]]; then
  echo "ERROR: virtual environment not found: $PWD/.venv" >&2
  exit 2
fi
# shellcheck disable=SC1091
source .venv/bin/activate
export PYTHONPATH="$PWD"

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="$PWD/storage/logs/a100_semantic_rebuild_${RUN_ID}"
export REPORT_DIR
mkdir -p "$REPORT_DIR"

echo "=== ISO A100 SEMANTIC PIPELINE ==="
echo "mode=$MODE"
echo "hostname=$(hostname)"
echo "repository=$PWD"
echo "branch=$(git branch --show-current)"
echo "commit=$(git log -1 --format='%H %s')"
echo "python=$(python3 --version 2>&1)"
echo "report_dir=$REPORT_DIR"

[[ "$(git branch --show-current)" == "sprint/academic-workforce-planning" ]] || {
  echo "ERROR: unexpected branch" >&2; exit 2;
}
git diff --quiet || { echo "ERROR: unstaged tracked changes exist" >&2; exit 2; }
git diff --cached --quiet || { echo "ERROR: staged changes exist" >&2; exit 2; }
echo "tracked_git_status=clean"
echo "untracked_entries=$(git status --porcelain | awk '$1=="??"{n++} END{print n+0}')"

nvidia-smi \
  --query-gpu=name,memory.total,memory.free,driver_version \
  --format=csv,noheader \
  | tee "$REPORT_DIR/gpu.txt"

python3 - <<'PY'
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.adapters.schedule_adapter import ScheduleCSVAdapter
from app.config import load_config

root = Path.cwd()
report_dir = Path(os.environ["REPORT_DIR"])
config = load_config()
configured_root = Path(config["project"]["root"]).resolve()
assert configured_root == root.resolve(), (
    f"Configured root {configured_root} does not match checkout {root.resolve()}"
)

storage = config["storage"]
root_keys = (
    "normalized", "constitutional", "schedule_observations",
    "faculty_observations", "catalog_observations",
)
ids = []
counts = {}
for key in root_keys:
    path = root / storage[key]
    assert path.is_dir(), f"Missing configured Knowledge Object root: {path}"
    files = list(path.rglob("*.json"))
    valid = 0
    for file in files:
        value = json.loads(file.read_text(encoding="utf-8"))
        object_id = value.get("id")
        assert object_id, f"Knowledge Object lacks id: {file}"
        ids.append(object_id)
        valid += 1
    counts[key] = {"path": str(path), "json": len(files), "valid": valid}

duplicate_ids = len(ids) - len(set(ids))
assert duplicate_ids == 0, f"Duplicate Knowledge Object IDs: {duplicate_ids}"

source = root / config["schedule_ingestion"]["canonical_source"]
expected_hash = "9ab803cc1715dd39a8ba8ba6890921ca04a1a8e0a20160dfcf785cc3de4aebc8"
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == expected_hash, f"Unexpected canonical schedule hash: {source_hash}"

schedule_root = root / storage["schedule_observations"]
schedule_files = list(schedule_root.rglob("*.json"))
assert len(schedule_files) == 18403, f"Expected 18,403 schedule objects; found {len(schedule_files)}"
stored = {}
for file in schedule_files:
    value = json.loads(file.read_text(encoding="utf-8"))
    stored[value["id"]] = value["repair"]["decision_fingerprint"]

preview = ScheduleCSVAdapter(source).adapt(
    timestamp=datetime(2026, 7, 21, tzinfo=timezone.utc)
)
computed = {item.id: item.repair["decision_fingerprint"] for item in preview.observations}
assert set(stored) == set(computed), "Schedule repair ID set differs from normalized corpus"
mismatches = sum(stored[key] != computed[key] for key in stored)
assert mismatches == 0, f"Schedule repair fingerprint mismatches: {mismatches}"

summary = {
    "configured_roots": counts,
    "logical_objects": len(ids),
    "duplicate_object_ids": duplicate_ids,
    "canonical_schedule_sha256": source_hash,
    "schedule_objects": len(schedule_files),
    "schedule_repair_fingerprint_mismatches": mismatches,
    "chunking": config["chunking"],
    "embedding": config["embedding"],
    "reranking": config["reranking"],
    "artifact_paths": {
        key: str(root / storage[key])
        for key in ("chunks", "embeddings", "vector_db")
    },
}
(report_dir / "corpus_preflight.json").write_text(
    json.dumps(summary, indent=2) + "\n", encoding="utf-8"
)
print("=== CORPUS PREFLIGHT ===")
for key, value in counts.items():
    print(f"{key}: json={value['json']:,} valid={value['valid']:,}")
print(f"logical_objects={len(ids):,} duplicate_ids=0")
print(f"schedule_objects={len(schedule_files):,} repair_fingerprint_mismatches=0")
print(f"embedding_model={config['embedding']['model']}")
print(f"embedding_device={config['embedding']['device']}")
PY

CLASS_REPORT="$REPORT_DIR/classification_idempotence"
python3 scripts/classify_knowledge_corpus.py \
  --dry-run \
  --report-dir "$CLASS_REPORT" \
  >"$REPORT_DIR/classification_idempotence.log" 2>&1

python3 - <<'PY'
import json
import os
from pathlib import Path

value = json.loads(
    (Path(os.environ["REPORT_DIR"]) /
     "classification_idempotence/classification_summary.json").read_text()
)["overall"]
for key in ("changed", "failed", "conflicted", "reviewed"):
    assert value[key] == 0, f"Classification idempotence failed: {key}={value[key]}"
print(
    "classification_idempotence="
    f"processed:{value['processed']:,} changed:0 conflicts:0 reviews:0 failures:0"
)
PY

python3 scripts/semantic_pipeline.py status --json \
  >"$REPORT_DIR/pipeline_status_before.json"
python3 scripts/semantic_pipeline.py rebuild --dry-run --json \
  >"$REPORT_DIR/rebuild_dry_run.json"

python3 - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["REPORT_DIR"])
value = json.loads((root / "rebuild_dry_run.json").read_text())
assert value.get("mutations_performed") is False
assert not value.get("configuration_conflicts"), value.get("configuration_conflicts")
assert all(value.get("dependencies", {}).values()), value.get("dependencies")
print(
    "pipeline_preflight="
    f"objects:{value['normalized_object_count']:,} "
    f"model:{value['embedding_model']} device:{value['embedding_device']} "
    f"free_disk_bytes:{value['free_disk_bytes']:,}"
)
if value.get("incomplete_staging_runs"):
    raise SystemExit(
        "Incomplete staging runs require inspection: "
        + ", ".join(value["incomplete_staging_runs"])
    )
PY

if [[ "$MODE" == "dry-run" ]]; then
  echo "DRY_RUN_COMPLETE report_dir=$REPORT_DIR"
  exit 0
fi

if pgrep -af 'streamlit|web_app.py' >"$REPORT_DIR/running_application_processes.txt"; then
  echo "ERROR: stop ISO/Streamlit before rebuilding" >&2
  cat "$REPORT_DIR/running_application_processes.txt"
  exit 2
fi

echo "=== STAGED REBUILD ==="
python3 scripts/semantic_pipeline.py rebuild --json \
  >"$REPORT_DIR/rebuild.json" \
  2>"$REPORT_DIR/rebuild.stderr.log"

python3 scripts/semantic_pipeline.py verify --json \
  >"$REPORT_DIR/pipeline_verification.json"
python3 scripts/validate_vector_db.py --sample-size 5000 --json \
  >"$REPORT_DIR/vector_db_validation.json"
python3 scripts/report_vector_db_inventory.py --top 12 --json \
  >"$REPORT_DIR/vector_db_inventory.json"

python3 - <<'PY'
import json
import os
import pickle
from collections import Counter, defaultdict
from pathlib import Path

from app.config import load_config

report_dir = Path(os.environ["REPORT_DIR"])
pipeline = json.loads((report_dir / "pipeline_verification.json").read_text())
vector = json.loads((report_dir / "vector_db_validation.json").read_text())
assert pipeline["valid"], pipeline["errors"]
assert vector["valid"], vector["errors"]
assert pipeline["chunk_count"] == pipeline["embedding_count"]
assert pipeline["embedding_count"] == pipeline["vector_count"]
assert pipeline["vector_count"] == pipeline["metadata_record_count"]

config = load_config()
project_root = Path(config["project"]["root"])
schedule_root = project_root / config["storage"]["schedule_observations"]
chunks_root = project_root / config["storage"]["chunks"]
vector_root = project_root / config["storage"]["vector_db"]
overall = Counter()
unresolved_by_term = Counter()
cpsc = defaultdict(Counter)
sec_subjects = Counter()
temporal = Counter()
schedule_objects = {}
selected_terms = {"2021_fall", "2022_fall", "2023_fall", "2024_fall", "2025_fall"}
sec_prefixes = {"PHYS", "CPSC", "CYBR", "IS", "CPEN", "EENG"}

def term_key(term):
    year, label = term.split("_", 1)
    order = {"spring": 10, "may": 20, "summer_1": 30,
             "extended_summer": 35, "summer_2": 40, "fall": 50}
    return int(year), order.get(label, 0)

total = 0
for path in schedule_root.rglob("*.json"):
    value = json.loads(path.read_text(encoding="utf-8"))
    schedule_objects[value["id"]] = value
    total += 1
    instructor_type = value.get("instructor_type") or {}
    if instructor_type.get("conflicting"):
        category = "unresolved_conflict"
        unresolved_by_term[value["academic_term"]] += 1
    else:
        category = instructor_type.get("normalized_value", "unknown")
    overall[category] += 1
    if value.get("subject") == "CPSC" and value["academic_term"] in selected_terms:
        cpsc[value["academic_term"]][category] += 1
    if value.get("subject") in sec_prefixes:
        sec_subjects[value["subject"]] += 1
    key = term_key(value["academic_term"])
    if key < (2026, 30):
        temporal["historical_or_completed"] += 1
    elif key <= (2026, 40):
        temporal["current_or_planned_summer_2026"] += 1
    else:
        temporal["future_or_planned"] += 1

# Verify every schedule object has exactly one chunk and that the factual
# metadata currently supported by app.chunk survives unchanged. The full
# repair assertion remains in the normalized object and is deliberately
# reported as not propagated by the current chunk contract.
schedule_chunks = {}
edward_chunks = []
for path in chunks_root.glob("*.json"):
    items = json.loads(path.read_text(encoding="utf-8"))
    for item in items:
        object_id = item.get("knowledge_object_id")
        if object_id in schedule_objects:
            assert object_id not in schedule_chunks, (
                f"Schedule object has multiple primary chunks: {object_id}"
            )
            schedule_chunks[object_id] = item
        metadata = item.get("metadata") or {}
        if metadata.get("display_name") == "Edward Brash":
            edward_chunks.append(item)
assert set(schedule_chunks) == set(schedule_objects), (
    "Schedule Knowledge Object/chunk ID sets differ"
)

conflicted_count = 0
for object_id, value in schedule_objects.items():
    chunk_metadata = schedule_chunks[object_id].get("metadata") or {}
    instructor_type = value.get("instructor_type") or {}
    expected = {
        "term": value.get("academic_term"),
        "term_published": value.get("academic_term_published"),
        "course_code": value.get("course_code"),
        "section": value.get("section"),
        "instructor_text": value.get("instructor_raw"),
        "instructor_type": instructor_type.get("normalized_value"),
    }
    for key, expected_value in expected.items():
        if expected_value not in (None, ""):
            assert chunk_metadata.get(key) == expected_value, (
                f"Schedule metadata mismatch for {object_id}: {key}"
            )
    identity_text = json.dumps(
        chunk_metadata.get("semantic_identity") or {}, sort_keys=True
    ).casefold()
    assert "employment_status" not in identity_text
    assert "faculty_employment" not in identity_text
    if instructor_type.get("conflicting"):
        conflicted_count += 1
        assert instructor_type.get("normalized_value") == "unknown"
        assert chunk_metadata.get("instructor_type") == "unknown"

with (vector_root / "records.pkl").open("rb") as handle:
    records = pickle.load(handle)
schedule_index = {
    item.get("knowledge_object_id"): item
    for item in records
    if item.get("knowledge_object_id") in schedule_objects
}
assert set(schedule_index) == set(schedule_objects), (
    "Schedule Knowledge Object/index-record ID sets differ"
)
for object_id, chunk in schedule_chunks.items():
    assert (schedule_index[object_id].get("metadata") or {}).get("instructor_type") == (
        chunk.get("metadata") or {}
    ).get("instructor_type"), f"Schedule instructor type lost in index: {object_id}"

# Governed SEC ontology check using Edward Brash as a representative faculty
# observation. No disciplinary specialty may be invented as a formal home.
assert edward_chunks, "No Edward Brash faculty chunk found"
edward_identity = (edward_chunks[0].get("metadata") or {}).get("semantic_identity") or {}
entities = edward_identity.get("institutional_entities") or []
sec_entities = [item for item in entities if item.get("entity_id") == "academic_unit:sec"]
assert len(sec_entities) == 1, "Edward Brash must resolve to exactly one SEC entity"
sec = sec_entities[0]
assert sec.get("entity_type") == "school"
assert sec.get("formal_unit_type") == "dependent_school"
roles = set(sec.get("operational_roles") or [])
assert {"department_equivalent", "faculty_home_unit", "workforce_allocation_unit"} <= roles
assert not any(
    item.get("entity_type") == "department"
    and any(term in str(item.get("published_name", "")).casefold()
            for term in ("physics", "computer science"))
    for item in entities
), "Invented Physics/Computer Science department membership for Edward Brash"
assert "instructor_type" not in (edward_chunks[0].get("metadata") or {})

usable = overall["full_time"] + overall["adjunct"]
sanity = {
    "overall": dict(overall),
    "direct_usable": usable,
    "total": total,
    "direct_usable_percentage": 100.0 * usable / total,
    "temporal": dict(temporal),
    "unresolved_by_term": dict(sorted(unresolved_by_term.items(), key=lambda x: term_key(x[0]))),
    "selected_cpsc_terms": {key: dict(value) for key, value in sorted(cpsc.items(), key=lambda x: term_key(x[0]))},
    "sec_related_subjects": dict(sec_subjects),
}
(report_dir / "schedule_sanity.json").write_text(
    json.dumps(sanity, indent=2) + "\n", encoding="utf-8"
)
print("=== STRUCTURAL VALIDATION ===")
print(
    f"objects={pipeline['normalized_object_count']:,} "
    f"chunks={pipeline['chunk_count']:,} "
    f"embeddings={pipeline['embedding_count']:,} "
    f"faiss={pipeline['vector_count']:,} "
    f"records={pipeline['metadata_record_count']:,}"
)
print(
    f"embedding_dimension={pipeline['embedding_dimension']} "
    f"model={pipeline['embedding_model']} errors=0"
)
print("=== SCHEDULE SANITY ===")
print(f"overall={dict(sorted(overall.items()))}")
print(f"direct_usable={usable:,}/{total:,} ({100.0*usable/total:.2f}%)")
print(f"temporal={dict(sorted(temporal.items()))}")
print(f"unresolved_by_term={sanity['unresolved_by_term']}")
print(f"selected_CPSC_terms={sanity['selected_cpsc_terms']}")
print(f"SEC_related_subjects={dict(sorted(sec_subjects.items()))}")
print("=== METADATA PROPAGATION ===")
print(
    f"schedule_objects_checked={len(schedule_objects):,} "
    f"schedule_chunks_checked={len(schedule_chunks):,} "
    f"schedule_index_records_checked={len(schedule_index):,}"
)
print(f"unresolved_source_conflicts_preserved={conflicted_count:,}")
print("schedule_repair_payload_in_chunks=no (normalized-object-only by current contract)")
print(
    "SEC=dependent_school roles="
    + ",".join(sorted(roles))
    + " invented_disciplinary_departments=0"
)
PY

if (( RERANK )); then
  python3 - <<'PY' >"$REPORT_DIR/retrieval_smoke.log"
from pathlib import Path

from app.config import load_config
from app.retrieval import retrieve
from app.vector_index import clear_runtime_caches

config = load_config()
root = Path(config["project"]["root"])
embedding = config["embedding"]
reranking = config["reranking"]
retrieval = config["retrieval"]
queries = (
    "Edward Brash faculty affiliation and research interests",
    "organizational status of the School of Engineering and Computing",
    "adjunct CPSC sections in Fall 2023",
    "sections with conflicting Instructor Type",
    "evidence relevant to the Physics major",
    "CNU Strategic Compass and faculty allocation",
    "historical freshman profile evidence",
)
clear_runtime_caches()
print("=== RETRIEVAL SMOKE TESTS ===")
for query in queries:
    constitutional = 2 if "Strategic Compass" in query else 0
    results, _, _, _ = retrieve(
        query=query,
        vector_db_dir=root / config["storage"]["vector_db"],
        model_name=embedding["model"], device=embedding["device"],
        top_k=5, fetch_k=200, dedupe_by="text", rerank=True,
        reranker_model=reranking["model"],
        reranker_device=reranking["device"],
        min_rerank_score=reranking.get("min_score"), return_trace=True,
        constitutional_top_k=constitutional, empirical_top_k=5-constitutional,
        max_per_document_family=retrieval["max_per_document_family"],
        max_per_evidence_role=retrieval["max_per_evidence_role"],
        evidence_role_relevance_margin=retrieval["evidence_role_relevance_margin"],
    )
    assert results, f"No results: {query}"
    print(f"\nQUERY: {query}")
    for rank, result in enumerate(results[:5], 1):
        metadata = result.metadata or {}
        citation = result.citation or {}
        title = citation.get("title") or metadata.get("document_title") or result.knowledge_object_id
        source = citation.get("relative_path") or citation.get("source_path") or metadata.get("relative_path") or "<unknown>"
        faiss_score = metadata.get("faiss_score")
        rerank_score = metadata.get("rerank_score", result.score)
        print(
            f"  {rank}. {str(title)[:80]} | type={result.object_type} | "
            f"semantic={metadata.get('semantic_space', '<missing>')} | "
            f"source={str(source)[:80]} | faiss={faiss_score if faiss_score is not None else 'n/a'} | "
            f"rerank={rerank_score:.4f}"
        )
PY
  cat "$REPORT_DIR/retrieval_smoke.log"
  python3 scripts/run_retrieval_smoke_tests.py --rerank \
    >"$REPORT_DIR/declarative_retrieval_smoke.log" 2>&1
  tail -n 40 "$REPORT_DIR/declarative_retrieval_smoke.log"
else
  echo "reranked_retrieval_smoke=skipped"
fi

echo "PIPELINE_COMPLETE report_dir=$REPORT_DIR"
