"""Adapt a raw faculty-directory snapshot into factual Knowledge Objects.

This Semantic Layer adapter records what the acquired institutional directory
published. It does not resolve people, canonicalize organizations, or derive
employment, workload, performance, staffing, or institutional-value claims.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from app.knowledge import KnowledgeObject, save_knowledge_object


ADAPTER_NAME = "faculty_directory_adapter"
ADAPTER_VERSION = "0.1"
OBJECT_TYPE = "faculty_observation"
INDEX_FILENAME = "faculty_index.html"
MANIFEST_FILENAME = "manifest.json"


def _normalized_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, Tag):
        value = value.get_text(" ", strip=True)
    text = " ".join(str(value).split())
    return text or None


def _text_lines(tag: Optional[Tag]) -> Tuple[str, ...]:
    if tag is None:
        return ()
    values = []
    for part in tag.get_text("\n").splitlines():
        value = _normalized_text(part)
        if value and value not in values:
            values.append(value)
    return tuple(values)


def _component_text_without(
    tag: Optional[Tag],
    *,
    remove_selectors: Iterable[str] = (),
    remove_headings: Iterable[str] = (),
) -> Optional[str]:
    if tag is None:
        return None
    fragment = BeautifulSoup(str(tag), "html.parser")
    for selector in remove_selectors:
        for node in fragment.select(selector):
            node.decompose()
    ignored = {value.casefold() for value in remove_headings}
    for heading in fragment.find_all(["h1", "h2", "h3", "h4"]):
        label = _normalized_text(heading)
        if label and label.casefold() in ignored:
            heading.decompose()
    return _normalized_text(fragment)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _snapshot_date(path: Path) -> str:
    value = path.name
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(
            "Faculty snapshot directory must use a YYYY-MM-DD name: "
            f"{path}"
        )
    return value


def _observation_id(snapshot_date: str, profile_url: str, relative_path: str) -> str:
    identity = {
        "snapshot_date": snapshot_date,
        "profile_url": profile_url,
        "relative_path": relative_path if not profile_url else None,
    }
    payload = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _relative_source_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _structural_variant(component: Tag) -> str:
    bio = component.select_one(".bio")
    education = component.select_one(".education")
    heading = education.find(["h1", "h2", "h3", "h4"]) if education else None
    features = (
        "biography" if bio is not None else "no-biography",
        f"education-{heading.name}" if heading else "education-no-heading",
        "teaching" if component.select_one(".teaching") else "no-teaching",
        "research" if component.select_one(".research") else "no-research",
        (
            "accomplishments"
            if component.select_one(".accomplishments")
            else "no-accomplishments"
        ),
    )
    return "; ".join(features)


def _manifest_records(snapshot_directory: Path) -> Dict[str, Dict[str, Any]]:
    manifest_path = snapshot_directory / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return {}
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Faculty acquisition manifest must contain a list")
    return {
        str(record.get("saved_filename")): record
        for record in payload
        if isinstance(record, dict) and record.get("saved_filename")
    }


@dataclass
class FacultyObservation(KnowledgeObject):
    """One snapshot-scoped observation of a published faculty profile."""

    observation_id: str = ""
    display_name: Optional[str] = None
    given_name: Optional[str] = None
    middle_name: Optional[str] = None
    family_name: Optional[str] = None
    suffix: Optional[str] = None
    profile_heading: Optional[str] = None
    published_titles: Tuple[str, ...] = field(default_factory=tuple)
    published_department: Optional[str] = None
    published_college: Optional[str] = None
    organizational_affiliations: Tuple[Dict[str, str], ...] = field(
        default_factory=tuple
    )
    email: Optional[str] = None
    phone: Optional[str] = None
    office: Optional[str] = None
    profile_url: Optional[str] = None
    biography: Optional[str] = None
    education_entries: Tuple[str, ...] = field(default_factory=tuple)
    research_interests: Optional[str] = None
    teaching_interests: Optional[str] = None
    publications: Tuple[str, ...] = field(default_factory=tuple)
    professional_experience: Tuple[str, ...] = field(default_factory=tuple)
    awards_honors: Tuple[str, ...] = field(default_factory=tuple)
    service: Tuple[str, ...] = field(default_factory=tuple)
    courses_or_areas_taught: Tuple[str, ...] = field(default_factory=tuple)
    other_labeled_sections: Dict[str, Tuple[str, ...]] = field(
        default_factory=dict
    )
    original_labeled_fields: Dict[str, Any] = field(default_factory=dict)
    snapshot_date: str = ""
    source_file: str = ""
    relative_source_path: str = ""
    raw_acquisition_hash: str = ""
    structural_variant: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.object_type != OBJECT_TYPE:
            raise ValueError(f"FacultyObservation.object_type must be {OBJECT_TYPE!r}")
        if not self.observation_id or self.id != self.observation_id:
            raise ValueError("id and observation_id must contain the same stable ID")
        if not self.snapshot_date:
            raise ValueError("snapshot_date is required")
        self.published_titles = tuple(self.published_titles)
        self.organizational_affiliations = tuple(
            dict(value) for value in self.organizational_affiliations
        )
        self.education_entries = tuple(self.education_entries)
        self.publications = tuple(self.publications)
        self.professional_experience = tuple(self.professional_experience)
        self.awards_honors = tuple(self.awards_honors)
        self.service = tuple(self.service)
        self.courses_or_areas_taught = tuple(self.courses_or_areas_taught)
        self.other_labeled_sections = {
            str(label): tuple(values)
            for label, values in self.other_labeled_sections.items()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FacultyObservation":
        payload = dict(data)
        payload["original_labeled_fields"] = {
            key: tuple(value) if isinstance(value, list) else value
            for key, value in payload.get("original_labeled_fields", {}).items()
        }
        return cls(**payload)


@dataclass
class FacultyAdaptationResult:
    observations: list[FacultyObservation] = field(default_factory=list)
    files_discovered: int = 0
    objects_created: int = 0
    skipped_files: int = 0
    failures: list[Dict[str, str]] = field(default_factory=list)
    missing_names: int = 0
    missing_departments: int = 0
    missing_emails: int = 0
    duplicate_observation_ids: int = 0
    structural_variants: Counter[str] = field(default_factory=Counter)
    unknown_labels: Counter[str] = field(default_factory=Counter)


class FacultyDirectoryAdapter:
    """Extract factual fields from one acquired faculty snapshot."""

    def __init__(self, snapshot_directory: Path) -> None:
        self.snapshot_directory = Path(snapshot_directory)
        if not self.snapshot_directory.is_dir():
            raise FileNotFoundError(
                f"Faculty snapshot not found: {self.snapshot_directory}"
            )

    def _parse_profile(
        self,
        path: Path,
        manifest_record: Dict[str, Any],
        snapshot_date: str,
        normalized_at: str,
    ) -> FacultyObservation:
        soup = BeautifulSoup(path.read_bytes(), "html.parser")
        component = soup.select_one("section.component-faculty-page")
        if component is None:
            raise ValueError("faculty profile component not found")

        contact = component.select_one(".contact-info")
        if contact is None:
            raise ValueError("faculty contact component not found")

        display_name = _normalized_text(contact.select_one(".name"))
        published_titles = _text_lines(contact.select_one(".job"))
        email = _normalized_text(
            contact.select_one('a.email[href^="mailto:"], a[href^="mailto:"]')
        )
        phone = _normalized_text(
            contact.select_one('a.phone[href^="tel:"], a[href^="tel:"]')
        )
        office_values = [
            value
            for paragraph in contact.find_all("p", recursive=False)
            if "job" not in (paragraph.get("class") or [])
            for value in [_normalized_text(paragraph)]
            if value
        ]

        affiliations = []
        for link in contact.select("ul.inline-list a[href]"):
            label = _normalized_text(link)
            url = str(link.get("href", ""))
            if label:
                affiliations.append({"label": label, "url": url})
        department = next(
            (
                item["label"]
                for item in affiliations
                if "/academics/departments/" in item["url"]
            ),
            None,
        )
        college = next(
            (
                item["label"]
                for item in affiliations
                if item["label"].casefold().startswith("college of ")
            ),
            None,
        )

        education = tuple(
            value
            for item in component.select(".education .degrees > li")
            for value in [_normalized_text(item)]
            if value
        )
        biography = _component_text_without(
            component.select_one(".bio"),
            remove_selectors=(".education",),
            remove_headings=("Biography",),
        )
        teaching = _component_text_without(
            component.select_one(".teaching"),
            remove_headings=("Teaching",),
        )
        research = _component_text_without(
            component.select_one(".research"),
            remove_headings=("Research",),
        )

        labeled_sections: Dict[str, Tuple[str, ...]] = {}
        for button in component.select(".accomplishments .accordion-button"):
            label = _normalized_text(button)
            target = str(button.get("data-bs-target", "")).lstrip("#")
            body = component.find(id=target) if target else None
            if not label or body is None:
                continue
            items = tuple(
                value
                for item in body.select(".facultyData > li")
                for value in [_normalized_text(item)]
                if value
            )
            if not items:
                value = _normalized_text(body.select_one(".accordion-body"))
                items = (value,) if value else ()
            labeled_sections[label] = items

        all_labeled_sections = dict(labeled_sections)
        publications = labeled_sections.pop("Publications", ())
        awards_honors = labeled_sections.pop("Awards and Honors", ())
        professional_experience = labeled_sections.pop(
            "Professional Experience", ()
        )
        service = labeled_sections.pop("Service", ())

        profile_url = str(manifest_record.get("original_url") or "")
        if not profile_url:
            meta_url = soup.select_one('meta[property="og:url"]')
            profile_url = str(meta_url.get("content", "")) if meta_url else ""
        relative_path = _relative_source_path(path)
        raw_hash = str(manifest_record.get("sha256_hash") or _sha256(path))
        observation_id = _observation_id(
            snapshot_date,
            profile_url,
            relative_path,
        )
        variant = _structural_variant(component)

        original_fields: Dict[str, Any] = {
            "Name": display_name,
            "Published titles": published_titles,
            "Office": tuple(office_values),
            "Phone": phone,
            "Email": email,
            "Organizational affiliations": tuple(affiliations),
            "Education": education,
            "Biography": biography,
            "Teaching": teaching,
            "Research": research,
            **all_labeled_sections,
        }
        original_fields = {
            key: value
            for key, value in original_fields.items()
            if value not in (None, "", (), [])
        }
        acquisition_timestamp = manifest_record.get("crawl_timestamp")
        provenance = {
            "snapshot_date": snapshot_date,
            "profile_url": profile_url or None,
            "relative_source_path": relative_path,
            "source_sha256": raw_hash,
            "acquisition_timestamp": acquisition_timestamp,
            "adapter": ADAPTER_NAME,
            "adapter_version": ADAPTER_VERSION,
            "source_type": "institutional_faculty_directory",
        }

        factual_lines = ["Faculty directory observation"]
        if display_name:
            factual_lines.append(f"Name: {display_name}")
        factual_lines.append(f"Snapshot: {snapshot_date}")

        return FacultyObservation(
            id=observation_id,
            object_type=OBJECT_TYPE,
            title=display_name or f"Faculty profile: {path.stem}",
            text="\n".join(factual_lines),
            metadata={
                "semantic_layer": OBJECT_TYPE,
                "adapter": ADAPTER_NAME,
                "adapter_version": ADAPTER_VERSION,
                "structural_variant": variant,
            },
            source={
                "kind": "institutional_faculty_directory",
                "path": relative_path,
                "url": profile_url or None,
                "content_hash": raw_hash,
            },
            created_at=acquisition_timestamp,
            normalized_at=normalized_at,
            observation_id=observation_id,
            display_name=display_name,
            profile_heading=display_name,
            published_titles=published_titles,
            published_department=department,
            published_college=college,
            organizational_affiliations=tuple(affiliations),
            email=email,
            phone=phone,
            office=office_values[0] if office_values else None,
            profile_url=profile_url or None,
            biography=biography,
            education_entries=education,
            research_interests=research,
            teaching_interests=teaching,
            publications=publications,
            professional_experience=professional_experience,
            awards_honors=awards_honors,
            service=service,
            courses_or_areas_taught=(),
            other_labeled_sections=labeled_sections,
            original_labeled_fields=original_fields,
            snapshot_date=snapshot_date,
            source_file=path.name,
            relative_source_path=relative_path,
            raw_acquisition_hash=raw_hash,
            structural_variant=variant,
            provenance=provenance,
        )

    def adapt(self, *, timestamp: Optional[datetime] = None) -> FacultyAdaptationResult:
        timestamp = timestamp or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            raise ValueError("Faculty adaptation timestamp must be timezone-aware")
        normalized_at = timestamp.isoformat()
        snapshot_date = _snapshot_date(self.snapshot_directory)
        manifest = _manifest_records(self.snapshot_directory)
        paths = sorted(
            path
            for path in self.snapshot_directory.glob("*.html")
            if path.name != INDEX_FILENAME
        )
        result = FacultyAdaptationResult(files_discovered=len(paths))
        seen_ids = set()

        for path in paths:
            try:
                observation = self._parse_profile(
                    path,
                    manifest.get(path.name, {}),
                    snapshot_date,
                    normalized_at,
                )
                if observation.id in seen_ids:
                    result.duplicate_observation_ids += 1
                    result.skipped_files += 1
                    continue
                seen_ids.add(observation.id)
                result.observations.append(observation)
                result.objects_created += 1
                result.structural_variants[observation.structural_variant or "unknown"] += 1
                result.unknown_labels.update(
                    observation.other_labeled_sections.keys()
                )
                if not observation.display_name:
                    result.missing_names += 1
                if not observation.published_department:
                    result.missing_departments += 1
                if not observation.email:
                    result.missing_emails += 1
            except Exception as exc:
                result.failures.append({"path": str(path), "error": str(exc)})
                result.skipped_files += 1

        return result


def write_observations(
    observations: Iterable[FacultyObservation],
    output_directory: Path,
) -> int:
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    count = 0
    for observation in observations:
        save_knowledge_object(
            observation,
            output_directory / f"faculty_observation_{observation.id}.json",
        )
        count += 1
    return count


__all__ = [
    "FacultyAdaptationResult",
    "FacultyDirectoryAdapter",
    "FacultyObservation",
    "write_observations",
]
