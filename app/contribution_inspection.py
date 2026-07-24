"""Developer rendering for direct inspection of contribution ontology objects."""

from __future__ import annotations

import json
from typing import Iterable

from app.contribution_ontology import ContributionKnowledgeObject


class ContributionOntologyInspector:
    """Render ontology structure without adding analysis or institutional facts."""

    def render(
        self,
        value: ContributionKnowledgeObject,
        *,
        include_canonical_json: bool = True,
    ) -> str:
        lines = [
            "=" * 78,
            "CONTRIBUTION KNOWLEDGE OBJECT",
            "=" * 78,
            f"Object ID: {value.contribution_object_id}",
            f"Object class: {type(value).__name__}",
            (
                f"Governed entity: {value.entity.entity_id} "
                f"({value.entity.published_name or value.entity.entity_type})"
            ),
            f"Entity type: {value.entity.entity_type}",
            f"Ontology version: {value.ontology_version}",
            f"Fingerprint: {value.deterministic_fingerprint}",
            "",
            "TEMPORAL SCOPE",
            json.dumps(
                value.temporal_scope.to_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            "",
            "PROVENANCE",
            json.dumps(
                dict(value.provenance),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            "",
            f"ASSERTIONS ({len(value.assertions)})",
        ]
        for index, assertion in enumerate(value.assertions, start=1):
            lines.extend(
                (
                    "",
                    f"[{index}] {assertion.assertion_id}",
                    (
                        f"    {assertion.subject.entity_id} "
                        f"--{assertion.predicate.value}--> "
                        f"{assertion.object.entity_id}"
                    ),
                    f"    Object label: {assertion.object.published_name or ''}",
                    (
                        "    Assertion fingerprint: "
                        f"{assertion.deterministic_fingerprint}"
                    ),
                    "    Temporal scope:",
                    _indent_json(assertion.temporal_scope.to_dict(), 8),
                    "    Qualifiers:",
                    _indent_json(dict(assertion.qualifiers), 8),
                    "    Provenance:",
                    _indent_json(dict(assertion.provenance), 8),
                    f"    Measures ({len(assertion.measures)}):",
                )
            )
            if assertion.measures:
                for measure in assertion.measures:
                    lines.extend(
                        (
                            (
                                f"      - {measure.measure_type}: "
                                f"{measure.value} {measure.unit}"
                            ),
                            f"        ID: {measure.measure_id}",
                            f"        Definition: {measure.definition}",
                            (
                                "        Qualifiers: "
                                f"{_compact_json(dict(measure.qualifiers))}"
                            ),
                            (
                                "        Limitations: "
                                f"{_compact_json(list(measure.limitations))}"
                            ),
                            (
                                "        Evidence bindings: "
                                f"{', '.join(measure.evidence_binding_ids) or 'none'}"
                            ),
                        )
                    )
            else:
                lines.append("      (none)")
            lines.append(
                f"    Evidence bindings ({len(assertion.evidence_bindings)}):"
            )
            for binding in assertion.evidence_bindings:
                fitness = binding.provenance.get("evidence_fitness") or ()
                lines.extend(
                    (
                        f"      - {binding.binding_id}",
                        (
                            f"        Builder: {binding.builder} "
                            f"v{binding.builder_version}"
                        ),
                        f"        Derivation: {binding.derivation_basis}",
                        (
                            "        Source references: "
                            f"{_compact_json(list(binding.source_references))}"
                        ),
                        (
                            "        Source fingerprints: "
                            f"{_compact_json(dict(binding.source_fingerprints))}"
                        ),
                        (
                            "        Evidence fitness: "
                            f"{_compact_json(list(fitness))}"
                        ),
                        "        Provenance:",
                        _indent_json(dict(binding.provenance), 10),
                    )
                )
        if include_canonical_json:
            lines.extend(
                (
                    "",
                    "CANONICAL JSON SERIALIZATION",
                    value.to_json(indent=2),
                )
            )
        return "\n".join(lines) + "\n"

    def structural_signature(
        self, value: ContributionKnowledgeObject
    ) -> dict[str, object]:
        """Return a non-evaluative index of the object's ontology structure."""

        predicates: dict[str, int] = {}
        object_types: dict[str, int] = {}
        for assertion in value.assertions:
            predicate = assertion.predicate.value
            predicates[predicate] = predicates.get(predicate, 0) + 1
            entity_type = assertion.object.entity_type
            object_types[entity_type] = object_types.get(entity_type, 0) + 1
        return {
            "contribution_object_id": value.contribution_object_id,
            "entity_id": value.entity.entity_id,
            "assertion_count": len(value.assertions),
            "predicate_counts": dict(sorted(predicates.items())),
            "object_type_counts": dict(sorted(object_types.items())),
            "deterministic_fingerprint": value.deterministic_fingerprint,
        }

    def compare_structure(
        self, values: Iterable[ContributionKnowledgeObject]
    ) -> tuple[dict[str, object], ...]:
        return tuple(
            self.structural_signature(value)
            for value in sorted(values, key=lambda item: item.entity.entity_id)
        )


def _compact_json(value) -> str:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def _indent_json(value, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(
        prefix + line
        for line in json.dumps(
            value, ensure_ascii=False, indent=2, sort_keys=True
        ).splitlines()
    )


__all__ = ["ContributionOntologyInspector"]
