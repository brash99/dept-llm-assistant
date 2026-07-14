from dataclasses import dataclass
from typing import Optional, Tuple

from app.constitution.objects import (
    ConstitutionalKnowledgeObject,
    ConstitutionalType,
)
from app.knowledge import KnowledgeObject, hash_text, now_iso


@dataclass(frozen=True)
class ConstitutionalObservationRequest:
    """
    Explicit governance instruction identifying an existing Knowledge Object
    as constitutional evidence.
    """

    constitutional_type: ConstitutionalType
    principles: Tuple[str, ...] = ()
    institutional_scope: Tuple[str, ...] = ()
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None
    notes: Optional[str] = None


class ConstitutionalObserver:
    """
    Converts an explicitly selected Knowledge Object into a canonical
    ConstitutionalKnowledgeObject.

    The observer preserves the source text and provenance. It assigns a
    semantic role but does not assess alignment or derive recommendations.
    """

    def observe(
        self,
        *,
        source: KnowledgeObject,
        request: ConstitutionalObservationRequest,
    ) -> ConstitutionalKnowledgeObject:
        if not source.text.strip():
            raise ValueError(
                "A constitutional observation must contain text."
            )

        principles = tuple(
            principle.strip()
            for principle in request.principles
            if principle.strip()
        )

        institutional_scope = tuple(
            scope.strip()
            for scope in request.institutional_scope
            if scope.strip()
        )

        identity_material = "\n".join(
            [
                source.id,
                request.constitutional_type.value,
                "|".join(principles),
                request.effective_from or "",
                request.effective_until or "",
            ]
        )

        constitutional_id = (
            "constitutional:"
            + hash_text(identity_material)
        )

        metadata = dict(source.metadata or {})

        metadata.update(
            {
                "semantic_space": "constitutional",
                "constitutional_type": (
                    request.constitutional_type.value
                ),
                "principles": list(principles),
                "institutional_scope": list(
                    institutional_scope
                ),
            }
        )

        if request.notes:
            metadata["constitutional_notes"] = (
                request.notes
            )

        source_metadata = dict(
            source.source or {}
        )

        source_metadata.update(
            {
                "derived_from_knowledge_object_id": (
                    source.id
                ),
                "constitutional_observation": True,
            }
        )

        return ConstitutionalKnowledgeObject(
            id=constitutional_id,
            object_type="constitutional_knowledge",
            title=source.title,
            text=source.text,
            metadata=metadata,
            source=source_metadata,
            created_at=source.created_at,
            normalized_at=now_iso(),
            constitutional_type=(
                request.constitutional_type.value
            ),
            principles=principles,
            institutional_scope=(
                institutional_scope
            ),
            effective_from=request.effective_from,
            effective_until=request.effective_until,
            source_knowledge_object_id=source.id,
        )
