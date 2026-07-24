"""Safe operations for ISO's normalized -> chunk -> embedding -> FAISS pipeline.

This module orchestrates existing builders. It does not normalize evidence,
classify Knowledge Objects, change retrieval scoring, or derive meaning.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import pickle
import shutil
import subprocess
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple
from uuid import uuid4

from app.config import load_config


MANIFEST_NAME = "semantic_pipeline_manifest.json"
INCOMPLETE_NAME = "incomplete_build.json"
SEMANTIC_FIELDS = (
    "source_family", "document_type", "institutional_role",
    "institutional_entities", "authority", "temporal_scope",
)
ROUTING_SELECTORS = {
    "cnu_institutional_research": {"source_family": "cnu_institutional_research"},
    "curated_external_evidence": {"source_family": "curated_external_evidence"},
    "schev_publications": {"source_family": "schev_publications"},
    "sec_annual_reports": {"source_family": "sec_google_drive", "institutional_role": "academic_unit_reporting_record"},
    "sec_planning": {"source_family": "sec_google_drive", "institutional_role": "academic_unit_planning_material"},
    "sec_program_review": {"source_family": "sec_google_drive", "institutional_role": "academic_program_review_evidence"},
    "sec_statistics": {"source_family": "sec_google_drive", "institutional_role": "academic_unit_operating_record"},
}


class ArtifactState(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    MISSING = "MISSING"
    INCONSISTENT = "INCONSISTENT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class PipelinePaths:
    repository_root: Path
    configured_root: Path
    normalized_roots: Tuple[Path, ...]
    chunks: Path
    embeddings: Path
    vector_db: Path
    staging_root: Path
    backup_root: Path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_root": str(self.repository_root),
            "configured_root": str(self.configured_root),
            "normalized_roots": [str(value) for value in self.normalized_roots],
            "chunks": str(self.chunks), "embeddings": str(self.embeddings),
            "vector_db": str(self.vector_db), "staging_root": str(self.staging_root),
            "backup_root": str(self.backup_root),
        }


@dataclass
class StageReport:
    state: ArtifactState
    reasons: list[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {"state": self.state.value, "reasons": self.reasons, "details": self.details}


@dataclass
class PipelineStatusReport:
    paths: PipelinePaths
    normalized: StageReport
    chunks: StageReport
    embeddings: StageReport
    vector_index: StageReport
    incomplete_staging_runs: Tuple[str, ...] = ()
    warnings: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "paths": self.paths.to_dict(), "normalized": self.normalized.to_dict(),
            "chunks": self.chunks.to_dict(), "embeddings": self.embeddings.to_dict(),
            "vector_index": self.vector_index.to_dict(),
            "incomplete_staging_runs": list(self.incomplete_staging_runs),
            "warnings": self.warnings,
        }


@dataclass
class VerificationReport:
    valid: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    normalized_object_count: int = 0
    chunk_file_count: int = 0
    chunk_count: int = 0
    embedding_file_count: int = 0
    embedding_count: int = 0
    embedding_dimension: Optional[int] = None
    embedding_model: Optional[str] = None
    vector_count: int = 0
    metadata_record_count: int = 0
    semantic_chunk_coverage: Dict[str, int] = field(default_factory=dict)
    semantic_index_coverage: Dict[str, int] = field(default_factory=dict)
    family_checks: Dict[str, Any] = field(default_factory=dict)
    vector_smoke_queries: int = 0

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class BuildHooks:
    chunk: Callable[..., Mapping[str, Any]]
    embed: Callable[..., Mapping[str, Any]]
    index: Callable[..., Mapping[str, Any]]


def resolve_pipeline_paths(config_path: Path | str = "config/settings.yaml") -> tuple[dict, PipelinePaths, list[str]]:
    config_path = Path(config_path).resolve()
    config = load_config(config_path)
    repository_root = config_path.parent.parent
    configured_root = Path(config["project"]["root"])
    warnings = []
    effective_root = configured_root
    if not configured_root.exists():
        effective_root = repository_root
        warnings.append(
            f"Configured project root {configured_root} is unavailable; using repository root {repository_root}."
        )
    storage = config["storage"]
    source_keys = ("normalized", "constitutional")
    roots = tuple(
        effective_root / storage[key] for key in source_keys if storage.get(key)
    )
    chunks = effective_root / storage["chunks"]
    embeddings = effective_root / storage["embeddings"]
    vector_db = effective_root / storage["vector_db"]
    common = Path(os.path.commonpath([str(chunks.parent), str(embeddings.parent), str(vector_db.parent)]))
    paths = PipelinePaths(
        repository_root=effective_root, configured_root=configured_root,
        normalized_roots=roots, chunks=chunks, embeddings=embeddings,
        vector_db=vector_db,
        staging_root=common / ".semantic_pipeline_staging",
        backup_root=common / ".semantic_pipeline_backups",
    )
    return config, paths, warnings


def default_build_hooks() -> BuildHooks:
    def chunk(**kwargs):
        from app.chunk import run_chunking
        return run_chunking(**kwargs)

    def embed(**kwargs):
        from app.embed import embed_chunks
        return embed_chunks(**kwargs)

    def index(**kwargs):
        from app.vector_index import build_faiss_index
        return build_faiss_index(**kwargs)

    return BuildHooks(chunk, embed, index)


class SemanticPipelineService:
    def __init__(
        self, config_path: Path | str = "config/settings.yaml", *,
        hooks: Optional[BuildHooks] = None,
        clock: Optional[Callable[[], datetime]] = None,
        run_id_factory: Optional[Callable[[], str]] = None,
        dependency_checker: Optional[Callable[[str], bool]] = None,
    ):
        self.config, self.paths, self.path_warnings = resolve_pipeline_paths(config_path)
        self.hooks = hooks or default_build_hooks()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.run_id_factory = run_id_factory or (
            lambda: self.clock().strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
        )
        self.dependency_checker = dependency_checker or (
            lambda name: importlib.util.find_spec(name) is not None
        )

    def status(self) -> PipelineStatusReport:
        normalized = _normalized_inventory(self.paths.normalized_roots)
        chunks = _chunk_inventory(self.paths.chunks)
        embeddings = _embedding_inventory(self.paths.embeddings, inspect_vectors=False)
        vector = _vector_inventory(self.paths.vector_db)
        manifest = _read_json(self.paths.vector_db / MANIFEST_NAME)
        _apply_freshness(normalized, chunks, embeddings, vector, manifest, self.config)
        incomplete = _incomplete_runs(self.paths.staging_root)
        return PipelineStatusReport(
            self.paths, normalized, chunks, embeddings, vector, incomplete,
            list(self.path_warnings),
        )

    def preflight(self, *, device: Optional[str] = None, embedding_context: str = "title_path") -> Dict[str, Any]:
        status = self.status()
        device = device or self.config.get("embedding", {}).get("device", "cuda")
        dependencies = {
            name: self.dependency_checker(name)
            for name in ("numpy", "faiss", "sentence_transformers")
        }
        targets = (self.paths.chunks, self.paths.embeddings, self.paths.vector_db)
        disk = shutil.disk_usage(self.paths.repository_root)
        filesystem_compatible = len({_device_id(path.parent) for path in targets}) == 1
        missing_roots = [str(path) for path in self.paths.normalized_roots if not path.exists()]
        return {
            "paths": self.paths.to_dict(),
            "status": status.to_dict(),
            "planned_stages": ["chunks", "embeddings", "vector_index", "verification"],
            "would_replace": [str(path) for path in targets if path.exists()],
            "would_backup": [str(path) for path in targets if path.exists()],
            "normalized_object_count": status.normalized.details.get("object_count", 0),
            "embedding_model": self.config.get("embedding", {}).get("model"),
            "embedding_device": device,
            "gpu_expected": str(device).casefold().startswith("cuda"),
            "embedding_context": embedding_context,
            "free_disk_bytes": disk.free,
            "dependencies": dependencies,
            "filesystem_compatible": filesystem_compatible,
            "incomplete_staging_runs": list(status.incomplete_staging_runs),
            "configuration_conflicts": (
                ([] if filesystem_compatible else ["Staging and targets are not on one filesystem."])
                + ([] if status.normalized.state == ArtifactState.CURRENT else ["Normalized Knowledge Object inputs are missing or unreadable."])
                + ([] if not missing_roots else ["Configured normalized roots are missing: " + ", ".join(missing_roots)])
            ),
            "mutations_performed": False,
        }

    def rebuild(
        self, *, dry_run: bool = False, device: Optional[str] = None,
        embedding_context: str = "title_path", cleanup_staging: bool = False,
    ) -> Dict[str, Any]:
        preflight = self.preflight(device=device, embedding_context=embedding_context)
        if dry_run:
            return {"mode": "dry_run", **preflight}
        missing = [name for name, present in preflight["dependencies"].items() if not present]
        if missing:
            raise RuntimeError("Missing rebuild dependencies: " + ", ".join(missing))
        if preflight["configuration_conflicts"]:
            raise RuntimeError("; ".join(preflight["configuration_conflicts"]))
        if preflight["incomplete_staging_runs"]:
            if not cleanup_staging:
                raise RuntimeError(
                    "Incomplete staging runs exist; inspect them or rerun with --cleanup-staging: "
                    + ", ".join(preflight["incomplete_staging_runs"])
                )
            _cleanup_incomplete_runs(self.paths.staging_root)

        run_id = self.run_id_factory()
        started = self.clock().isoformat()
        run_root = self.paths.staging_root / run_id
        staged = {
            "chunks": run_root / "chunks", "embeddings": run_root / "embeddings",
            "vector_db": run_root / "vector_db",
        }
        for path in staged.values():
            path.mkdir(parents=True, exist_ok=False)
        _write_json(run_root / INCOMPLETE_NAME, {"run_id": run_id, "started_at": started})

        chunk_cfg = self.config.get("chunking", {})
        embed_cfg = self.config.get("embedding", {})
        device = device or embed_cfg.get("device", "cuda")
        try:
            chunk_result = dict(self.hooks.chunk(
                source_dirs=self.paths.normalized_roots, chunks_dir=staged["chunks"],
                limit=None, chunk_size=chunk_cfg.get("chunk_size", 3000),
                overlap=chunk_cfg.get("overlap", 300),
                max_chunks_per_document=chunk_cfg.get("max_chunks_per_document"),
            ))
            if chunk_result.get("failed") or not chunk_result.get("total_chunks"):
                raise RuntimeError(f"Chunking failed validation: {chunk_result.get('errors', [])}")
            embed_result = dict(self.hooks.embed(
                chunks_dir=staged["chunks"], embeddings_dir=staged["embeddings"],
                model_name=embed_cfg.get("model"), batch_size=embed_cfg.get("batch_size", 32),
                device=device, limit=None, embedding_context=embedding_context,
            ))
            if embed_result.get("failed_files") or embed_result.get("total_chunks") != chunk_result.get("total_chunks"):
                raise RuntimeError(f"Embedding failed validation: {embed_result.get('errors', [])}")
            index_result = dict(self.hooks.index(
                embeddings_dir=staged["embeddings"], vector_db_dir=staged["vector_db"]
            ))
            verification = verify_pipeline(
                self.paths.normalized_roots, staged["chunks"], staged["embeddings"],
                staged["vector_db"], expected_model=embed_cfg.get("model"),
                required_semantic_selectors=ROUTING_SELECTORS,
            )
            if not verification.valid:
                raise RuntimeError("Staged verification failed: " + "; ".join(verification.errors))
            manifest = self._manifest(
                run_id, started, staged, chunk_result, embed_result,
                index_result, verification, device, embedding_context,
            )
            backup_paths = _promote(
                run_id, staged,
                {"chunks": self.paths.chunks, "embeddings": self.paths.embeddings, "vector_db": self.paths.vector_db},
                self.paths.backup_root,
                before_promotion=lambda backups: _write_json(
                    staged["vector_db"] / MANIFEST_NAME,
                    {**manifest, "backup_paths": {key: str(value) for key, value in backups.items()}},
                ),
            )
            marker = run_root / INCOMPLETE_NAME
            marker.unlink(missing_ok=True)
            if run_root.exists() and not any(run_root.iterdir()):
                run_root.rmdir()
            post = verify_pipeline(
                self.paths.normalized_roots, self.paths.chunks, self.paths.embeddings,
                self.paths.vector_db, expected_model=embed_cfg.get("model"),
                required_semantic_selectors=ROUTING_SELECTORS,
            )
            if not post.valid:
                _rollback(
                    {"chunks": self.paths.chunks, "embeddings": self.paths.embeddings, "vector_db": self.paths.vector_db},
                    backup_paths,
                )
                raise RuntimeError("Post-promotion verification failed; previous artifacts restored: " + "; ".join(post.errors))
            return {
                "mode": "rebuild", "run_id": run_id, "manifest": str(self.paths.vector_db / MANIFEST_NAME),
                "backup_paths": {key: str(value) for key, value in backup_paths.items()},
                "verification": post.to_dict(),
            }
        except Exception:
            # The marker and staged outputs intentionally remain for diagnosis.
            raise

    def verify(self) -> VerificationReport:
        return verify_pipeline(
            self.paths.normalized_roots, self.paths.chunks, self.paths.embeddings,
            self.paths.vector_db,
            expected_model=self.config.get("embedding", {}).get("model"),
            required_semantic_selectors=ROUTING_SELECTORS,
        )

    def _manifest(self, run_id, started, staged, chunks, embeddings, index, verification, device, context):
        normalized = _normalized_inventory(self.paths.normalized_roots)
        chunk_inventory = _chunk_inventory(staged["chunks"])
        embedding_inventory = _embedding_inventory(staged["embeddings"], inspect_vectors=False)
        vector_inventory = _vector_inventory(staged["vector_db"])
        return {
            "schema_version": 1, "run_id": run_id, "started_at": started,
            "completed_at": self.clock().isoformat(), "repository_commit": _git_commit(self.paths.repository_root),
            "normalized_roots": [str(value) for value in self.paths.normalized_roots],
            "normalized_object_count": normalized.details.get("object_count"),
            "normalized_fingerprint": normalized.details.get("fingerprint"),
            "chunk_count": chunks.get("total_chunks"),
            "chunk_fingerprint": chunk_inventory.details.get("fingerprint"),
            "chunk_configuration": {
                "chunk_size": chunks.get("chunk_size"), "overlap": chunks.get("overlap"),
                "max_chunks_per_document": chunks.get("max_chunks_per_document_setting"),
            },
            "chunker": "app.chunk.run_chunking", "embedding_count": embeddings.get("total_chunks"),
            "embedding_fingerprint": embedding_inventory.details.get("fingerprint"),
            "embedding_model": embeddings.get("model"), "embedding_dimension": embeddings.get("embedding_dimension"),
            "embedding_normalized": True, "embedding_context": context, "execution_device": device,
            "faiss_index_type": index.get("index_type"), "faiss_vector_count": index.get("num_vectors"),
            "index_record_fingerprint": vector_inventory.details.get("record_fingerprint"),
            "metadata_record_count": verification.metadata_record_count,
            "configured_artifact_paths": self.paths.to_dict(),
            "staged_artifact_paths": {key: str(value) for key, value in staged.items()},
            "validation": verification.to_dict(),
            "semantic_metadata_coverage": {
                "chunks": verification.semantic_chunk_coverage,
                "index_records": verification.semantic_index_coverage,
                "families": verification.family_checks,
            },
        }


def verify_pipeline(
    normalized_roots: Sequence[Path], chunks_dir: Path, embeddings_dir: Path,
    vector_db_dir: Path, *, expected_model: Optional[str] = None,
    required_semantic_selectors: Mapping[str, Mapping[str, Any]] = ROUTING_SELECTORS,
    norm_tolerance: float = 1e-3,
) -> VerificationReport:
    report = VerificationReport()
    objects = _load_object_identities(normalized_roots, report.errors)
    report.normalized_object_count = len(objects)
    representatives = _semantic_representatives(objects, required_semantic_selectors)
    chunk_ids = set(); chunks_by_object = {}
    chunk_coverage=Counter()
    for file,value in _iter_json_arrays(chunks_dir, report.errors, "chunk"):
        report.chunk_file_count += 1
        for chunk in value:
            report.chunk_count += 1
            cid = chunk.get("id"); oid = chunk.get("knowledge_object_id")
            if not cid or cid in chunk_ids: report.errors.append(f"Missing or duplicate chunk ID: {cid!r}")
            else: chunk_ids.add(cid)
            if oid not in objects: report.errors.append(f"Chunk {cid!r} maps to unknown Knowledge Object {oid!r}")
            if not isinstance(chunk.get("metadata"), dict): report.errors.append(f"Chunk {cid!r} has no metadata object")
            if oid in representatives.values(): chunks_by_object.setdefault(oid, []).append(chunk)
            _count_semantic(chunk,chunk_coverage)
    report.semantic_chunk_coverage=dict(sorted(chunk_coverage.items()))

    embedding_ids = set(); vectors_for_smoke = []
    models = set(); dimensions = set(); normalization_flags = set()
    for file,value in _iter_json_arrays(embeddings_dir, report.errors, "embedding"):
        report.embedding_file_count += 1
        for item in value:
            report.embedding_count += 1
            cid = item.get("chunk_id"); vector = item.get("embedding")
            if not cid or cid in embedding_ids: report.errors.append(f"Missing or duplicate embedded chunk ID: {cid!r}")
            else: embedding_ids.add(cid)
            if not isinstance(vector, list) or not vector:
                report.errors.append(f"Embedding {cid!r} has no vector"); continue
            dimensions.add(len(vector))
            if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in vector):
                report.errors.append(f"Embedding {cid!r} contains NaN, infinity, or a nonnumeric value"); continue
            metadata = item.get("embedding_metadata") or {}
            if metadata.get("model"): models.add(str(metadata["model"]))
            normalization_flags.add(metadata.get("normalized"))
            if metadata.get("normalized"):
                norm = math.sqrt(sum(float(value) ** 2 for value in vector))
                if abs(norm - 1.0) > norm_tolerance:
                    report.errors.append(f"Embedding {cid!r} norm {norm:.6f} is outside tolerance")
            if len(vectors_for_smoke) < 3: vectors_for_smoke.append(vector)
    if chunk_ids != embedding_ids:
        report.errors.append(f"Chunk/embedding ID sets differ ({len(chunk_ids)} chunks, {len(embedding_ids)} embeddings)")
    if len(dimensions) > 1: report.errors.append(f"Embedding dimensions are inconsistent: {sorted(dimensions)}")
    report.embedding_dimension = next(iter(dimensions), None)
    if len(models) > 1: report.errors.append(f"Embedding models are inconsistent: {sorted(models)}")
    report.embedding_model = next(iter(models), None)
    if normalization_flags != {True}:
        report.errors.append(f"Embedding normalization metadata is inconsistent: {sorted(map(str, normalization_flags))}")
    if expected_model and report.embedding_model and report.embedding_model != expected_model:
        report.errors.append(f"Embedding model {report.embedding_model!r} does not match configured model {expected_model!r}")

    records = []
    try:
        import faiss
        index = faiss.read_index(str(Path(vector_db_dir) / "index.faiss"))
        with (Path(vector_db_dir) / "records.pkl").open("rb") as handle: records = pickle.load(handle)
        metadata = _read_json(Path(vector_db_dir) / "metadata.json") or {}
        report.vector_count = int(index.ntotal); report.metadata_record_count = len(records)
        if report.vector_count != report.embedding_count: report.errors.append("FAISS vector count does not equal embedding count")
        if len(records) != report.vector_count: report.errors.append("FAISS metadata-record count does not equal vector count")
        if metadata.get("num_vectors") != report.vector_count: report.errors.append("Vector metadata num_vectors is inconsistent")
        if metadata.get("dimension") != report.embedding_dimension: report.errors.append("Vector metadata dimension is inconsistent")
        if int(index.d) != report.embedding_dimension: report.errors.append("FAISS dimension does not equal embedding dimension")
        if metadata.get("index_type") != type(index).__name__: report.errors.append("Vector metadata index_type is inconsistent")
        record_ids = [record.get("chunk_id") for record in records]
        if len(record_ids) != len(set(record_ids)): report.errors.append("FAISS metadata contains duplicate chunk mappings")
        if set(record_ids) != embedding_ids: report.errors.append("FAISS metadata/chunk mapping differs from embeddings")
        if vectors_for_smoke and report.vector_count:
            import numpy as np
            queries = np.asarray(vectors_for_smoke, dtype="float32")
            scores, indices = index.search(queries, 1)
            if indices.shape != (len(vectors_for_smoke), 1) or (indices < 0).any():
                report.errors.append("FAISS vector smoke search returned invalid indices")
            else: report.vector_smoke_queries = len(vectors_for_smoke)
    except Exception as exc:
        report.errors.append(f"Unable to read or search vector index: {type(exc).__name__}: {exc}")
    report.semantic_index_coverage = _semantic_coverage(records)
    report.family_checks = _verify_semantic_families(objects, chunks_by_object, records, required_semantic_selectors, report.errors)
    report.valid = not report.errors
    return report


def _normalized_inventory(roots):
    count = 0; digest = hashlib.sha256(); errors = []
    for path in _json_paths(roots):
        try:
            value = json.loads(path.read_text(encoding="utf-8")); count += 1
            meta = value.get("metadata") or {}
            token = {
                "id": value.get("id"), "object_type": value.get("object_type"),
                "content_hash": value.get("content_hash") or meta.get("content_hash") or value.get("document_hash") or value.get("raw_acquisition_hash"),
                "semantic_identity": meta.get("semantic_identity"),
            }
            digest.update(json.dumps(token, sort_keys=True, separators=(",", ":"), default=str).encode())
        except Exception as exc: errors.append(f"{path}: {exc}")
    state = ArtifactState.INCONSISTENT if errors else (ArtifactState.CURRENT if count else ArtifactState.MISSING)
    return StageReport(state, errors or (["No normalized Knowledge Objects found."] if not count else []), {"object_count": count, "fingerprint": digest.hexdigest() if count else None})


def _chunk_inventory(path):
    if not Path(path).is_dir():
        return StageReport(ArtifactState.MISSING, [f"Chunk directory does not exist: {path}"], {"file_count": 0, "chunk_count": 0})
    errors=[];ids=[];coverage=Counter();files=0;count=0
    for file,items in _iter_json_arrays(path,errors,"chunk"):
        files+=1
        for item in items: count+=1;ids.append(_artifact_identity_token(item,"id"));_count_semantic(item,coverage)
    details={"file_count":files,"chunk_count":count,"fingerprint":_fingerprint(ids),"semantic_coverage":dict(coverage),"latest_mtime":_latest_mtime(path)}
    return StageReport(ArtifactState.INCONSISTENT if errors else (ArtifactState.UNKNOWN if count else ArtifactState.MISSING), errors or (["No chunk artifacts found."] if not count else ["No build manifest establishes freshness."]), details)


def _embedding_inventory(path, inspect_vectors=False):
    if not Path(path).is_dir():
        return StageReport(ArtifactState.MISSING, [f"Embedding directory does not exist: {path}"], {"file_count": 0, "embedding_count": 0})
    errors=[];ids=[];dimensions=set();models=set();files=0;count=0
    for file,items in _iter_json_arrays(path,errors,"embedding"):
        files+=1
        for item in items:
            count+=1;ids.append(_artifact_identity_token(item,"chunk_id"));meta=item.get("embedding_metadata") or {}
            if meta.get("model"):models.add(str(meta["model"]))
            vector=item.get("embedding")
            if isinstance(vector,list):dimensions.add(len(vector))
    details={"file_count":files,"embedding_count":count,"fingerprint":_fingerprint(ids),"dimensions":sorted(dimensions),"models":sorted(models),"latest_mtime":_latest_mtime(path)}
    return StageReport(ArtifactState.INCONSISTENT if errors or len(dimensions)>1 or len(models)>1 else (ArtifactState.UNKNOWN if count else ArtifactState.MISSING), errors or (["No embedding artifacts found."] if not count else ["No build manifest establishes freshness."]), details)


def _vector_inventory(path):
    path=Path(path); required=("index.faiss","records.pkl","metadata.json")
    missing=[name for name in required if not (path/name).is_file()]
    if missing: return StageReport(ArtifactState.MISSING,["Missing: "+", ".join(missing)],{"latest_mtime":_latest_mtime(path)})
    try:
        import faiss
        index=faiss.read_index(str(path/"index.faiss"))
        with (path/"records.pkl").open("rb") as handle: records=pickle.load(handle)
        meta=_read_json(path/"metadata.json") or {}
        reasons=[]
        if int(index.ntotal)!=len(records): reasons.append("FAISS vector and record counts differ.")
        if meta.get("num_vectors")!=int(index.ntotal): reasons.append("metadata num_vectors differs from FAISS.")
        if meta.get("dimension")!=int(index.d): reasons.append("metadata dimension differs from FAISS.")
        if meta.get("index_type")!=type(index).__name__: reasons.append("metadata index_type differs from FAISS.")
        state=ArtifactState.INCONSISTENT if reasons else ArtifactState.UNKNOWN
        if not reasons: reasons=["Artifacts are structurally consistent, but no build manifest establishes freshness."]
        return StageReport(state,reasons,{"vector_count":int(index.ntotal),"record_count":len(records),"dimension":int(index.d),"index_type":type(index).__name__,"embedding_model":meta.get("embedding_model"),"record_fingerprint":_fingerprint(_artifact_identity_token(record,"id") for record in records),"latest_mtime":_latest_mtime(path)})
    except Exception as exc: return StageReport(ArtifactState.INCONSISTENT,[f"Unable to load vector artifacts: {type(exc).__name__}: {exc}"],{})


def _apply_freshness(normalized,chunks,embeddings,vector,manifest,config):
    if not manifest: return
    if chunks.state != ArtifactState.MISSING and chunks.state != ArtifactState.INCONSISTENT:
        if manifest.get("normalized_fingerprint") != normalized.details.get("fingerprint"):
            chunks.state=ArtifactState.STALE; chunks.reasons=["Normalized corpus fingerprint differs from the build manifest."]
        elif manifest.get("chunk_count") != chunks.details.get("chunk_count"):
            chunks.state=ArtifactState.INCONSISTENT; chunks.reasons=["Chunk count differs from the build manifest."]
        elif manifest.get("chunk_fingerprint") != chunks.details.get("fingerprint"):
            chunks.state=ArtifactState.INCONSISTENT; chunks.reasons=["Chunk Semantic Identity fingerprint differs from the build manifest."]
        else: chunks.state=ArtifactState.CURRENT; chunks.reasons=["Normalized fingerprint and chunk count match the build manifest."]
    if embeddings.state not in (ArtifactState.MISSING,ArtifactState.INCONSISTENT):
        if chunks.state != ArtifactState.CURRENT or manifest.get("chunk_fingerprint") != chunks.details.get("fingerprint"):
            embeddings.state=ArtifactState.STALE; embeddings.reasons=["Chunk dependency differs from the build manifest."]
        elif manifest.get("embedding_model") != config.get("embedding",{}).get("model"):
            embeddings.state=ArtifactState.STALE; embeddings.reasons=["Configured embedding model differs from the build manifest."]
        elif manifest.get("embedding_count") != embeddings.details.get("embedding_count"):
            embeddings.state=ArtifactState.INCONSISTENT; embeddings.reasons=["Embedding count differs from the build manifest."]
        elif manifest.get("embedding_fingerprint") != embeddings.details.get("fingerprint"):
            embeddings.state=ArtifactState.INCONSISTENT; embeddings.reasons=["Embedding metadata fingerprint differs from the build manifest."]
        else: embeddings.state=ArtifactState.CURRENT; embeddings.reasons=["Chunk fingerprint, model, and count match the build manifest."]
    if vector.state not in (ArtifactState.MISSING,ArtifactState.INCONSISTENT):
        if embeddings.state != ArtifactState.CURRENT:
            vector.state=ArtifactState.STALE; vector.reasons=["Embedding dependency is not current."]
        elif manifest.get("faiss_vector_count") != vector.details.get("vector_count"):
            vector.state=ArtifactState.INCONSISTENT; vector.reasons=["FAISS count differs from the build manifest."]
        elif manifest.get("index_record_fingerprint") != vector.details.get("record_fingerprint"):
            vector.state=ArtifactState.INCONSISTENT; vector.reasons=["Index-record metadata fingerprint differs from the build manifest."]
        else: vector.state=ArtifactState.CURRENT; vector.reasons=["Embedding dependency and FAISS count match the build manifest."]


def _load_object_identities(roots, errors):
    values={}
    for path in _json_paths(roots):
        try:
            value=json.loads(path.read_text(encoding="utf-8")); oid=value.get("id")
            if not oid or oid in values: errors.append(f"Missing or duplicate Knowledge Object ID: {oid!r}")
            else: values[oid]=(value.get("metadata") or {}).get("semantic_identity") or {}
        except Exception as exc: errors.append(f"Unable to load normalized object {path}: {exc}")
    return values


def _semantic_representatives(objects,selectors):
    return {
        name: sorted(oid for oid,identity in objects.items() if all(identity.get(field)==value for field,value in selector.items()))[0]
        for name,selector in selectors.items()
        if any(all(identity.get(field)==value for field,value in selector.items()) for identity in objects.values())
    }


def _verify_semantic_families(objects,chunks_by_object,records,selectors,errors):
    records_by_object={}
    for record in records: records_by_object.setdefault(record.get("knowledge_object_id"),[]).append(record)
    result={}
    for family,selector in selectors.items():
        candidates=sorted(oid for oid,identity in objects.items() if all(identity.get(field)==value for field,value in selector.items()))
        if not candidates:
            errors.append(f"No normalized representative exists for semantic family {family!r}"); result[family]={"valid":False,"reason":"missing_normalized_representative"}; continue
        oid=candidates[0]; identity=objects[oid]
        expected={field:value for field,value in identity.items() if field in SEMANTIC_FIELDS and value not in (None,[],{})}
        family_errors=[]
        for label,items in (("chunk",chunks_by_object.get(oid,[])),("index",records_by_object.get(oid,[]))):
            if not items: family_errors.append(f"missing_{label}_record"); continue
            if not any(all((item.get("metadata") or {}).get("semantic_identity",{}).get(field)==value for field,value in expected.items()) for item in items):
                family_errors.append(f"{label}_semantic_identity_mismatch")
        if family_errors: errors.append(f"Semantic propagation failed for {family}: {', '.join(family_errors)}")
        result[family]={"valid":not family_errors,"knowledge_object_id":oid,"checked_fields":sorted(expected),"errors":family_errors}
    return result


def _semantic_coverage(records):
    counts=Counter()
    for item in records: _count_semantic(item,counts)
    return dict(sorted(counts.items()))


def _count_semantic(item,counts):
    identity=(item.get("metadata") or {}).get("semantic_identity") or {}
    for field in SEMANTIC_FIELDS:
        if identity.get(field) not in (None,[],{}): counts[field]+=1


def _iter_json_arrays(path,errors,label):
    path=Path(path)
    if not path.is_dir():
        errors.append(f"Missing {label} directory: {path}")
        return
    for file in sorted(path.glob("*.json")):
        if file.name==MANIFEST_NAME: continue
        try:
            value=json.loads(file.read_text(encoding="utf-8"))
            if not isinstance(value,list): raise ValueError("artifact must contain a JSON array")
            yield file,value
        except Exception as exc: errors.append(f"Unreadable {label} artifact {file}: {exc}")


def _json_paths(roots):
    found={}
    for root in roots:
        root=Path(root)
        if root.is_file() and root.suffix.casefold()==".json": found[str(root.resolve())]=root
        elif root.is_dir():
            for path in root.rglob("*.json"): found[str(path.resolve())]=path
    return tuple(found[key] for key in sorted(found))


def _fingerprint(values):
    if not values: return None
    digest=hashlib.sha256()
    for value in sorted(values): digest.update(value.encode());digest.update(b"\0")
    return digest.hexdigest()


def _artifact_identity_token(item, id_field):
    metadata=item.get("metadata") if isinstance(item.get("metadata"),dict) else {}
    embedding=item.get("embedding_metadata") if isinstance(item.get("embedding_metadata"),dict) else {}
    payload={"id":item.get(id_field) or item.get("chunk_id"),"semantic_identity":metadata.get("semantic_identity")}
    if embedding:
        payload["embedding"]={
            "model":embedding.get("model"),
            "embedding_context":embedding.get("embedding_context",embedding.get("context")),
            "normalized":embedding.get("normalized"),
        }
    return json.dumps(payload,sort_keys=True,separators=(",",":"),default=str)


def _read_json(path):
    try: return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError,json.JSONDecodeError,OSError): return None


def _write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name("."+path.name+".tmp")
    temporary.write_text(json.dumps(value,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
    os.replace(temporary,path)


def _latest_mtime(path):
    path=Path(path)
    files=[item for item in path.glob("*") if item.is_file()] if path.is_dir() else []
    return datetime.fromtimestamp(max((item.stat().st_mtime for item in files),default=0),timezone.utc).isoformat() if files else None


def _device_id(path):
    path=Path(path); existing=path
    while not existing.exists() and existing!=existing.parent: existing=existing.parent
    return existing.stat().st_dev


def _incomplete_runs(root):
    root=Path(root)
    if not root.is_dir(): return ()
    return tuple(sorted(path.name for path in root.iterdir() if path.is_dir() and (path/INCOMPLETE_NAME).is_file()))


def _cleanup_incomplete_runs(root):
    root=Path(root)
    for name in _incomplete_runs(root):
        path=root/name
        if path.parent!=root or not (path/INCOMPLETE_NAME).is_file(): raise RuntimeError(f"Unsafe staging cleanup target: {path}")
        shutil.rmtree(path)


def _promote(run_id,staged,targets,backup_root,before_promotion):
    backup_run=Path(backup_root)/run_id; backup_run.mkdir(parents=True,exist_ok=False)
    backups={key:backup_run/key for key in targets if Path(targets[key]).exists()}
    before_promotion(backups)
    promoted=[]
    try:
        for key,target in targets.items():
            target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists(): os.replace(target,backups[key])
            os.replace(staged[key],target);promoted.append(key)
        return backups
    except Exception:
        _rollback(targets,backups,promoted)
        raise


def _rollback(targets,backups,promoted=None):
    promoted=set(promoted or targets)
    for key in reversed(tuple(targets)):
        target=Path(targets[key]);backup=backups.get(key)
        if key in promoted and target.exists(): shutil.rmtree(target)
        if backup and Path(backup).exists(): os.replace(backup,target)


def _git_commit(root):
    try: return subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True,stderr=subprocess.DEVNULL).strip()
    except Exception: return None


__all__ = [
    "ArtifactState", "BuildHooks", "MANIFEST_NAME", "PipelinePaths",
    "PipelineStatusReport", "SemanticPipelineService", "StageReport",
    "VerificationReport", "resolve_pipeline_paths", "verify_pipeline",
]
