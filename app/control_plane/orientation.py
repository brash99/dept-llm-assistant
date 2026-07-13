import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import List, Optional, Set

from app.control_plane.catalog import ProgramCatalog
from app.control_plane.entities import ProgramEntity
from app.control_plane.expectations import expectations_for_program
from app.control_plane.resolver import ProgramResolution, ProgramResolver


STOP_WORDS = {
    "a",
    "an",
    "and",
    "arts",
    "bachelor",
    "degree",
    "in",
    "major",
    "of",
    "program",
    "science",
    "the",
}


def tokens(value: str) -> Set[str]:
    words = re.findall(r"[a-z0-9]+", value.casefold())
    return {word for word in words if word not in STOP_WORDS}


def program_similarity(query_name: str, program: ProgramEntity) -> float:
    """
    Provisional lexical similarity.

    This intentionally does not claim semantic equivalence. It provides a
    deterministic first-pass neighborhood that can later be replaced or
    augmented by embeddings, curricular overlap, and shared resources.
    """

    query_tokens = tokens(query_name)
    program_tokens = tokens(program.name)

    union = query_tokens | program_tokens
    intersection = query_tokens & program_tokens

    jaccard = len(intersection) / len(union) if union else 0.0

    sequence = SequenceMatcher(
        None,
        query_name.casefold(),
        program.name.casefold(),
    ).ratio()

    return 0.70 * jaccard + 0.30 * sequence


@dataclass(frozen=True)
class ProgramNeighbor:
    program: ProgramEntity
    score: float
    method: str = "lexical_v0.1"


@dataclass(frozen=True)
class ProgramOrientation:
    question: str
    resolution: ProgramResolution
    proposed_program_name: Optional[str]
    catalog_match: bool
    neighbors: List[ProgramNeighbor] = field(default_factory=list)
    expected_evidence: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ProgramOrientationService:
    def __init__(self, catalog: ProgramCatalog):
        self.catalog = catalog
        self.resolver = ProgramResolver(catalog)

    def orient(
        self,
        question: str,
        proposed_program_name: Optional[str] = None,
        neighbor_limit: int = 5,
    ) -> ProgramOrientation:
        resolution = self.resolver.resolve(question)

        comparison_name = (
            resolution.program.name
            if resolution.program is not None
            else proposed_program_name
        )

        neighbors: List[ProgramNeighbor] = []

        if comparison_name:
            for candidate in self.catalog.all():
                if (
                    resolution.program is not None
                    and candidate.id == resolution.program.id
                ):
                    continue

                score = program_similarity(comparison_name, candidate)

                if score > 0.0:
                    neighbors.append(
                        ProgramNeighbor(
                            program=candidate,
                            score=score,
                        )
                    )

            neighbors.sort(key=lambda item: item.score, reverse=True)
            neighbors = neighbors[:neighbor_limit]

        warnings: List[str] = []

        if resolution.program is not None:
            warnings.append(
                f"{resolution.program.name} is already recorded as "
                f"{resolution.program.status} in the institutional catalog."
            )
        elif proposed_program_name:
            warnings.append(
                f"{proposed_program_name} was not found as an exact program "
                "name or alias in the institutional catalog."
            )
        else:
            warnings.append(
                "No program entity could be resolved from the question. "
                "Supply a proposed program name for neighborhood analysis."
            )

        return ProgramOrientation(
            question=question,
            resolution=resolution,
            proposed_program_name=proposed_program_name,
            catalog_match=resolution.found,
            neighbors=neighbors,
            expected_evidence=expectations_for_program().categories,
            warnings=warnings,
        )
