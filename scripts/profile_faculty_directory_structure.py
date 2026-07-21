#!/usr/bin/env python3
"""Profile the HTML structure of a raw CNU faculty-directory snapshot.

This Evidence Layer reconnaissance tool reports structures and field presence.
It deliberately does not extract faculty values, normalize names, infer
departments, resolve entities, or create semantic records.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from typing import Callable, Iterable
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag


# ---------------------------------------------------------------------------
# Report configuration
# ---------------------------------------------------------------------------

SNAPSHOT_DIRECTORY = Path("data/acquisition/faculty/raw/2026-07-21")
INDEX_FILENAME = "faculty_index.html"
REPORT_PATH = Path("reports/faculty_directory_structure_report.md")
TOP_COUNT = 25


COMMON_SELECTORS = (
    "main.cn-page-template-cnu",
    "section.component-faculty-page",
    "section.component-faculty-page .profile",
    "section.component-faculty-page .profile-image img",
    "section.component-faculty-page .contact-info",
    "section.component-faculty-page .contact-info .name",
    "section.component-faculty-page .contact-info .job",
    'section.component-faculty-page .contact-info a[href^="mailto:"]',
    'section.component-faculty-page .contact-info a[href^="tel:"]',
    "section.component-faculty-page .contact-info .inline-list a",
    'section.component-faculty-page .contact-info a[href*="/academics/departments/"]',
    "section.component-faculty-page .bio",
    "section.component-faculty-page .education",
    "section.component-faculty-page .education .degrees",
    "section.component-faculty-page .disciplines",
    "section.component-faculty-page .teaching",
    "section.component-faculty-page .research",
    "section.component-faculty-page .accomplishments",
    "section.component-faculty-page .accomplishments .accordion-item",
    "section.component-faculty-page .accomplishments .facultyData",
)


@dataclass(frozen=True)
class FieldRule:
    """Structural test for the presence of a field, not its value."""

    label: str
    description: str
    present: Callable[[BeautifulSoup], bool]


def _has_selector(selector: str) -> Callable[[BeautifulSoup], bool]:
    return lambda soup: soup.select_one(selector) is not None


def _normalized_text(tag: Tag) -> str:
    return " ".join(tag.get_text(" ", strip=True).casefold().split())


def _has_labeled_element(soup: BeautifulSoup, labels: set[str]) -> bool:
    component = soup.select_one("section.component-faculty-page")
    if component is None:
        return False
    for tag in component.find_all(
        ["h1", "h2", "h3", "h4", "dt", "th", "strong", "button"]
    ):
        if _normalized_text(tag).rstrip(":") in labels:
            return True
    return False


def _has_office_structure(soup: BeautifulSoup) -> bool:
    contact = soup.select_one("section.component-faculty-page .contact-info")
    if contact is None:
        return False
    return any(
        "job" not in (child.get("class") or [])
        for child in contact.find_all("p", recursive=False)
    )


def _has_cv_structure(soup: BeautifulSoup) -> bool:
    component = soup.select_one("section.component-faculty-page")
    if component is None:
        return False
    for link in component.find_all("a", href=True):
        text = _normalized_text(link)
        href = str(link["href"]).casefold()
        if text in {"cv", "curriculum vitae", "vita"}:
            return True
        if re.search(r"(?:^|[/_-])(?:cv|vita)(?:[._/-]|$)", href):
            return True
    return False


FIELD_RULES = (
    FieldRule(
        "Name",
        ".component-faculty-page .contact-info .name",
        _has_selector(".component-faculty-page .contact-info .name"),
    ),
    FieldRule(
        "Title",
        ".component-faculty-page .contact-info .job",
        _has_selector(".component-faculty-page .contact-info .job"),
    ),
    FieldRule(
        "Office",
        "direct .contact-info child paragraph other than .job",
        _has_office_structure,
    ),
    FieldRule(
        "Phone",
        '.contact-info a.phone or a[href^="tel:"]',
        _has_selector(
            '.component-faculty-page .contact-info a.phone, '
            '.component-faculty-page .contact-info a[href^="tel:"]'
        ),
    ),
    FieldRule(
        "Email",
        '.contact-info a.email or a[href^="mailto:"]',
        _has_selector(
            '.component-faculty-page .contact-info a.email, '
            '.component-faculty-page .contact-info a[href^="mailto:"]'
        ),
    ),
    FieldRule(
        "Department",
        'organizational link whose href contains "/academics/departments/"',
        _has_selector(
            '.component-faculty-page .contact-info '
            'a[href*="/academics/departments/"]'
        ),
    ),
    FieldRule("Education", ".education", _has_selector(".education")),
    FieldRule(
        "Biography",
        'heading/label exactly "Biography"',
        lambda soup: _has_labeled_element(soup, {"biography"}),
    ),
    FieldRule("Teaching", ".teaching", _has_selector(".teaching")),
    FieldRule("Research", ".research", _has_selector(".research")),
    FieldRule(
        "Courses",
        'heading/label exactly "Course" or "Courses"',
        lambda soup: _has_labeled_element(soup, {"course", "courses"}),
    ),
    FieldRule("CV", "CV/vita link text or URL pattern", _has_cv_structure),
)


def _profile_files() -> list[Path]:
    if not SNAPSHOT_DIRECTORY.is_dir():
        raise FileNotFoundError(
            f"Faculty snapshot directory not found: {SNAPSHOT_DIRECTORY}"
        )

    return sorted(
        path
        for path in SNAPSHOT_DIRECTORY.glob("*.html")
        if path.name != INDEX_FILENAME
    )


def _title_format(soup: BeautifulSoup) -> str:
    if soup.title is None:
        return "[missing title]"

    title = " ".join(soup.title.get_text(" ", strip=True).split())
    suffix = " | Christopher Newport University"
    if title.endswith(suffix) and title != suffix.strip():
        return f"<profile name>{suffix}"
    return title or "[empty title]"


def _heading_signature(soup: BeautifulSoup) -> str:
    parts = []
    for heading in soup.find_all(["h1", "h2"]):
        label = _normalized_text(heading)
        if "name" in (heading.get("class") or []):
            label = "<profile name>"
        parts.append(f"{heading.name}:{label or '[empty]'}")
    return " → ".join(parts) or "[no h1/h2]"


def _education_heading_level(soup: BeautifulSoup) -> str:
    education = soup.select_one(".education")
    if education is None:
        return "missing"
    heading = education.find(["h1", "h2", "h3", "h4"])
    return heading.name if heading is not None else "no-heading"


def _template_signature(soup: BeautifulSoup) -> str:
    """Return a coarse layout signature, ignoring repeated content records."""
    if _has_labeled_element(soup, {"biography"}):
        biography_layout = "biography-present"
    elif soup.select_one(".no-bio") is not None:
        biography_layout = "no-biography-layout"
    else:
        biography_layout = "other-biography-layout"

    features = (
        (
            "faculty-component"
            if soup.select_one("section.component-faculty-page")
            else "no-faculty-component"
        ),
        biography_layout,
        f"education-{_education_heading_level(soup)}",
        "teaching" if soup.select_one(".teaching") else "no-teaching",
        "research" if soup.select_one(".research") else "no-research",
        (
            "accomplishments"
            if soup.select_one(".accomplishments")
            else "no-accomplishments"
        ),
    )
    return "; ".join(features)


def _metadata_keys(soup: BeautifulSoup) -> set[str]:
    keys = set()
    for meta in soup.find_all("meta"):
        if meta.has_attr("charset"):
            keys.add("meta[charset]")
        for attribute in ("name", "property", "itemprop", "http-equiv"):
            value = meta.get(attribute)
            if value:
                keys.add(f'meta[{attribute}="{value}"]')
    return keys


def _page_classes(soup: BeautifulSoup) -> set[str]:
    classes = set()
    component = soup.select_one("section.component-faculty-page")
    if component is None:
        return classes
    for tag in component.find_all(class_=True):
        classes.update(str(value) for value in tag.get("class") or [])
    return classes


def _table(headers: Iterable[str], rows: Iterable[Iterable[object]]) -> list[str]:
    headers = list(headers)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        values = [str(value).replace("|", "\\|").replace("\n", " ") for value in row]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def _percent(count: int, total: int) -> str:
    return f"{(100.0 * count / total):.1f}%" if total else "0.0%"


def _counter_rows(counter: Counter[str], total: int, limit: int = TOP_COUNT):
    ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    for label, count in ranked[:limit]:
        yield (f"`{label}`", count, _percent(count, total))


def _duplicate_rows(hash_to_files: dict[str, list[str]]):
    duplicates = [
        (digest, files)
        for digest, files in hash_to_files.items()
        if len(files) > 1
    ]
    for digest, files in sorted(duplicates):
        yield (f"`{digest}`", len(files), ", ".join(f"`{name}`" for name in files))


def _index_analysis(index_path: Path) -> tuple[list[str], dict[str, object]]:
    if not index_path.is_file():
        return (
            [
                "## 6. Index Page Analysis",
                "",
                f"The index page is missing: `{index_path}`.",
            ],
            {"profile_links": 0},
        )

    soup = BeautifulSoup(index_path.read_bytes(), "html.parser")
    cards = soup.select(
        ".cardHolder.cn-funnel a.flex-card.cn-index-funnel.filter-select[href]"
    )
    hrefs = [str(card.get("href", "")) for card in cards]
    relative_links = sum(not urlparse(href).netloc for href in hrefs)
    title_attributes = sum(bool(card.get("title")) for card in cards)
    visible_labels = sum(bool(card.get_text(" ", strip=True)) for card in cards)
    image_sources = sum(card.select_one("img[src]") is not None for card in cards)
    image_alts = sum(
        bool((card.select_one("img") or {}).get("alt"))
        if card.select_one("img") is not None
        else False
        for card in cards
    )

    container = soup.select_one(".cardHolder.cn-funnel")
    department_data = []
    department_classes = []
    department_headings = []
    if container is not None:
        department_data = container.select(
            "[data-department], [data-dept], [data-school], [data-college]"
        )
        department_classes = container.select(
            ".department, .departments, .school, .college"
        )
        department_headings = [
            tag
            for tag in container.find_all(["h2", "h3", "h4"])
            if "faculty directory" not in _normalized_text(tag)
        ]

    department_markers = (
        len(department_data) + len(department_classes) + len(department_headings)
    )
    if department_markers:
        organization = (
            "Potential department/school grouping markers were detected and "
            "must be inspected before use: "
            f"{department_markers} structural markers."
        )
    else:
        organization = (
            "No explicit department grouping, department data attributes, or "
            "department headings were detected inside `.cardHolder.cn-funnel`. The "
            "index is structurally a flat searchable card list; department "
            "membership must not be inferred from card order."
        )

    class_signatures = Counter(
        " ".join(card.get("class") or []) or "[no class]" for card in cards
    )

    lines = [
        "## 6. Index Page Analysis",
        "",
        (
            "- Profile cards matched by `.cardHolder.cn-funnel "
            "a.flex-card.cn-index-funnel.filter-select[href]`: "
            f"**{len(cards)}**"
        ),
        f"- Relative profile links: **{relative_links}**",
        f"- Absolute profile links: **{len(cards) - relative_links}**",
        f"- Cards with a `title` attribute: **{title_attributes}**",
        f"- Cards with visible text: **{visible_labels}**",
        f"- Cards with an image source: **{image_sources}**",
        f"- Cards with image alt text: **{image_alts}**",
        "",
        "### Department organization",
        "",
        organization,
        "",
        "### Profile-link representation",
        "",
        (
            "Profiles are represented as anchor cards inside "
            "`.cardHolder.cn-funnel`, adjacent to the `#facultyList` search "
            "controls. The current cards carry URL-relative `href` values, a `title` "
            "attribute, visible text, and a nested headshot image. These are "
            "index metadata structures only; this report does not extract "
            "their values."
        ),
        "",
        *_table(
            ("Card class signature", "Count"),
            ((f"`{signature}`", count) for signature, count in class_signatures.most_common()),
        ),
        "",
        "### Index-only normalization implications",
        "",
        (
            "- Use `.cardHolder.cn-funnel "
            "a.flex-card.cn-index-funnel.filter-select[href]` as the primary "
            "discovery selector."
        ),
        "- Preserve card `title`, visible label, and image metadata as source-level fallbacks only; do not assume they supersede profile-page fields.",
        "- The index supplies no reliable department grouping in its current structure.",
    ]
    return lines, {"profile_links": len(cards)}


def build_report() -> tuple[str, dict[str, object]]:
    profile_paths = _profile_files()
    total = len(profile_paths)
    if not profile_paths:
        raise RuntimeError(f"No faculty profile HTML files found in {SNAPSHOT_DIRECTORY}")

    sizes = []
    hash_to_files: dict[str, list[str]] = defaultdict(list)
    title_formats: Counter[str] = Counter()
    heading_signatures: Counter[str] = Counter()
    class_pages: Counter[str] = Counter()
    selector_pages: Counter[str] = Counter()
    selector_nodes: Counter[str] = Counter()
    metadata_pages: Counter[str] = Counter()
    field_pages: Counter[str] = Counter()
    template_signatures: Counter[str] = Counter()
    base_template_pages = 0

    for path in profile_paths:
        content = path.read_bytes()
        sizes.append((len(content), path.name))
        digest = hashlib.sha256(content).hexdigest()
        hash_to_files[digest].append(path.name)
        soup = BeautifulSoup(content, "html.parser")

        title_formats[_title_format(soup)] += 1
        heading_signatures[_heading_signature(soup)] += 1
        template_signatures[_template_signature(soup)] += 1

        if soup.select_one("section.component-faculty-page") is not None:
            base_template_pages += 1

        class_pages.update(_page_classes(soup))
        metadata_pages.update(_metadata_keys(soup))

        for selector in COMMON_SELECTORS:
            matches = soup.select(selector)
            if matches:
                selector_pages[selector] += 1
                selector_nodes[selector] += len(matches)

        for rule in FIELD_RULES:
            if rule.present(soup):
                field_pages[rule.label] += 1

    sizes.sort()
    total_bytes = sum(size for size, _name in sizes)
    unique_hashes = len(hash_to_files)
    duplicate_groups = {
        digest: files for digest, files in hash_to_files.items() if len(files) > 1
    }
    duplicate_files = sum(len(files) - 1 for files in duplicate_groups.values())
    minimum_size, minimum_file = sizes[0]
    maximum_size, maximum_file = sizes[-1]
    average_size = total_bytes / total

    index_lines, index_stats = _index_analysis(SNAPSHOT_DIRECTORY / INDEX_FILENAME)

    all_use_base = base_template_pages == total
    lines = [
        "# Faculty Directory Structure Report",
        "",
        (
            "This report characterizes the raw HTML snapshot structurally. It "
            "does not extract faculty values, normalize names, infer "
            "departments, resolve entities, or create semantic records."
        ),
        "",
        f"**Snapshot:** `{SNAPSHOT_DIRECTORY}`",
        "",
        "## 1. Corpus Summary",
        "",
        f"- Total HTML profile pages: **{total}**",
        f"- Total unique SHA-256 hashes: **{unique_hashes}**",
        f"- Duplicate files beyond the first copy: **{duplicate_files}**",
        f"- Average profile page size: **{average_size:,.1f} bytes**",
        f"- Minimum page size: **{minimum_size:,} bytes** (`{minimum_file}`)",
        f"- Maximum page size: **{maximum_size:,} bytes** (`{maximum_file}`)",
        "",
        "### Duplicate content groups",
        "",
    ]

    if duplicate_groups:
        lines.extend(
            _table(
                ("SHA-256", "Files in group", "Filenames"),
                _duplicate_rows(hash_to_files),
            )
        )
    else:
        lines.append("No byte-identical profile files were detected.")

    lines.extend(
        [
            "",
            "## 2. HTML Structure",
            "",
            "### Page title formats",
            "",
            *_table(
                ("Title format", "Pages", "Coverage"),
                _counter_rows(title_formats, total),
            ),
            "",
            "### Most common H1/H2 sequences",
            "",
            (
                "The profile-name heading is represented as `<profile name>` "
                "so the count measures structure rather than individual text."
            ),
            "",
            *_table(
                ("H1/H2 sequence", "Pages", "Coverage"),
                _counter_rows(heading_signatures, total, 15),
            ),
            "",
            "### Common HTML classes",
            "",
            (
                "Counts below are pages containing the class within "
                "`section.component-faculty-page`, not site chrome or raw "
                "class occurrences."
            ),
            "",
            *_table(
                ("Class", "Pages", "Coverage"),
                _counter_rows(class_pages, total),
            ),
            "",
            "### Common CSS selectors",
            "",
            *_table(
                ("Selector", "Pages", "Coverage", "Matched nodes"),
                (
                    (
                        f"`{selector}`",
                        selector_pages[selector],
                        _percent(selector_pages[selector], total),
                        selector_nodes[selector],
                    )
                    for selector in COMMON_SELECTORS
                ),
            ),
            "",
            "### Common metadata tags",
            "",
            "Counts are pages containing at least one matching metadata key.",
            "",
            *_table(
                ("Metadata selector", "Pages", "Coverage"),
                _counter_rows(metadata_pages, total),
            ),
            "",
            "## 3. Common Field Labels and Structural Markers",
            "",
            (
                "Several contact fields are encoded by classes or link schemes "
                "rather than visible labels. `Department` below means only the "
                "presence of a department-path organizational link; no "
                "department value is extracted or inferred."
            ),
            "",
            *_table(
                ("Field", "Structural rule", "Pages present", "Coverage"),
                (
                    (
                        rule.label,
                        f"`{rule.description}`",
                        field_pages[rule.label],
                        _percent(field_pages[rule.label], total),
                    )
                    for rule in FIELD_RULES
                ),
            ),
            "",
            "## 4. Structural Consistency",
            "",
            f"- Pages using `section.component-faculty-page`: **{base_template_pages} / {total}**",
            f"- All pages use the common faculty component shell: **{'Yes' if all_use_base else 'No'}**",
            f"- Estimated structural variants: **{len(template_signatures)}**",
            "",
            (
                "The variant estimate is intentionally coarse. It fingerprints "
                "the faculty component, biography/no-biography layout, "
                "Education heading level, Teaching, Research, and Selected "
                "Accomplishments. It ignores repeated publication/award items "
                "and other content volume, so content differences are not "
                "misreported as separate templates."
            ),
            "",
            *_table(
                ("Structural variant", "Pages", "Coverage"),
                _counter_rows(template_signatures, total, len(template_signatures)),
            ),
            "",
            "### Distinguishing characteristics",
            "",
            "- Biography-present pages commonly nest `.education` inside `.bio`, where Education may use an `h3`.",
            "- No-biography pages commonly use `.no-bio` and may present Education as an `h2`.",
            "- Teaching, Research, and Selected Accomplishments are optional structural regions, not guaranteed fields.",
            "- Publication, award, and similar accomplishment lists vary in length within the same outer template.",
            "",
            "## 5. Missing Sections",
            "",
            *_table(
                ("Section/field", "Pages present", "Pages missing", "Missing coverage"),
                (
                    (
                        rule.label,
                        field_pages[rule.label],
                        total - field_pages[rule.label],
                        _percent(total - field_pages[rule.label], total),
                    )
                    for rule in FIELD_RULES
                    if rule.label
                    in {"Email", "Office", "Phone", "Department", "Biography", "Education"}
                ),
            ),
            "",
            (
                "A missing structural marker means the field was not located by "
                "the stated rule. It does not establish that the real-world "
                "information is absent."
            ),
            "",
            *index_lines,
            "",
            "## 7. Normalization Recommendations",
            "",
            "### Recommended selector order",
            "",
            "| Later extraction target | Primary selector | Fallback / caution |",
            "| --- | --- | --- |",
            "| Profile component | `section.component-faculty-page` | Reject or quarantine pages lacking the component rather than parsing global navigation |",
            "| Name | `.component-faculty-page .contact-info h2.name` | Page `<title>` and index card title are fallbacks; compare rather than silently overwrite |",
            "| Job title | `.component-faculty-page .contact-info p.job` | May contain `<br>`-separated multiple roles |",
            "| Email | `.component-faculty-page .contact-info a.email[href^=\"mailto:\"]` | Fall back to a scoped `a[href^=\"mailto:\"]`; never use the footer contact block |",
            "| Phone | `.component-faculty-page .contact-info a.phone[href^=\"tel:\"]` | Fall back to a scoped `a[href^=\"tel:\"]`; global telephone selectors match the site footer |",
            "| Office | `.component-faculty-page .contact-info > p:not(.job)` | Fragile because the current office line has no office-specific class or label; retain source locator and require fallback validation |",
            "| Affiliations | `.component-faculty-page .contact-info ul.inline-list a` | Links may represent departments, colleges, schools, programs, or offices; classify by authoritative URL pattern later, never by list order |",
            "| Department link candidate | `.component-faculty-page .contact-info a[href*=\"/academics/departments/\"]` | Structural candidate only; preserve URL and label and do not infer when absent |",
            "| Biography | `.bio > h2` followed by content within `.bio` | Do not absorb nested `.education`; support `.no-bio` pages |",
            "| Education | `.education` then `.degrees > li` | Heading level varies (`h2`/`h3`) with biography layout; select by class, not heading level |",
            "| Teaching | `.disciplines .teaching` | Optional and free-form |",
            "| Research | `.disciplines .research` | Optional and free-form |",
            "| Accomplishments | `.accomplishments .accordion-item` paired with its collapse body | Categories and list lengths vary; preserve category/source context |",
            "| CV | Link label/URL fallback rules reported above | Low structural reliability; do not treat arbitrary PDF links as CVs |",
            "",
            "### Reliability and fallback guidance",
            "",
            "- The faculty component, contact block, name, and job classes are the strongest current structural anchors; use measured coverage above as the acceptance baseline.",
            "- Email and phone should be detected by both semantic class and URI scheme. Record absence explicitly.",
            "- Always scope contact selectors to the faculty component; global `.contact-info` and `tel:` selectors also match the common footer.",
            "- Office is structurally weak because it is an unlabeled paragraph. A parser should validate position within `.contact-info` and preserve the raw locator.",
            "- Education must be class-selected because its heading level changes with biography presence.",
            "- Organizational links must not be collapsed into a single department field. Department, college, school, program, and office links can coexist.",
            "- Same outer template does not guarantee the same optional sections. Missing Biography, Education, Research, Teaching, accomplishments, or CV must remain missing.",
            "- Nested paragraph markup and variable accordion content are structural anomalies that favor scoped selectors over sibling-position assumptions.",
            "- Use the index for profile discovery and source-level fallback metadata, not for department inference.",
            "- A future normalizer should retain source filename, SHA-256, exact selector/locator, and snapshot date for every extracted assertion.",
        ]
    )

    summary = {
        "profiles": total,
        "unique_hashes": unique_hashes,
        "duplicate_files": duplicate_files,
        "average_size": average_size,
        "template_variants": len(template_signatures),
        "base_template_pages": base_template_pages,
        "index_profile_links": index_stats["profile_links"],
    }
    return "\n".join(lines) + "\n", summary


def main() -> int:
    report, summary = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print("Faculty Directory Structural Reconnaissance")
    print(f"Profiles: {summary['profiles']}")
    print(f"Unique SHA-256 hashes: {summary['unique_hashes']}")
    print(f"Duplicate files: {summary['duplicate_files']}")
    print(f"Average page size: {summary['average_size']:,.1f} bytes")
    print(f"Estimated structural variants: {summary['template_variants']}")
    print(
        "Common faculty component: "
        f"{summary['base_template_pages']} / {summary['profiles']} pages"
    )
    print(f"Index profile cards: {summary['index_profile_links']}")
    print(f"Report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
