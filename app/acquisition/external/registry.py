from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Tuple

import yaml

from app.acquisition.authority import SourceAuthority
from app.acquisition.external.contracts import (
    AcquisitionMode,
    ExternalResourceDefinition,
    ExternalSourceDefinition,
)


class ExternalSourceRegistry:
    """Ordered registry of authorities and explicit external resources."""

    def __init__(self, sources: Iterable[ExternalSourceDefinition]) -> None:
        self.sources = tuple(sources)
        self._by_key: Dict[str, ExternalSourceDefinition] = {}
        self._resources: Dict[str, Tuple[ExternalSourceDefinition, ExternalResourceDefinition]] = {}

        for source in self.sources:
            if source.key in self._by_key:
                raise ValueError(f"Duplicate external source key: {source.key}")
            self._by_key[source.key] = source
            for resource in source.resources:
                if resource.id in self._resources:
                    raise ValueError(f"Duplicate external resource id: {resource.id}")
                self._resources[resource.id] = (source, resource)

    @classmethod
    def from_yaml(cls, path: Path) -> "ExternalSourceRegistry":
        with Path(path).open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}

        sources = []
        for raw_source in payload.get("sources", []):
            resources = tuple(
                ExternalResourceDefinition(
                    id=str(item["id"]),
                    title=str(item["title"]),
                    canonical_url=str(item["canonical_url"]),
                    document_type=str(item["document_type"]),
                    evidence_domains=tuple(item["evidence_domains"]),
                    effective_period=item.get("effective_period"),
                    version=item.get("version"),
                    geographic_scope=str(item.get("geographic_scope", "United States")),
                    acquisition_mode=(
                        AcquisitionMode(item["acquisition_mode"])
                        if item.get("acquisition_mode")
                        else None
                    ),
                )
                for item in raw_source.get("resources", [])
            )
            source = ExternalSourceDefinition(
                key=str(raw_source["key"]),
                name=str(raw_source["name"]),
                issuing_authority=str(raw_source["issuing_authority"]),
                authority_class=SourceAuthority(raw_source["authority_class"]),
                evidence_role=str(raw_source["evidence_role"]),
                supported_decision_types=tuple(raw_source["supported_decision_types"]),
                supported_evidence_domains=tuple(raw_source["supported_evidence_domains"]),
                refresh_policy=str(raw_source["refresh_policy"]),
                max_age_days=int(raw_source["max_age_days"]),
                expected_extraction_method=str(raw_source["expected_extraction_method"]),
                resources=resources,
                acquisition_mode=AcquisitionMode(
                    raw_source.get("acquisition_mode", AcquisitionMode.LIVE_WEB.value)
                ),
            )
            cls._validate(source)
            sources.append(source)
        return cls(sources)

    @staticmethod
    def _validate(source: ExternalSourceDefinition) -> None:
        required = (
            source.key,
            source.name,
            source.issuing_authority,
            source.evidence_role,
            source.refresh_policy,
            source.expected_extraction_method,
        )
        if not all(value.strip() for value in required):
            raise ValueError("External source metadata must not be empty.")
        if source.authority_class is SourceAuthority.UNKNOWN:
            raise ValueError(f"External source {source.key!r} requires known authority.")
        if source.max_age_days <= 0:
            raise ValueError(f"External source {source.key!r} requires positive max_age_days.")
        for resource in source.resources:
            if not resource.canonical_url.startswith(("https://", "http://")):
                raise ValueError(f"Resource {resource.id!r} requires a canonical HTTP URL.")
            unsupported = set(resource.evidence_domains) - set(source.supported_evidence_domains)
            if unsupported:
                raise ValueError(f"Resource {resource.id!r} has unsupported domains: {sorted(unsupported)}")

    def source(self, key: str) -> ExternalSourceDefinition:
        return self._by_key[key]

    def resource(self, resource_id: str) -> Tuple[ExternalSourceDefinition, ExternalResourceDefinition]:
        return self._resources[resource_id]
