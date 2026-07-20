import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from app.control_plane.concepts import InstitutionalConcept
from app.control_plane.entities import ProgramEntity
from app.control_plane.resolver import ProgramResolution, ProgramResolver
from app.control_plane.semantic_neighbors import (
    SemanticProgramNeighbor,
    SemanticProgramNeighborhoodService,
)
from app.question_scope import QuestionScopeAssessment, classify_question_scope


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
    question_scope: QuestionScopeAssessment = field(
        default_factory=lambda: classify_question_scope("")
    )

    @property
    def has_resolved_entities(self) -> bool:
        return bool(self.resolved_entities)

    @property
    def has_proposed_concepts(self) -> bool:
        return bool(self.proposed_concepts)


class ProposedProgramConceptExtractor:
    """
    Deterministically identify proposed academic-program concepts.

    The extractor intentionally recognizes only explicit proposal language.
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
        r"\boffer(?:ed|s|ing)?\b",
        r"\bexpand(?:ed|s|ing)?\b",
        r"\bnew\b",
    )

    _PROGRAM_PATTERN = re.compile(
        r"""
        \b(?:
            start(?:ing)?|
            create(?:d|s|ing)?|
            establish(?:ed|es|ing)?|
            launch(?:ed|es|ing)?|
            add(?:ed|s|ing)?|
            develop(?:ed|s|ing)?|
            introduce(?:d|s|ing)?|
            propose(?:d|s|ing)?|
            offer(?:ed|s|ing)?|
            expand(?:ed|s|ing)?|
            new
        )\b
        \s+
        (?:(?:a|an|the|new)\s+)?
        (?P<name>
            [A-Za-z][A-Za-z&/\-]*(?:
                \s+[A-Za-z][A-Za-z&/\-]*
            ){0,6}?
        )
        \s+
        (?:academic\s+)?
        (?P<structure>program|major|concentration|certificate|track|specialization|pathway)\b
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

        if not self._contains_proposal_language(question):
            return []

        concepts: List[InstitutionalConcept] = []

        for match in self._PROGRAM_PATTERN.finditer(question):
            raw_name = match.group("name")
            structure = match.group("structure").casefold()
            concept_type = {
                "program": "academic_program",
                "major": "academic_program",
                "concentration": "academic_concentration",
                "certificate": "academic_certificate",
                "track": "academic_track",
                "specialization": "academic_specialization",
                "pathway": "academic_pathway",
            }[structure]
            cleaned_name = self._clean_name(raw_name)

            if not cleaned_name:
                continue

            concept = InstitutionalConcept(
                name=cleaned_name,
                concept_type=concept_type,
                asserted=False,
                confidence=0.85,
                extraction_method="explicit_academic_structure_v0.5",
            )

            if self._duplicates_resolved_entity(concept, resolution):
                continue

            concepts.append(concept)

        return self._deduplicate(concepts)

    @staticmethod
    def _duplicates_resolved_entity(
        concept: InstitutionalConcept,
        resolution: ProgramResolution,
    ) -> bool:
        """Avoid relabeling the resolved catalog entity as a proposal."""
        if not resolution.found or resolution.program is None:
            return False

        asserted_names = {
            resolution.program.name.casefold(),
            *(alias.casefold() for alias in resolution.program.aliases),
        }
        return concept.name.casefold() in asserted_names

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
    Produce an InstitutionalOrientation from catalog and semantic services.

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
        question_scope = classify_question_scope(clean_question)

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
            question_scope=question_scope,
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
            structure_label = concept.concept_type.removeprefix(
                "academic_"
            ).replace("_", " ")
            parts.append(
                f"Proposed academic {structure_label} concept: {concept.name}."
            )

        return "\n".join(parts)

    def _build_notes(
        self,
        resolution: ProgramResolution,
        proposed_concepts: Sequence[InstitutionalConcept],
    ) -> List[str]:
        notes: List[str] = []

        if resolution.found and resolution.program is not None:
            notes.append(
                "The question explicitly references an existing program "
                "in the asserted institutional catalog."
            )

        if proposed_concepts:
            notes.append(
                "The question references a proposed academic program that "
                "is not asserted as an existing program in the catalog."
            )

        if notes:
            return notes

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
