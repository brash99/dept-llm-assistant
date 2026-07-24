"""Reviewed, versioned registries used by deterministic document routing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Tuple

import yaml

from app.classification.document_signals import DocumentSignals


DEFAULT_REGISTRY = Path(__file__).resolve().parents[2] / "config" / "document_classification_registry.yaml"


@dataclass(frozen=True)
class RegistryRule:
    rule_id: str
    classifier: str
    priority: int
    source_keys: Tuple[str, ...]
    path_prefixes: Tuple[str, ...]
    path_segments_all: Tuple[str, ...]
    domains: Tuple[str, ...]
    source_family: Optional[str]
    document_type: Optional[str]
    institutional_role: Optional[str]
    allowed_document_types: Tuple[str, ...]
    allowed_institutional_roles: Tuple[str, ...]
    issuing_authority: Optional[str]
    authority_class: Optional[str]
    institutional_entity: Optional[Mapping[str, Any]]
    audit_required: bool
    notes: str
    version: str

    def matches(self, signals: DocumentSignals) -> bool:
        if self.source_keys and signals.source_key not in self.source_keys:
            return False
        path = signals.qualified_relative_path.casefold()
        if self.path_prefixes and not any(path.startswith(value) for value in self.path_prefixes):
            return False
        if self.path_segments_all and not all(value in signals.path_segments for value in self.path_segments_all):
            return False
        if self.domains and signals.canonical_domain not in self.domains:
            return False
        return bool(self.source_keys or self.path_prefixes or self.domains)


class DocumentFamilyRegistry:
    def __init__(self, rules: Tuple[RegistryRule, ...], version: str):
        self.rules = rules
        self.version = version

    @classmethod
    def load(cls, path: Path = DEFAULT_REGISTRY) -> "DocumentFamilyRegistry":
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls(_rules(payload.get("document_families") or (), str(payload.get("version", "1"))), str(payload.get("version", "1")))

    def matches(self, signals: DocumentSignals) -> Tuple[RegistryRule, ...]:
        return tuple(sorted((rule for rule in self.rules if rule.matches(signals)), key=lambda item: (-item.priority, item.rule_id)))


class InstitutionalPublisherRegistry:
    def __init__(self, rules: Tuple[RegistryRule, ...], version: str):
        self.rules = rules
        self.version = version

    @classmethod
    def load(cls, path: Path = DEFAULT_REGISTRY) -> "InstitutionalPublisherRegistry":
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls(_rules(payload.get("publishers") or (), str(payload.get("version", "1"))), str(payload.get("version", "1")))

    def matches(self, signals: DocumentSignals) -> Tuple[RegistryRule, ...]:
        return tuple(rule for rule in self.rules if rule.matches(signals))


def _rules(values, version):
    return tuple(
        RegistryRule(
            rule_id=str(value["rule_id"]), classifier=str(value["classifier"]),
            priority=int(value.get("priority", 0)),
            source_keys=tuple(str(v).casefold() for v in value.get("source_keys") or ()),
            path_prefixes=tuple(str(v).casefold().lstrip("/") for v in value.get("path_prefixes") or ()),
            path_segments_all=tuple(str(v).casefold() for v in value.get("path_segments_all") or ()),
            domains=tuple(str(v).casefold() for v in value.get("domains") or ()),
            source_family=value.get("source_family"), document_type=value.get("document_type"),
            institutional_role=value.get("institutional_role"), issuing_authority=value.get("issuing_authority"),
            allowed_document_types=tuple(str(v) for v in value.get("allowed_document_types") or (() if value.get("document_type") is None else (value["document_type"],))),
            allowed_institutional_roles=tuple(str(v) for v in value.get("allowed_institutional_roles") or (() if value.get("institutional_role") is None else (value["institutional_role"],))),
            authority_class=value.get("authority_class"), institutional_entity=value.get("institutional_entity"),
            audit_required=bool(value.get("audit_required", False)), notes=str(value.get("notes", "")),
            version=str(value.get("version", version)),
        ) for value in values
    )


__all__ = ["DocumentFamilyRegistry", "InstitutionalPublisherRegistry", "RegistryRule"]
