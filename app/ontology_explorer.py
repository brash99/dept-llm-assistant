"""Extensible developer model for interactive ISO ontology inspection."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol

from app.contribution_ontology import ContributionKnowledgeObject
from app.department_contributions import DepartmentContributionKnowledgeObject


@dataclass(frozen=True)
class OntologyGraphNode:
    node_id: str
    entity_id: str
    entity_type: str
    label: str


@dataclass(frozen=True)
class OntologyGraphEdge:
    edge_id: str
    subject_id: str
    predicate: str
    object_id: str
    assertion_fingerprint: str


@dataclass(frozen=True)
class OntologyGraph:
    nodes: tuple[OntologyGraphNode, ...]
    edges: tuple[OntologyGraphEdge, ...]

    def to_dot(
        self,
        predicates: Iterable[str] | None = None,
        target_entity_types: Iterable[str] | None = None,
    ) -> str:
        selected = None if predicates is None else set(predicates)
        selected_types = (
            None
            if target_entity_types is None
            else set(target_entity_types)
        )
        entity_types = {
            node.entity_id: node.entity_type for node in self.nodes
        }
        edges = tuple(
            edge
            for edge in self.edges
            if (selected is None or edge.predicate in selected)
            and (
                selected_types is None
                or entity_types[edge.object_id] in selected_types
            )
        )
        represented = {
            entity_id
            for edge in edges
            for entity_id in (edge.subject_id, edge.object_id)
        }
        nodes = tuple(
            node for node in self.nodes if node.entity_id in represented
        )
        node_names = {
            node.entity_id: f"n{index}"
            for index, node in enumerate(nodes)
        }
        lines = [
            "digraph ISOContributionOntology {",
            '  graph [rankdir="LR", bgcolor="transparent"];',
            '  node [shape="box", style="rounded"];',
        ]
        for node in nodes:
            label = _dot_escape(
                f"{node.label}\n[{node.entity_type}]\n{node.entity_id}"
            )
            lines.append(f'  {node_names[node.entity_id]} [label="{label}"];')
        for edge in edges:
            lines.append(
                f'  {node_names[edge.subject_id]} -> '
                f'{node_names[edge.object_id]} '
                f'[label="{_dot_escape(edge.predicate)}", '
                f'tooltip="{_dot_escape(edge.edge_id)}"];'
            )
        lines.append("}")
        return "\n".join(lines)


@dataclass(frozen=True)
class ExplorableSemanticObject:
    adapter_id: str
    object_type: str
    display_label: str
    source_path: Path
    semantic_object: Any


@dataclass(frozen=True)
class OntologyLoadResult:
    objects: tuple[ExplorableSemanticObject, ...]
    ignored_paths: tuple[Path, ...]
    errors: tuple[str, ...]


class OntologyObjectAdapter(Protocol):
    """Contract future semantic-object families implement for exploration."""

    adapter_id: str
    object_type: str

    def recognizes(self, payload: Mapping[str, Any]) -> bool: ...

    def deserialize(self, payload: Mapping[str, Any]) -> Any: ...

    def display_label(self, value: Any) -> str: ...

    def hierarchy(self, value: Any) -> Mapping[str, Any]: ...

    def graph(self, value: Any) -> OntologyGraph: ...

    def canonical_json(self, value: Any) -> str: ...


class DepartmentContributionExplorerAdapter:
    """Explorer projection for Department Contribution Knowledge Objects."""

    adapter_id = "department_contribution_v1"
    object_type = "department_contribution"

    def recognizes(self, payload: Mapping[str, Any]) -> bool:
        return payload.get("contribution_object_type") == self.object_type

    def deserialize(
        self, payload: Mapping[str, Any]
    ) -> DepartmentContributionKnowledgeObject:
        return DepartmentContributionKnowledgeObject.from_dict(payload)

    def display_label(
        self, value: DepartmentContributionKnowledgeObject
    ) -> str:
        return value.entity.published_name or value.entity.entity_id

    def hierarchy(
        self, value: DepartmentContributionKnowledgeObject
    ) -> Mapping[str, Any]:
        return {
            "object_identity": {
                "contribution_object_type": self.object_type,
                "contribution_object_id": value.contribution_object_id,
                "ontology_version": value.ontology_version,
                "deterministic_fingerprint": value.deterministic_fingerprint,
            },
            "governed_entity": value.entity.to_dict(),
            "temporal_scope": value.temporal_scope.to_dict(),
            "provenance": dict(value.provenance),
            "contribution_assertions": [
                _assertion_hierarchy(assertion)
                for assertion in value.assertions
            ],
        }

    def graph(
        self, value: DepartmentContributionKnowledgeObject
    ) -> OntologyGraph:
        entities = {
            value.entity.entity_id: value.entity,
        }
        for assertion in value.assertions:
            entities[assertion.subject.entity_id] = assertion.subject
            entities[assertion.object.entity_id] = assertion.object
        nodes = tuple(
            OntologyGraphNode(
                node_id=f"ontology_graph_node:{entity_id}",
                entity_id=entity_id,
                entity_type=entity.entity_type,
                label=entity.published_name or entity_id,
            )
            for entity_id, entity in sorted(entities.items())
        )
        edges = tuple(
            OntologyGraphEdge(
                edge_id=assertion.assertion_id,
                subject_id=assertion.subject.entity_id,
                predicate=assertion.predicate.value,
                object_id=assertion.object.entity_id,
                assertion_fingerprint=assertion.deterministic_fingerprint,
            )
            for assertion in value.assertions
        )
        return OntologyGraph(nodes, edges)

    def canonical_json(
        self, value: DepartmentContributionKnowledgeObject
    ) -> str:
        return value.to_json(indent=2)


class OntologyExplorerRegistry:
    """Dispatch canonical semantic objects to independently registered adapters."""

    def __init__(self, adapters: Iterable[OntologyObjectAdapter] = ()):
        self._adapters: dict[str, OntologyObjectAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    @classmethod
    def default(cls) -> "OntologyExplorerRegistry":
        return cls((DepartmentContributionExplorerAdapter(),))

    def register(self, adapter: OntologyObjectAdapter) -> None:
        if adapter.adapter_id in self._adapters:
            raise ValueError(
                f"Duplicate ontology explorer adapter: {adapter.adapter_id}"
            )
        self._adapters[adapter.adapter_id] = adapter

    def adapter_for_payload(
        self, payload: Mapping[str, Any]
    ) -> OntologyObjectAdapter | None:
        matches = tuple(
            adapter
            for adapter in self._adapters.values()
            if adapter.recognizes(payload)
        )
        if len(matches) > 1:
            raise ValueError("Multiple ontology explorer adapters recognize object")
        return matches[0] if matches else None

    def adapter(self, adapter_id: str) -> OntologyObjectAdapter:
        return self._adapters[adapter_id]

    @property
    def supported_object_types(self) -> tuple[str, ...]:
        return tuple(
            sorted({adapter.object_type for adapter in self._adapters.values()})
        )


class OntologyObjectRepository:
    """Load and validate canonical semantic objects without reconstructing them."""

    def __init__(self, registry: OntologyExplorerRegistry | None = None):
        self.registry = registry or OntologyExplorerRegistry.default()

    def load_directory(self, root: Path) -> OntologyLoadResult:
        root = Path(root)
        if not root.exists():
            return OntologyLoadResult(
                (),
                (),
                (f"Ontology object directory does not exist: {root}",),
            )
        objects = []
        ignored = []
        errors = []
        for path in sorted(root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, Mapping):
                    ignored.append(path)
                    continue
                adapter = self.registry.adapter_for_payload(payload)
                if adapter is None:
                    ignored.append(path)
                    continue
                value = adapter.deserialize(payload)
                objects.append(
                    ExplorableSemanticObject(
                        adapter_id=adapter.adapter_id,
                        object_type=adapter.object_type,
                        display_label=adapter.display_label(value),
                        source_path=path,
                        semantic_object=value,
                    )
                )
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"{path}: {exc}")
        return OntologyLoadResult(
            tuple(
                sorted(
                    objects,
                    key=lambda item: (
                        item.object_type,
                        item.display_label.casefold(),
                        str(item.source_path),
                    ),
                )
            ),
            tuple(sorted(ignored)),
            tuple(errors),
        )


def _assertion_hierarchy(assertion) -> Mapping[str, Any]:
    return {
        "assertion_identity": {
            "assertion_id": assertion.assertion_id,
            "deterministic_fingerprint": assertion.deterministic_fingerprint,
        },
        "relationship": {
            "subject": assertion.subject.to_dict(),
            "predicate": assertion.predicate.value,
            "object": assertion.object.to_dict(),
        },
        "temporal_scope": assertion.temporal_scope.to_dict(),
        "qualifiers": dict(assertion.qualifiers),
        "measures": [measure.to_dict() for measure in assertion.measures],
        "evidence_bindings": [
            {
                **binding.to_dict(),
                "evidence_fitness": list(
                    binding.provenance.get("evidence_fitness") or ()
                ),
            }
            for binding in assertion.evidence_bindings
        ],
        "provenance": dict(assertion.provenance),
    }


def _dot_escape(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )


__all__ = [
    "DepartmentContributionExplorerAdapter",
    "ExplorableSemanticObject",
    "OntologyExplorerRegistry",
    "OntologyGraph",
    "OntologyGraphEdge",
    "OntologyGraphNode",
    "OntologyLoadResult",
    "OntologyObjectAdapter",
    "OntologyObjectRepository",
]
