import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from app.control_plane.concepts import InstitutionalConcept
from app.control_plane.entities import ProgramEntity
from app.control_plane.resolver import ProgramResolution, ProgramResolver
from app.control_plane.semantic_neighbors import (
    SemanticProgramNeighbor,
    SemanticProgramNeighborhoodService,
)


@dataclass(frozen=True)
class InstitutionalOrientation:
    """
    Contract produced by the Semantic Control Plane before retrieval begins.

    The contract distinguishes asserted institutional entities from concepts
    derived from the user's question.
    """

    question: str
    resolved_entities: Tuple[ProgramEntity, ...]
    proposed_concepts: Tuple[InstitutionalConcept, ...]
    semantic_neighbors: Tuple[SemanticProgramNeighbor, ...]
    resolution: ProgramResolution
    confidence: float
    notes: Tuple[str, ...]

    @property
    def has_resolved_entities(self) -> bool:
        return bool(self.resolved_entities)

    @property
    def has_proposed_concepts(self) -> bool:
        return bool(self.proposed_concepts)


class ProposedProgramConceptExtractor:
    """
    Deterministically identify proposed academic-program concepts.

    Version 0.1 intentionally recognizes only explicit proposal language.
    It does not use an LLM and does not fabricate ProgramEntity records.
    """

    _ACTION_PATTERNS: Sequence[str] = (
        r"\bstart(?:ing)?\b",
        r"\bcreate(?:d|s|ing)?\b",
        r"\bestablish(?:ed|es|ing)?\b",
        r"\blaunch(?:ed|es|ing)?\b",
        r"\badd(?:ed|s|ing)?\b",
        r"\bdevelop(?:ed|s|ing)?\b",
        r"\bintroduce(?:d|s|ing)?\b",
        r"\bpropose(?:d|s|ing)?\b",
        r"\bnew\b",
    )

    _PROGRAM_PATTERN = re.compile(
        r"""
        (?P<name>
            [A-Za-z][A-Za-z&/\-]*(?:
                \s+[A-Za-z][A-Za-z&/\-]*
            ){0,6}
        )
        \s+
        program\b
        """,
        flags=re.IGNORECASE | re.VERBOSE,
    )

    _LEADING_NOISE = re.compile(
        r"""
        ^(?:
            what|
            which|
            where|
            when|
            why|
            how|
            if|
            we|
            the|
            a|
            an|
            additional|
            resources?|
            would|
            be|
            required|
            needed|
            need|
            to|
            for|
            should|
            could|
            might|
            start|
            starting|
            create|
            creating|
            establish|
            establishing|
            launch|
            launching|
            add|
            adding|
            develop|
            developing|
            introduce|
            introducing|
            propose|
            proposing|
            new|
            university|
            institution
        )\s+
        """,
        flags=re.IGNORECASE | re.VERBOSE,
    )

    def extract(
        self,
        question: str,
        resolution: ProgramResolution,
    ) -> List[InstitutionalConcept]:
        if resolution.found:
            return []

        if not self._contains_proposal_language(question):
            return []

        concepts: List[InstitutionalConcept] = []

        for match in self._PROGRAM_PATTERN.finditer(question):
            raw_name = match.group("name")
            cleaned_name = self._clean_name(raw_name)

            if not cleaned_name:
                continue

            concepts.append(
                InstitutionalConcept(
                    name=cleaned_name,
                    concept_type="academic_program",
                    asserted=False,
                    confidence=0.85,
                    extraction_method="explicit_proposed_program_v0.1",
                )
            )

        return self._deduplicate(concepts)

    def _contains_proposal_language(self, question: str) -> bool:
        return any(
            re.search(pattern, question, flags=re.IGNORECASE)
            for pattern in self._ACTION_PATTERNS
        )

    def _clean_name(self, value: str) -> str:
        words = value.strip().split()

        while words:
            candidate = " ".join(words)
            cleaned = self._LEADING_NOISE.sub("", candidate, count=1)

            if cleaned == candidate:
                break

            words = cleaned.split()

        if not words:
            return ""

        return " ".join(
            word.upper()
            if word.casefold() in {"ai", "it"}
            else word.capitalize()
            for word in words
        )

    def _deduplicate(
        self,
        concepts: Sequence[InstitutionalConcept],
    ) -> List[InstitutionalConcept]:
        seen = set()
        deduplicated: List[InstitutionalConcept] = []

        for concept in concepts:
            key = (concept.concept_type, concept.name.casefold())

            if key in seen:
                continue

            seen.add(key)
            deduplicated.append(concept)

        return deduplicated


class ProgramOrientationService:
    """
    Produce an InstitutionalOrientation from the Sprint 1 program services.

    This service remains advisory. It executes before retrieval but does not
    yet modify the retrieval query or ranking.
    """

    def __init__(
        self,
        resolver: ProgramResolver,
        neighborhood_service: SemanticProgramNeighborhoodService,
        concept_extractor: Optional[ProposedProgramConceptExtractor] = None,
        neighbor_limit: int = 5,
    ) -> None:
        self.resolver = resolver
        self.neighborhood_service = neighborhood_service
        self.concept_extractor = (
            concept_extractor or ProposedProgramConceptExtractor()
        )
        self.neighbor_limit = neighbor_limit

    def orient(self, question: str) -> InstitutionalOrientation:
        clean_question = question.strip()

        if not clean_question:
            raise ValueError("Question must not be empty.")

        resolution = self.resolver.resolve(clean_question)

        resolved_entities: List[ProgramEntity] = []
        if resolution.found and resolution.program is not None:
            resolved_entities.append(resolution.program)

        proposed_concepts = self.concept_extractor.extract(
            question=clean_question,
            resolution=resolution,
        )

        semantic_query = self._build_semantic_query(
            question=clean_question,
            resolved_entities=resolved_entities,
            proposed_concepts=proposed_concepts,
        )

        excluded_program_id = (
            resolution.program.id
            if resolution.found and resolution.program is not None
            else None
        )

        neighbors = self.neighborhood_service.neighbors(
            query_text=semantic_query,
            exclude_program_id=excluded_program_id,
            limit=self.neighbor_limit,
        )

        notes = self._build_notes(
            resolution=resolution,
            proposed_concepts=proposed_concepts,
        )

        confidence = self._derive_confidence(
            resolution=resolution,
            proposed_concepts=proposed_concepts,
        )

        return InstitutionalOrientation(
            question=clean_question,
            resolved_entities=tuple(resolved_entities),
            proposed_concepts=tuple(proposed_concepts),
            semantic_neighbors=tuple(neighbors),
            resolution=resolution,
            confidence=confidence,
            notes=tuple(notes),
        )

    def _build_semantic_query(
        self,
        question: str,
        resolved_entities: Sequence[ProgramEntity],
        proposed_concepts: Sequence[InstitutionalConcept],
    ) -> str:
        parts = [question]

        for entity in resolved_entities:
            parts.append(f"Resolved existing academic program: {entity.name}.")

        for concept in proposed_concepts:
            parts.append(
                f"Proposed academic program concept: {concept.name}."
            )

        return "\n".join(parts)

    def _build_notes(
        self,
        resolution: ProgramResolution,
        proposed_concepts: Sequence[InstitutionalConcept],
    ) -> List[str]:
        if resolution.found and resolution.program is not None:
            return [
                (
                    "The question explicitly references an existing program "
                    "in the asserted institutional catalog."
                )
            ]

        if proposed_concepts:
            return [
                (
                    "The question references a proposed academic program that "
                    "is not asserted as an existing program in the catalog."
                )
            ]

        return [
            (
                "No existing or explicitly proposed academic program was "
                "identified."
            )
        ]

    def _derive_confidence(
        self,
        resolution: ProgramResolution,
        proposed_concepts: Sequence[InstitutionalConcept],
    ) -> float:
        if resolution.found:
            return resolution.confidence

        if proposed_concepts:
            return max(
                concept.confidence
                for concept in proposed_concepts
            )

        return 0.0
