from pathlib import Path
from typing import Dict, Iterable, List, Optional

from app.constitution.objects import (
    ConstitutionalKnowledgeObject,
    ConstitutionalType,
)
from app.knowledge import load_knowledge_object


class ConstitutionalCatalog:
    def __init__(
        self,
        objects: Iterable[ConstitutionalKnowledgeObject],
    ) -> None:
        self._objects = list(objects)
        self._by_id: Dict[
            str,
            ConstitutionalKnowledgeObject,
        ] = {}

        for obj in self._objects:
            if obj.id in self._by_id:
                raise ValueError(
                    f"Duplicate constitutional object ID: {obj.id}"
                )

            self._by_id[obj.id] = obj

    @classmethod
    def from_directory(
        cls,
        directory: Path,
    ) -> "ConstitutionalCatalog":
        directory = Path(directory)

        if not directory.exists():
            return cls([])

        objects: List[
            ConstitutionalKnowledgeObject
        ] = []

        for path in sorted(directory.glob("*.json")):
            loaded = load_knowledge_object(path)

            if isinstance(
                loaded,
                ConstitutionalKnowledgeObject,
            ):
                objects.append(loaded)

        return cls(objects)

    def all(
        self,
    ) -> List[ConstitutionalKnowledgeObject]:
        return list(self._objects)

    def get(
        self,
        object_id: str,
    ) -> Optional[ConstitutionalKnowledgeObject]:
        return self._by_id.get(object_id)

    def by_type(
        self,
        constitutional_type: ConstitutionalType,
    ) -> List[ConstitutionalKnowledgeObject]:
        return [
            obj
            for obj in self._objects
            if obj.constitutional_type
            == constitutional_type.value
        ]

    def by_principle(
        self,
        principle: str,
    ) -> List[ConstitutionalKnowledgeObject]:
        target = principle.casefold().strip()

        return [
            obj
            for obj in self._objects
            if any(
                item.casefold() == target
                for item in obj.principles
            )
        ]

    def __len__(self) -> int:
        return len(self._objects)
