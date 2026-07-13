from dataclasses import dataclass
from typing import Iterable, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from app.control_plane.entities import ProgramEntity


@dataclass(frozen=True)
class SemanticProgramNeighbor:
    program: ProgramEntity
    score: float
    method: str = "semantic_embedding_v0.1"


def build_program_semantic_text(program: ProgramEntity) -> str:
    """
    Construct the text used to represent a program in embedding space.

    Only factual catalog fields are included. No recommendation or inferred
    relationship is stored in the ProgramEntity itself.
    """
    parts = [
        f"Academic program: {program.name}.",
    ]

    if program.degree_type:
        parts.append(f"Degree type: {program.degree_type}.")

    if program.department:
        parts.append(f"Department: {program.department}.")

    if program.school:
        parts.append(f"School: {program.school}.")

    if program.accreditation:
        parts.append(
            "Accreditation: "
            + ", ".join(program.accreditation)
            + "."
        )

    if program.aliases:
        parts.append(
            "Known aliases: "
            + ", ".join(program.aliases)
            + "."
        )

    return " ".join(parts)


class SemanticProgramNeighborhoodService:
    """
    Derive program neighborhoods using the same type of embedding model used
    elsewhere in ISO.

    This service remains advisory. It does not modify retrieval.
    """

    def __init__(
        self,
        programs: Iterable[ProgramEntity],
        model_name: str,
        device: str = "cuda",
    ) -> None:
        self.programs = list(programs)
        self.model_name = model_name
        self.device = device

        self.model = SentenceTransformer(
            model_name,
            device=device,
        )

        program_texts = [
            build_program_semantic_text(program)
            for program in self.programs
        ]

        self.program_embeddings = self.model.encode(
            program_texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    def neighbors(
        self,
        query_text: str,
        exclude_program_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[SemanticProgramNeighbor]:
        if not query_text.strip():
            return []

        query_embedding = self.model.encode(
            [query_text],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]

        scores = np.dot(
            self.program_embeddings,
            query_embedding,
        )

        ranked: List[SemanticProgramNeighbor] = []

        for program, score in zip(self.programs, scores):
            if (
                exclude_program_id is not None
                and program.id == exclude_program_id
            ):
                continue

            ranked.append(
                SemanticProgramNeighbor(
                    program=program,
                    score=float(score),
                )
            )

        ranked.sort(
            key=lambda item: item.score,
            reverse=True,
        )

        return ranked[:limit]
