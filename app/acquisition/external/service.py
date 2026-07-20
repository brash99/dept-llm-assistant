from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import ssl
from typing import Dict, Iterable, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import certifi

from app.acquisition.external.contracts import (
    AcquisitionPlan,
    StagedExternalDocument,
    ValidationResult,
)
from app.acquisition.external.registry import ExternalSourceRegistry
from app.acquisition.manifest import AcquisitionManifest, AcquisitionStatus
from app.acquisition.method import AcquisitionMethod
from app.acquisition.source_document import SourceDocument
from app.knowledge import save_knowledge_object
from app.normalize import build_default_registry, normalize_single_file


@dataclass(frozen=True)
class FetchedArtifact:
    content: bytes
    media_type: str
    final_url: str


class CuratedURLFetcher:
    """Fetch exactly one registry URL; this class does not discover links."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch(self, url: str) -> FetchedArtifact:
        request = Request(
            url,
            headers={
                "User-Agent": "InstitutionalSemanticObservatory/1.0 (curated evidence acquisition)",
                "Accept": "text/html,application/pdf,text/plain,*/*;q=0.5",
            },
        )
        context = ssl.create_default_context(cafile=certifi.where())
        with urlopen(request, timeout=self.timeout_seconds, context=context) as response:
            return FetchedArtifact(
                content=response.read(),
                media_type=response.headers.get_content_type() or "application/octet-stream",
                final_url=response.geturl(),
            )


class ExternalEvidenceAcquisitionService:
    """Stage, validate, and promote only resources in an acquisition plan."""

    REQUIRED_PROVENANCE = (
        "issuing_authority",
        "authority_class",
        "evidence_role",
        "decision_types",
        "evidence_domains",
        "retrieval_timestamp",
        "effective_period",
        "version",
        "canonical_url",
        "document_type",
        "geographic_scope",
    )

    def __init__(
        self,
        *,
        registry: ExternalSourceRegistry,
        staging_dir: Path,
        normalized_dir: Path,
        fetcher=None,
        manifest_path: Optional[Path] = None,
    ) -> None:
        self.registry = registry
        self.staging_dir = Path(staging_dir)
        self.normalized_dir = Path(normalized_dir)
        self.fetcher = fetcher or CuratedURLFetcher()
        self.manifest = AcquisitionManifest(
            manifest_path or self.staging_dir / "external_manifest.jsonl"
        )

    def stage(self, plan: AcquisitionPlan) -> tuple[StagedExternalDocument, ...]:
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        staged = []
        seen_resources = set()

        for item in plan.items:
            if item.resource_id in seen_resources:
                continue
            seen_resources.add(item.resource_id)
            source, resource = self.registry.resource(item.resource_id)
            artifact = self.fetcher.fetch(resource.canonical_url)
            relative_path = self._relative_path(source.key, resource.id, artifact)
            destination = self.staging_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(artifact.content)

            content_hash = hashlib.sha256(artifact.content).hexdigest()
            acquired_at = datetime.now(timezone.utc)
            source_document = SourceDocument(
                id=f"sha256:{content_hash}",
                title=resource.title,
                source_organization=source.issuing_authority,
                authority=source.authority_class,
                acquisition_method=AcquisitionMethod.DIRECT_DOWNLOAD,
                relative_path=relative_path.as_posix(),
                content_hash=content_hash,
                acquired_at=acquired_at,
                source_url=artifact.final_url,
                media_type=artifact.media_type,
            )
            record = StagedExternalDocument(
                source_document=source_document,
                source_key=source.key,
                resource_id=resource.id,
                issuing_authority=source.issuing_authority,
                authority_class=source.authority_class.value,
                evidence_role=source.evidence_role,
                decision_types=source.supported_decision_types,
                evidence_domains=resource.evidence_domains,
                effective_period=resource.effective_period,
                version=resource.version,
                canonical_url=resource.canonical_url,
                document_type=resource.document_type,
                geographic_scope=resource.geographic_scope,
                refresh_policy=source.refresh_policy,
                max_age_days=source.max_age_days,
                expected_extraction_method=source.expected_extraction_method,
            )
            self._write_sidecar(record)
            staged.append(record)
        return tuple(staged)

    def validate(
        self,
        records: Iterable[StagedExternalDocument],
        *,
        now: Optional[datetime] = None,
    ) -> tuple[ValidationResult, ...]:
        now = now or datetime.now(timezone.utc)
        parser_registry = build_default_registry()
        results = []
        batch_hashes = set()

        for record in records:
            errors = []
            path = self.staging_dir / record.source_document.relative_path
            provenance = record.provenance()
            missing = [key for key in self.REQUIRED_PROVENANCE if not provenance.get(key)]
            if missing:
                errors.append("Missing provenance: " + ", ".join(missing))

            parser = parser_registry.get_parser(path)
            extracted_characters = 0
            if parser is None:
                errors.append("No normalization parser available.")
            else:
                expected_parser = record.expected_extraction_method.casefold()
                if expected_parser not in parser.name.casefold():
                    errors.append(
                        "Configured extraction method does not match the "
                        f"available parser: {record.expected_extraction_method} "
                        f"!= {parser.name}."
                    )
                try:
                    document = parser.parse(path, self.staging_dir)
                    extracted_characters = len(document.text.strip())
                    if extracted_characters == 0:
                        errors.append("Extraction produced no text.")
                except Exception as error:
                    errors.append(f"Extraction failed: {error}")

            age_days = (now - record.source_document.acquired_at).total_seconds() / 86400
            fresh = age_days <= record.max_age_days
            if not fresh:
                errors.append("Staged artifact exceeds its refresh-policy age.")

            decision = self.manifest.classify(record.source_document)
            duplicate = (
                decision.status is AcquisitionStatus.DUPLICATE_CONTENT
                or record.source_document.content_hash in batch_hashes
            )
            if duplicate:
                errors.append("Duplicate content already exists in the external manifest.")
            elif decision.status is AcquisitionStatus.UNCHANGED:
                errors.append("The same resource version is already acquired.")

            batch_hashes.add(record.source_document.content_hash)

            results.append(
                ValidationResult(
                    resource_id=record.resource_id,
                    valid=not errors,
                    errors=tuple(errors),
                    extracted_characters=extracted_characters,
                    duplicate=duplicate,
                    fresh=fresh,
                )
            )
        return tuple(results)

    def promote(
        self,
        records: Iterable[StagedExternalDocument],
        validations: Iterable[ValidationResult],
    ) -> Dict[str, Path]:
        validation_by_id = {item.resource_id: item for item in validations}
        outputs: Dict[str, Path] = {}

        for record in records:
            validation = validation_by_id.get(record.resource_id)
            if validation is None or not validation.valid:
                continue

            path = self.staging_dir / record.source_document.relative_path
            document, output_path = normalize_single_file(
                path=path,
                raw_drive=self.staging_dir,
                normalized_dir=self.normalized_dir,
                source_key=f"external_{record.source_key}",
            )
            provenance = record.provenance()
            document.metadata = dict(document.metadata or {})
            document.metadata["external_provenance"] = provenance
            document.metadata.update(
                {
                    "issuing_authority": record.issuing_authority,
                    "authority_class": record.authority_class,
                    "evidence_role": record.evidence_role,
                    "decision_types": list(record.decision_types),
                    "evidence_domains": list(record.evidence_domains),
                    "canonical_url": record.canonical_url,
                    "geographic_scope": record.geographic_scope,
                }
            )
            document.source = dict(document.source or {})
            document.source.update(
                {
                    "kind": "curated_external",
                    "canonical_url": record.canonical_url,
                    "source_document_id": record.source_document.id,
                    "acquired_at": record.source_document.acquired_at.isoformat(),
                }
            )
            save_knowledge_object(document, output_path)
            self.manifest.record(record.source_document)
            outputs[record.resource_id] = Path(output_path)
        return outputs

    def acquire_validate_promote(self, plan: AcquisitionPlan) -> Dict[str, object]:
        staged = self.stage(plan)
        validations = self.validate(staged)
        promoted = self.promote(staged, validations)
        return {"staged": staged, "validations": validations, "promoted": promoted}

    def _write_sidecar(self, record: StagedExternalDocument) -> None:
        source_path = self.staging_dir / record.source_document.relative_path
        sidecar = source_path.with_suffix(source_path.suffix + ".provenance.json")
        sidecar.write_text(
            json.dumps(
                {
                    "source_document": record.source_document.to_dict(),
                    "external_provenance": record.provenance(),
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _relative_path(source_key: str, resource_id: str, artifact: FetchedArtifact) -> Path:
        name = Path(urlparse(artifact.final_url).path).name
        if not name or "." not in name:
            suffix = {
                "text/html": ".html",
                "application/pdf": ".pdf",
                "text/plain": ".txt",
            }.get(artifact.media_type.casefold(), ".bin")
            name = resource_id + suffix
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
        return Path(source_key, resource_id, safe_name)
