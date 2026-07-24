"""Adapt undergraduate catalog PDFs into factual semantic observations.

Phase 1 records publication metadata, published academic units, department
faculty rosters, and the university faculty registry. It deliberately does not
extract curricula, courses, requirements, policies, or derive employment and
organizational conclusions.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

import fitz

from app.knowledge import KnowledgeObject, save_knowledge_object


ADAPTER_NAME = "academic_catalog_adapter"
ADAPTER_VERSION = "0.1"

CATALOG_OBJECT_TYPE = "catalog_observation"
ACADEMIC_UNIT_OBJECT_TYPE = "academic_unit_observation"
ROSTER_OBJECT_TYPE = "department_faculty_roster_observation"
CATALOG_FACULTY_OBJECT_TYPE = "catalog_faculty_observation"

# The 2022-23 PDF embeds small-cap Latin glyphs behind Malayalam code points.
# This is a deterministic text-decoding correction, not semantic inference.
PDF_SMALL_CAP_TRANSLATION = str.maketrans(
    {
        "ൾ": "e",
        "ඉ": "p",
        "ൺ": "a",
        "උ": "r",
        "ඍ": "t",
        "ආ": "m",
        "ඇ": "n",
        "ඈ": "o",
        "ൿ": "f",
        "ං": "i",
        "඄": "k",
        "අ": "l",
        "඀": "g",
        "ඒ": "y",
        "ඁ": "h",
        "ඌ": "s",
        "ർ": "c",
        "ඎ": "u",
        "ൽ": "d",
        "ඏ": "v",
    }
)

ROSTER_CATEGORY = re.compile(
    r"^(?P<category>Distinguished Professor|Professor|Associate Professor|"
    r"Assistant Professors?|Master Lecturer|Senior Lecturer|Lecturer|"
    r"Instructor|Research Scientist|Post[- ]?Doctoral Fellow|Emeriti|Emeritus)"
    r":\s*(?P<names>.*)$",
    re.IGNORECASE,
)
ROSTER_STOP = re.compile(
    r"^(?:Mission(?: Statement)?|Vision|Health-Related Professions|"
    r"Bachelor|The Curriculum|Equipment|Research Projects|Professional "
    r"Collaboration|NASM Accreditation)\b",
    re.IGNORECASE,
)
LEADERSHIP = re.compile(
    r"\b(?:Chair|Dean|Director|Associate Dean|Assistant Dean)\b", re.IGNORECASE
)
ACADEMIC_UNIT_START = re.compile(
    r"^(?:The )?(?:Department of |School of |Neuroscience Program$|"
    r"Honors Program$|Joseph W\. Luter, III School of Business$|"
    r".+ Department$)",
    re.IGNORECASE,
)
DEGREE_MARKER = re.compile(
    r"\b(?:A\.A\.|A\.B\.|B\.A\.|B\.S\.|B\.Sc\.|B\.F\.A\.|B\.M\.|"
    r"B\.M\.E\.|B\.B\.A\.|M\.A\.|M\.S\.|M\.Sc\.|M\.Ed\.|M\.F\.A\.|"
    r"M\.M\.|M\.B\.A\.|M\.Eng\.|Ph\.D\.|D\.M\.A\.|J\.D\.|"
    r"Dipl\.-Ing|ABD)"
)


def _normalize(value: str) -> str:
    value = value.translate(PDF_SMALL_CAP_TRANSLATION)
    value = value.replace("\u00ad", "")
    return " ".join(value.split())


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _catalog_year(path: Path) -> str:
    match = re.search(r"(?P<start>20\d{2})-(?P<end>\d{2})", path.stem)
    if match is None:
        raise ValueError(f"Catalog filename does not contain an academic year: {path}")
    return f"{match.group('start')}-{match.group('end')}"


def _stable_id(object_type: str, catalog_year: str, *identity: str) -> str:
    payload = json.dumps(
        [object_type, catalog_year, *identity],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _page_lines(page: fitz.Page) -> list[str]:
    return [
        value
        for raw in page.get_text("text").splitlines()
        for value in [_normalize(raw)]
        if value
    ]


def _is_header_noise(value: str, catalog_year: str) -> bool:
    return (
        value.isdigit()
        or value in {catalog_year, "Faculty", "FACULTY"}
        or re.fullmatch(r"20\d{2}-20\d{2}", value) is not None
    )


def _joined_unit_candidates(
    lines: Sequence[str], stop_index: int
) -> list[Tuple[int, str]]:
    candidates = []
    index = 0
    while index < stop_index:
        line = lines[index]
        if not ACADEMIC_UNIT_START.match(line):
            index += 1
            continue
        line = re.sub(r"^The\s+", "", line, flags=re.IGNORECASE)
        parts = [line]
        cursor = index + 1
        needs_continuation = bool(
            re.search(r"(?:\band|\bof|\bClassical|\bArt)$", line)
        )
        while cursor < stop_index and needs_continuation:
            following = lines[cursor]
            if (
                LEADERSHIP.search(following)
                or following == "Faculty"
                or ROSTER_CATEGORY.match(following)
                or "@" in following
                or re.search(r"\(\d{3}\)\s*\d", following)
            ):
                break
            if len(parts) >= 2 or len(following) > 60:
                break
            if following.startswith(("Department of ", "School of ")):
                break
            parts.append(following)
            cursor += 1
        candidates.append((index, " ".join(parts)))
        index = max(cursor, index + 1)
    return candidates


def _fallback_page_topic(lines: Sequence[str], catalog_year: str) -> Optional[str]:
    for line in reversed(lines):
        if _is_header_noise(line, catalog_year):
            continue
        if (
            "@" in line
            or LEADERSHIP.search(line)
            or re.search(r"\(\d{3}\)\s*\d", line)
            or re.search(r"\b(?:Hall|Center|Building|Room)\b", line)
        ):
            continue
        if len(line) <= 100 and not line.endswith(('.', ';', ':')):
            return line
    return None


@dataclass(frozen=True)
class CatalogFacultyRosterEntry:
    published_name: str
    published_category: str


@dataclass
class CatalogObservation(KnowledgeObject):
    observation_id: str = ""
    catalog_year: str = ""
    publication_title: str = ""
    publication_designation: Optional[str] = None
    publication_date: Optional[str] = None
    source_filename: str = ""
    relative_source_path: str = ""
    document_hash: str = ""
    page_count: int = 0
    provenance: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_observation(self, CATALOG_OBJECT_TYPE)


@dataclass
class AcademicUnitObservation(KnowledgeObject):
    observation_id: str = ""
    catalog_year: str = ""
    published_name: str = ""
    published_parent_unit: Optional[str] = None
    published_leadership: Tuple[str, ...] = field(default_factory=tuple)
    introductory_description: Optional[str] = None
    page_numbers: Tuple[int, ...] = field(default_factory=tuple)
    source_filename: str = ""
    relative_source_path: str = ""
    document_hash: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_observation(self, ACADEMIC_UNIT_OBJECT_TYPE)
        self.published_leadership = tuple(self.published_leadership)
        self.page_numbers = tuple(self.page_numbers)


@dataclass
class DepartmentFacultyRosterObservation(KnowledgeObject):
    observation_id: str = ""
    catalog_year: str = ""
    academic_unit: str = ""
    entries: Tuple[CatalogFacultyRosterEntry, ...] = field(default_factory=tuple)
    page_numbers: Tuple[int, ...] = field(default_factory=tuple)
    source_filename: str = ""
    relative_source_path: str = ""
    document_hash: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_observation(self, ROSTER_OBJECT_TYPE)
        self.entries = tuple(
            value
            if isinstance(value, CatalogFacultyRosterEntry)
            else CatalogFacultyRosterEntry(**value)
            for value in self.entries
        )
        self.page_numbers = tuple(self.page_numbers)


@dataclass
class CatalogFacultyObservation(KnowledgeObject):
    observation_id: str = ""
    catalog_year: str = ""
    published_name: str = ""
    published_title: Optional[str] = None
    academic_unit: Optional[str] = None
    education: Optional[str] = None
    appointment_year: Optional[str] = None
    published_entry_text: str = ""
    page_numbers: Tuple[int, ...] = field(default_factory=tuple)
    source_filename: str = ""
    relative_source_path: str = ""
    document_hash: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_observation(self, CATALOG_FACULTY_OBJECT_TYPE)
        self.page_numbers = tuple(self.page_numbers)


def _validate_observation(observation: KnowledgeObject, object_type: str) -> None:
    if observation.object_type != object_type:
        raise ValueError(f"object_type must be {object_type!r}")
    if not getattr(observation, "observation_id", ""):
        raise ValueError("observation_id is required")
    if observation.id != getattr(observation, "observation_id"):
        raise ValueError("id and observation_id must contain the same stable ID")
    if not getattr(observation, "catalog_year", ""):
        raise ValueError("catalog_year is required")


CATALOG_CLASSES = {
    CATALOG_OBJECT_TYPE: CatalogObservation,
    ACADEMIC_UNIT_OBJECT_TYPE: AcademicUnitObservation,
    ROSTER_OBJECT_TYPE: DepartmentFacultyRosterObservation,
    CATALOG_FACULTY_OBJECT_TYPE: CatalogFacultyObservation,
}


def catalog_observation_from_dict(data: Dict[str, Any]) -> KnowledgeObject:
    cls = CATALOG_CLASSES[str(data.get("object_type"))]
    return cls(**dict(data))


@dataclass
class CatalogAdaptationResult:
    observations: list[KnowledgeObject] = field(default_factory=list)
    files_discovered: int = 0
    files_processed: int = 0
    files_failed: int = 0
    failures: list[Dict[str, str]] = field(default_factory=list)
    objects_by_type: Counter[str] = field(default_factory=Counter)
    duplicate_observation_ids: int = 0
    roster_entries: int = 0
    registry_entries: int = 0


class CatalogAdapter:
    """Process all catalog PDFs in a directory as longitudinal evidence."""

    def __init__(self, source_directory: Path) -> None:
        self.source_directory = Path(source_directory)
        if not self.source_directory.is_dir():
            raise FileNotFoundError(
                f"Catalog source directory not found: {self.source_directory}"
            )

    @staticmethod
    def _provenance(
        path: Path,
        catalog_year: str,
        document_hash: str,
        page_numbers: Sequence[int],
    ) -> Dict[str, Any]:
        return {
            "catalog_year": catalog_year,
            "source_filename": path.name,
            "relative_source_path": _relative_path(path),
            "source_sha256": document_hash,
            "page_numbers": list(page_numbers),
            "adapter": ADAPTER_NAME,
            "adapter_version": ADAPTER_VERSION,
            "source_type": "institutional_academic_catalog",
        }

    def _catalog_metadata(
        self,
        path: Path,
        document: fitz.Document,
        year: str,
        document_hash: str,
        normalized_at: str,
    ) -> CatalogObservation:
        first_lines = _page_lines(document[0])
        designation = next(
            (line for line in first_lines if line.startswith("Volume ")), None
        )
        publication_date = None
        if designation:
            match = re.search(
                r"\b(?:January|February|March|April|May|June|July|August|"
                r"September|October|November|December)\s+20\d{2}\b",
                designation,
            )
            publication_date = match.group(0) if match else None
        metadata_title = _normalize(str((document.metadata or {}).get("title") or ""))
        publication_title = metadata_title or next(
            (line for line in first_lines if "Catalog" in line),
            path.stem,
        )
        observation_id = _stable_id(CATALOG_OBJECT_TYPE, year, document_hash)
        provenance = self._provenance(path, year, document_hash, (1,))
        return CatalogObservation(
            id=observation_id,
            object_type=CATALOG_OBJECT_TYPE,
            title=publication_title,
            text=f"Academic catalog observation\nCatalog year: {year}",
            metadata={"semantic_layer": CATALOG_OBJECT_TYPE},
            source={
                "kind": "institutional_academic_catalog",
                "path": _relative_path(path),
                "content_hash": document_hash,
            },
            normalized_at=normalized_at,
            observation_id=observation_id,
            catalog_year=year,
            publication_title=publication_title,
            publication_designation=designation,
            publication_date=publication_date,
            source_filename=path.name,
            relative_source_path=_relative_path(path),
            document_hash=document_hash,
            page_count=document.page_count,
            provenance=provenance,
        )

    @staticmethod
    def _parse_roster_blocks(
        lines: Sequence[str], catalog_year: str
    ) -> list[Tuple[int, Optional[str], list[CatalogFacultyRosterEntry]]]:
        blocks = []
        index = 0
        while index < len(lines):
            match = ROSTER_CATEGORY.match(lines[index])
            if match is None:
                index += 1
                continue
            start = index
            categories: list[Tuple[str, list[str]]] = []
            while index < len(lines):
                match = ROSTER_CATEGORY.match(lines[index])
                if match:
                    categories.append(
                        (match.group("category"), [match.group("names")])
                    )
                    index += 1
                    continue
                line = lines[index]
                if (
                    ROSTER_STOP.match(line)
                    or ACADEMIC_UNIT_START.match(line)
                    or LEADERSHIP.search(line)
                    or line == "Faculty"
                    or "@" in line
                ):
                    break
                if not categories or _is_header_noise(line, catalog_year):
                    index += 1
                    continue
                if len(line) > 100 or line.endswith("."):
                    break
                categories[-1][1].append(line)
                index += 1
            entries = []
            for category, fragments in categories:
                names = " ".join(fragments)
                for name in names.split(","):
                    published_name = _normalize(name)
                    if published_name:
                        entries.append(
                            CatalogFacultyRosterEntry(
                                published_name=published_name,
                                published_category=category,
                            )
                        )
            blocks.append((start, None, entries))
            if index == start:
                index += 1
        return blocks

    def _department_observations(
        self,
        path: Path,
        document: fitz.Document,
        year: str,
        document_hash: str,
        normalized_at: str,
    ) -> list[KnowledgeObject]:
        observations: list[KnowledgeObject] = []
        units: Dict[str, Dict[str, Any]] = {}
        rosters = []

        for page_index, page in enumerate(document):
            lines = _page_lines(page)
            blocks = self._parse_roster_blocks(lines, year)
            if not blocks:
                continue
            first_block = blocks[0][0]
            all_candidates = _joined_unit_candidates(lines, len(lines))
            stop_positions = [
                index for index, line in enumerate(lines) if ROSTER_STOP.match(line)
            ]
            first_stop = min(stop_positions) if stop_positions else len(lines)
            candidates = [
                item
                for item in all_candidates
                if (
                    item[0] < first_block
                    or item[0] >= max(0, len(lines) - 12)
                    or (
                        first_block < item[0] < first_stop
                        and not lines[item[0]].startswith("The ")
                    )
                )
            ]
            page_topic = _fallback_page_topic(lines, year)

            # Preserve explicit parent schools here. Roster-owning units are
            # added below; this prevents layout-like prose and footer headings
            # from becoming academic-unit observations.
            for candidate_index, (position, name) in enumerate(candidates):
                next_position = (
                    candidates[candidate_index + 1][0]
                    if candidate_index + 1 < len(candidates)
                    else first_stop
                )
                leadership = tuple(
                    line
                    for line in lines[position + 1 : next_position]
                    if LEADERSHIP.search(line)
                )
                parent = next(
                    (
                        prior_name
                        for prior_position, prior_name in reversed(candidates)
                        if prior_position < position
                        and prior_name.startswith("School of ")
                    ),
                    None,
                )
                if "School of " in name:
                    units.setdefault(
                        name,
                        {
                            "page": page_index + 1,
                            "leadership": leadership,
                            "parent": parent,
                        },
                    )

            previous_block_start = -1
            for block_start, _unused, entries in blocks:
                preceding = [item for item in candidates if item[0] < block_start]
                following = [item for item in candidates if item[0] > block_start]
                recent = [
                    item for item in preceding if item[0] > previous_block_start
                ]
                parent_school = next(
                    (
                        name
                        for _position, name in reversed(preceding)
                        if "School of " in name
                    ),
                    None,
                )
                recent_departments = [
                    name
                    for _position, name in recent
                    if name.startswith("Department of ")
                    or name.endswith(" Department")
                ]
                if len(recent_departments) > 1 and parent_school:
                    unit_name = parent_school
                else:
                    unit_name = recent[-1][1] if recent else (
                        preceding[-1][1] if preceding else (
                            following[0][1] if following else page_topic
                        )
                    )
                if not unit_name:
                    continue
                rosters.append((unit_name, page_index + 1, entries))
                unit_position = next(
                    (
                        position
                        for position, candidate_name in reversed(preceding)
                        if candidate_name == unit_name
                    ),
                    None,
                )
                unit_leadership = tuple(
                    line
                    for line in (
                        lines[unit_position + 1 : block_start]
                        if unit_position is not None
                        else ()
                    )
                    if LEADERSHIP.search(line)
                )
                units.setdefault(
                    unit_name,
                    {
                        "page": page_index + 1,
                        "leadership": unit_leadership,
                        "parent": (
                            parent_school if unit_name != parent_school else None
                        ),
                    },
                )
                previous_block_start = block_start

        for unit_name, values in units.items():
            page_number = int(values["page"])
            observation_id = _stable_id(
                ACADEMIC_UNIT_OBJECT_TYPE, year, document_hash, unit_name
            )
            provenance = self._provenance(
                path, year, document_hash, (page_number,)
            )
            observations.append(
                AcademicUnitObservation(
                    id=observation_id,
                    object_type=ACADEMIC_UNIT_OBJECT_TYPE,
                    title=unit_name,
                    text=f"Published academic unit: {unit_name}\nCatalog year: {year}",
                    metadata={"semantic_layer": ACADEMIC_UNIT_OBJECT_TYPE},
                    source={
                        "kind": "institutional_academic_catalog",
                        "path": _relative_path(path),
                        "content_hash": document_hash,
                    },
                    normalized_at=normalized_at,
                    observation_id=observation_id,
                    catalog_year=year,
                    published_name=unit_name,
                    published_parent_unit=values["parent"],
                    published_leadership=values["leadership"],
                    page_numbers=(page_number,),
                    source_filename=path.name,
                    relative_source_path=_relative_path(path),
                    document_hash=document_hash,
                    provenance=provenance,
                )
            )

        for ordinal, (unit_name, page_number, entries) in enumerate(rosters):
            observation_id = _stable_id(
                ROSTER_OBJECT_TYPE,
                year,
                document_hash,
                unit_name,
                str(ordinal),
            )
            provenance = self._provenance(
                path, year, document_hash, (page_number,)
            )
            observations.append(
                DepartmentFacultyRosterObservation(
                    id=observation_id,
                    object_type=ROSTER_OBJECT_TYPE,
                    title=f"Faculty roster: {unit_name} ({year})",
                    text=f"Published faculty roster: {unit_name}\nCatalog year: {year}",
                    metadata={"semantic_layer": ROSTER_OBJECT_TYPE},
                    source={
                        "kind": "institutional_academic_catalog",
                        "path": _relative_path(path),
                        "content_hash": document_hash,
                    },
                    normalized_at=normalized_at,
                    observation_id=observation_id,
                    catalog_year=year,
                    academic_unit=unit_name,
                    entries=tuple(entries),
                    page_numbers=(page_number,),
                    source_filename=path.name,
                    relative_source_path=_relative_path(path),
                    document_hash=document_hash,
                    provenance=provenance,
                )
            )
        return observations

    @staticmethod
    def _is_registry_name(line: str) -> bool:
        return (
            line.upper() == line
            and 2 <= len(line.split()) <= 8
            and len(line) < 90
            and re.search(r"[A-Z]", line) is not None
            and line not in {"FACULTY", "EMERITI FACULTY", "INDEX"}
        )

    def _registry_observations(
        self,
        path: Path,
        document: fitz.Document,
        year: str,
        document_hash: str,
        normalized_at: str,
    ) -> list[CatalogFacultyObservation]:
        start_page = next(
            (
                index
                for index, page in enumerate(document)
                if "parenthetical date indicates" in page.get_text("text")
            ),
            None,
        )
        if start_page is None:
            return []

        records: list[Tuple[str, list[str], list[int]]] = []
        current_name: Optional[str] = None
        current_lines: list[str] = []
        current_pages: list[int] = []
        stop = False
        for page_index in range(start_page, document.page_count):
            lines = _page_lines(document[page_index])
            page_has_name = False
            for line in lines:
                if line == "EMERITI FACULTY":
                    stop = True
                    break
                if self._is_registry_name(line):
                    page_has_name = True
                    if current_name is not None:
                        records.append((current_name, current_lines, current_pages))
                    current_name = line
                    current_lines = []
                    current_pages = [page_index + 1]
                    continue
                if current_name is not None and not _is_header_noise(line, year):
                    current_lines.append(line)
                    if page_index + 1 not in current_pages:
                        current_pages.append(page_index + 1)
            if stop:
                break
            if page_index > start_page and not page_has_name:
                break
        if current_name is not None:
            records.append((current_name, current_lines, current_pages))

        observations = []
        for name, fragments, pages in records:
            entry_text = _normalize(" ".join(fragments))
            year_match = re.search(r"\(((?:19|20)\d{2})\)\s*$", entry_text)
            appointment_year = year_match.group(1) if year_match else None
            without_year = (
                entry_text[: year_match.start()].rstrip(" .")
                if year_match
                else entry_text
            )
            degree_match = DEGREE_MARKER.search(without_year)
            appointment_text = (
                without_year[: degree_match.start()].strip(" .")
                if degree_match
                else without_year
            )
            education = (
                without_year[degree_match.start() :].strip()
                if degree_match
                else None
            )
            title = appointment_text or None
            academic_unit = None
            unit_match = re.match(
                r"^(?P<title>.+?)\s+in\s+(?:the\s+)?(?P<unit>.+?)\.?$",
                appointment_text,
                flags=re.IGNORECASE,
            )
            if unit_match:
                title = unit_match.group("title")
                academic_unit = unit_match.group("unit").rstrip(".")
            observation_id = _stable_id(
                CATALOG_FACULTY_OBJECT_TYPE,
                year,
                document_hash,
                name,
            )
            provenance = self._provenance(path, year, document_hash, pages)
            observations.append(
                CatalogFacultyObservation(
                    id=observation_id,
                    object_type=CATALOG_FACULTY_OBJECT_TYPE,
                    title=name,
                    text=f"Published catalog faculty entry: {name}\nCatalog year: {year}",
                    metadata={"semantic_layer": CATALOG_FACULTY_OBJECT_TYPE},
                    source={
                        "kind": "institutional_academic_catalog",
                        "path": _relative_path(path),
                        "content_hash": document_hash,
                    },
                    normalized_at=normalized_at,
                    observation_id=observation_id,
                    catalog_year=year,
                    published_name=name,
                    published_title=title,
                    academic_unit=academic_unit,
                    education=education,
                    appointment_year=appointment_year,
                    published_entry_text=entry_text,
                    page_numbers=tuple(pages),
                    source_filename=path.name,
                    relative_source_path=_relative_path(path),
                    document_hash=document_hash,
                    provenance=provenance,
                )
            )
        return observations

    def _adapt_file(
        self, path: Path, normalized_at: str
    ) -> list[KnowledgeObject]:
        year = _catalog_year(path)
        document_hash = _hash_file(path)
        with fitz.open(path) as document:
            observations: list[KnowledgeObject] = [
                self._catalog_metadata(
                    path, document, year, document_hash, normalized_at
                )
            ]
            observations.extend(
                self._department_observations(
                    path, document, year, document_hash, normalized_at
                )
            )
            observations.extend(
                self._registry_observations(
                    path, document, year, document_hash, normalized_at
                )
            )
            return observations

    def adapt(self, *, timestamp: Optional[datetime] = None) -> CatalogAdaptationResult:
        timestamp = timestamp or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            raise ValueError("Catalog adaptation timestamp must be timezone-aware")
        result = CatalogAdaptationResult()
        paths = sorted(self.source_directory.glob("*.pdf"))
        result.files_discovered = len(paths)
        seen_ids = set()

        for path in paths:
            try:
                observations = self._adapt_file(path, timestamp.isoformat())
                for observation in observations:
                    if observation.id in seen_ids:
                        result.duplicate_observation_ids += 1
                        continue
                    seen_ids.add(observation.id)
                    result.observations.append(observation)
                    result.objects_by_type[observation.object_type] += 1
                    if isinstance(observation, DepartmentFacultyRosterObservation):
                        result.roster_entries += len(observation.entries)
                    if isinstance(observation, CatalogFacultyObservation):
                        result.registry_entries += 1
                result.files_processed += 1
            except Exception as exc:
                result.files_failed += 1
                result.failures.append({"path": str(path), "error": str(exc)})
        return result


def write_observations(
    observations: Iterable[KnowledgeObject], output_root: Path
) -> int:
    output_root = Path(output_root)
    count = 0
    for observation in observations:
        year = str(getattr(observation, "catalog_year"))
        directory = output_root / year
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{observation.object_type}_{observation.id}.json"
        save_knowledge_object(observation, path)
        count += 1
    return count


__all__ = [
    "AcademicUnitObservation",
    "CatalogAdapter",
    "CatalogAdaptationResult",
    "CatalogFacultyObservation",
    "CatalogFacultyRosterEntry",
    "CatalogObservation",
    "DepartmentFacultyRosterObservation",
    "catalog_observation_from_dict",
    "write_observations",
]
